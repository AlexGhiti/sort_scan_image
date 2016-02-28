#!/usr/bin/env python

import os
import re
import subprocess
import argparse

from paperDB import paperDB
from paperSort import paperSort

import pyinotify

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print "New paper:", event.pathname
        if re.match(".*tmp$", event.pathname):
            paper.ocr(event.pathname)
            paper.add_to_db_with_svm(event.pathname + ".txt")

class Paper:
    # scan_paper_dest may be an url or a local dest.
    def __init__(self, scan_paper_src, scan_paper_dest,
                    dict_path, db_path):
        self.scan_paper_src = scan_paper_src
        self.scan_paper_dest = scan_paper_dest
        self.paper_sort = paperSort(dict_path)
        self.paper_db = paperDB(db_path, self.paper_sort.dictionary)
        self.paper_db.table_create("paper")

    def __ocr(self, fname):
            #print("%s" % ["convert", fname, "{0}.jpg".format(fname)])
            #res = subprocess.call(["convert", fname,
            #                                "{0}.jpg".format(fname)])
            print("*** OCRing %s..." % fname)
            res = subprocess.call(["tesseract", "{0}".format(fname),
                                                "{0}".format(fname),
                                                "-l fra"])
            if res != 0:
                print("*** Tesseract failed on %s." % fname)

    def __parse_ocr_paper(self, ocr_paper_path):
        # 1/ Open OCRised file and read its content.
        content = self.paper_sort.read_content_ocr_file(ocr_paper_path)
        if (content is None):
            return None

        # 2/ Tokenisation of the file content.
        list_content_word = self.paper_sort.tokenise_content(content)

        # 3/ Generate vector of words according to current directory.
        vect_res = self.paper_sort.get_vector_list_word(self.paper_sort.dictionary, list_content_word)

        return vect_res

    # Returns the list of .tmp file only.
    def __get_paper_list(self, path):
        paper_list = []
        for root, directories, filenames in os.walk(path):
            if not "unknown" in root:
                paper_list.extend([os.path.join(root, f) for f in filenames if re.match(".*tmp$", f) ])

        return paper_list

    # Do 'cleanup' on ocr text and adds the result to db.
    def add_to_db_with_category(self, ocr_paper_path, category):
        vect_res = self.__parse_ocr_paper(ocr_paper_path);
        self.paper_sort.add_vector_db(self.paper_db, vect_res, ocr_paper_path,
                                        category)

    def add_to_db_with_svm(self, ocr_paper_path):
        vect_res = self.__parse_ocr_paper(ocr_paper_path);
        svm_category = self.paper_sort.clf.predict(vect_res)
        print("Le nouveau document est : %s" % svm_category)
        self.paper_sort.add_vector_db(self.paper_db, vect_res, ocr_paper_path,
                                        svm_category)

    # May be to discuss, but I prefer sorting documents in
    # directory by hand rather than writing a document giving
    # the category name of each document.
    def create_db(self, ocr):
        self.paper_db.table_create("paper")
        paper_list = self.__get_paper_list(self.scan_paper_src)
        for p in paper_list:
            if ocr:
                self.ocr(p)

            self.add_to_db_with_category(p + ".txt",
                                        p.split('/')[-2])

    def teach_svm(self):
        print(self.paper_sort.dictionary)
        # Get the list of vectors from db.
        (list_sample_vector, list_category) = self.paper_db.table_get_all_vector_for_svm(
                                                "paper", self.paper_sort.dictionary)
        print(list_sample_vector)
        print(list_category)

        if len(list_sample_vector) != 0:
            self.paper_sort.clf.fit(list_sample_vector,
                                    [i[0] for i in list_category])


parser = argparse.ArgumentParser(description = 'Process grep_and_sed arguments.')
# Create db from existing OCRised paper.
parser.add_argument('--create_db', action='store_true',
                    help = 'Create db from already ocrised paper.')
# Use this option to OCRise all paper to use in create_db option.
parser.add_argument('--create_db_with_ocr', action='store_true',
                    help = 'Create db from raw image (ie. : call ocr).')
parser.add_argument('--scan_paper_src', default = "/tmp/sort_scan_image/",
                    help = 'With create_db* = true: path where documents are '
                           'already classified.\n'
                            'With create_db* = false: path where freshly '
                            'scanned papers are copied after scan.')
parser.add_argument('--scan_paper_dest', default = "/tmp/sort_scan_image_dest/",
                    help = 'Only used with create_db* = false: root path (local '
                            'or remote) where classified papers must be sent '
                            '(Your server for example).')
parser.add_argument('--dict', default = "dictionary",
                    help = 'Dictionary filename to use to classify.')
parser.add_argument('--db', default = "paper.db",
                    help = 'Db filename to use to keep classification.')

args = parser.parse_args()

paper = Paper(args.scan_paper_src, args.scan_paper_dest,
            os.path.join(args.scan_paper_src, args.dict),
            os.path.join(args.scan_paper_src, args.db))

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_CREATE  # watched events

# We create the database at first based on path hierarchy inside
# scan_paper_src: that way, it is easy(ier) to move files around
# than write category of documents in a text database.
if args.create_db:
    paper.create_db(ocr = False)
elif args.create_db_with_ocr:
    paper.create_db(ocr = True)
else:
    # Main use: as a daemon which waits for new file
    # to classify. (TODO implement inotify rather than
    # loop...). Use 'supervisor' to deal with boot start..etc.
    # Here we start by teaching svm, and then we loop forever.
    paper.teach_svm()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(os.path.join(args.scan_paper_src, "unknown"), mask, rec = True)

    notifier.loop()
