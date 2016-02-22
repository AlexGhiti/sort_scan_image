#!/usr/bin/env python

import time
import os
import re
import subprocess
import argparse

from paperDB import paperDB
from paperSort import paperSort


class Paper:
    # scan_paper_dest may be an url or a local dest.
    def __init__(self, scan_paper_src, scan_paper_dest,
                    dict_path, db_path):
        self.scan_paper_src = scan_paper_src
        self.scan_paper_dest = scan_paper_dest
        self.paper_sort = paperSort(dict_path)
        self.paper_db = paperDB(db_path, self.paper_sort.dictionary)
        self.paper_db.table_create("paper")

    def ocr(self, fname):
            #print("%s" % ["convert", fname, "{0}.jpg".format(fname)])
            #res = subprocess.call(["convert", fname,
            #                                "{0}.jpg".format(fname)])
            print("*** OCRing %s..." % fname)
            res = subprocess.call(["tesseract", "{0}".format(fname),
                                                "{0}".format(fname),
                                                "-l fra"])
            if res != 0:
                print("*** Tesseract failed on %s." % fname)

    def parse_ocr_paper(self, ocr_paper_path):
        # 1/ Open OCRised file and read its content.
        content = self.paper_sort.read_content_ocr_file(ocr_paper_path)
        if (content is None):
            return None

        # 2/ Tokenisation of the file content.
        list_content_word = self.paper_sort.tokenise_content(content)

        # 3/ Generate vector of words according to current directory.
        vect_res = self.paper_sort.get_vector_list_word(self.paper_sort.dictionary, list_content_word)

        return vect_res

    # Do 'cleanup' on ocr text and adds the result to db.
    def add_to_db_with_category(self, ocr_paper_path, category):
        vect_res = self.parse_ocr_paper(ocr_paper_path);
        self.paper_sort.add_vector_db(self.paper_db, vect_res, ocr_paper_path,
                                        category)

    def add_to_db_with_svm(self, ocr_paper_path):
        vect_res = self.parse_ocr_paper(ocr_paper_path);
        svm_category = self.paper_sort.clf.predict(vect_res)
        print("Le nouveau document est : %s" % svm_category)
        self.paper_sort.add_vector_db(self.paper_db, vect_res, ocr_paper_path,
                                        svm_category)

    # Returns the list of .tmp file only.
    def get_paper_list(self):
        paper_list = []
        for root, directories, filenames in os.walk(self.scan_paper_src):
            paper_list.extend([os.path.join(root, f) for f in filenames if re.match(".*tmp$", f) ])

        return paper_list

    # May be to discuss, but I prefer sorting documents in
    # directory by hand rather than writing a document giving
    # the category name of each document.
    def create_db(self, ocr):
        self.paper_db.table_create("paper")
        paper_list = self.get_paper_list()
        for p in paper_list:
            if ocr:
                self.ocr(p)

            self.add_to_db_with_category(p + ".txt",
                                        p.split('/')[-2])


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
parser.add_argument('--dict', default = "/tmp/sort_scan_image/dictionary",
                    help = 'Full path to the dictionary to use to classify.')
parser.add_argument('--db', default = "/tmp/sort_scan_image/test.db",
                    help = 'Full path to the db to use to keep classification.')

args = parser.parse_args()

paper = Paper(args.scan_paper_src, args.scan_paper_dest, args.dict, args.db)

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
    while (1):
        paper_list = paper.get_paper_list()
        for p in paper_list:
            paper.add_to_db_with_svm(p + ".txt")
        time.sleep(1)



