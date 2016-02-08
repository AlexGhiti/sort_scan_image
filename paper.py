#!/usr/bin/env python

import time
import os
import re
import subprocess
import argparse

from paperDB import paperDB
from paperSort import paperSort


class Paper:
    # scan_doc_dest may be an url or a local dest.
    def __init__(self, scan_doc_src, scan_doc_dest,
                    dict_path, db_path):
        self.scan_doc_src = scan_doc_src
        self.scan_doc_dest = scan_doc_dest
        self.paper_sort = paperSort(dict_path)
        self.paper_db = paperDB(db_path, self.paper_sort.dictionary)
        self.paper_db.table_create("paper")

    # May be to discuss, but I prefer sorting documents in
    # directory by hand rather than writing a document giving
    # the category name of each document.
    def table_populate(self, ocr):
        print("*** Creating table %s..." % "paper")
        self.paper_db.table_create("paper")

        for root, directories, filenames in os.walk(self.scan_doc_src):
            for filename in filenames:
                fpath = os.path.join(root, filename)
                ocr_done = 0
                if ocr and re.match("scan_and_sort.*tmp$",  filename):
                    self.ocr_doc(fpath)
                    ocr_done = 1

                if ocr_done or re.match("scan_and_sort.*tmp.txt$", filename):
                    print("*** Adding %s to the database..." % fpath)
                    self.paper_sort.svm_sort(fpath, self.paper_db, True)

    def ocr_doc(self, fname):
            #print("%s" % ["convert", fname, "{0}.jpg".format(fname)])
            #res = subprocess.call(["convert", fname,
            #                                "{0}.jpg".format(fname)])
            print("*** OCRing %s..." % fname)
            res = subprocess.call(["tesseract", "{0}".format(fname),
                                                "{0}".format(fname),
                                                "-l fra"])
            if res != 0:
                print("*** Tesseract failed on %s." % fname)

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
# Create db from existing OCRised doc.
parser.add_argument('--create_db', action='store_true',
                    help = 'Create db from already ocrised doc.')
# Use this option to OCRise all doc to use in create_db option.
parser.add_argument('--create_db_with_ocr', action='store_true',
                    help = 'Create db from raw image (ie. : call ocr).')
parser.add_argument('--scan_doc_src', default = "/tmp/sort_scan_image/",
                    help = 'With create_db* = true: path where documents are '
                           'already classified.\n'
                            'With create_db* = false: path where freshly '
                            'scanned docs are copied after scan.')
parser.add_argument('--scan_doc_dest', default = "/tmp/sort_scan_image_dest/",
                    help = 'Only used with create_db* = false: root path (local '
                            'or remote) where classified docs must be sent '
                            '(Your server for example).')
parser.add_argument('--dict', default = "/tmp/sort_scan_image/dictionary",
                    help = 'Full path to the dictionary to use to classify.')
parser.add_argument('--db', default = "/tmp/sort_scan_image/test.db",
                    help = 'Full path to the db to use to keep classification.')

args = parser.parse_args()

paper = Paper(args.scan_doc_src, args.scan_doc_dest, args.dict, args.db)

# We create the database at first based on path hierarchy inside
# scan_doc_src: that way, it is easy(ier) to move files around
# than write category of documents in a text database.
if args.create_db:
    paper.table_populate(False)
elif args.create_db_with_ocr:
    paper.table_populate(True)
else:
    # Main use: as a daemon which waits for new file
    # to classify. (TODO implement inotify rather than
    # loop...).
    while (1):
        paper.parse_scan_doc()
        time.sleep(1)



