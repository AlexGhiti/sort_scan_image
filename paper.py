#!/usr/bin/env python

import time
from os.path import isfile, join
from os import listdir
import re
import subprocess
import argparse

from sklearn import svm

from paperDB import paperDB
from paperSort import paperSort


class Paper:
    # scan_doc_dest may be an url or a local dest.
    def __init__(self, scan_doc_src, scan_doc_dest,
                    dict_path, db_path):
        self.scan_doc_src = scan_doc_src
        self.scan_doc_dest = scan_doc_dest
        self.paper_sort = paperSort(self.dict_path)
        self.paper_db = paperDB(self.db_path, self.paper_sort.dictionary)
        self.paper_db.table_create(self.db_path)


    def create_db():
        pass

    def teach_svm():
        print(self.paper_sort.dictionary)
        # Get the list of vectors from db.
        (list_sample_vector, list_category) =
            paper_db.table_get_all_vector_for_svm(
                    "training_sample", self.paper_sort.dictionary)
        print(list_sample_vector)
        print(list_category)

        if len(list_sample_vector) != 0:
            self.paper_sort.clf.fit(list_sample_vector,
                                    [i[0] for i in list_category])

    def parse_scan_doc(ocr):
        # Get all the scanned images.
        scan_doc_list = [f for f in listdir(self.scan_doc_src) if isfile(join(self.scan_doc_src, f))]

        # Apply the whole process to any file in it !
        for fname in scan_doc_list:
            if re.match("scan_and_sort.*tmp$", fname) is None:
                continue

            # print("Converting %s" % fname)
            # res = subprocess.call(["convert", scan_doc_src + fname,
            #                        scan_doc_src + fname + ".jpg"])

            print("OCRing %s" % fname)
            res = subprocess.call(["tesseract",	self.scan_doc_src + fname,
                                   self.scan_doc_src + fname,
                                   "-l fra"])
            if res == 0:
                print("Tesseract on %s ok." % fname)
                if not ocr:
                    paper_sort.svm_sort(self.scan_doc_src + fname, self.paper_db)
                    # TODO add copying file to its dest.

parser = argparse.ArgumentParser(description = 'Process grep_and_sed arguments.')
# Create db from existing OCRised doc.
parser.add_argument('--create_db', action='store_true',
                    help = 'Old string to search and replace.')
# Use this option to OCRise all doc to use in create_db option.
parser.add_argument('--ocr', action='store_true',
                    help = 'Old string to search and replace.')
parser.add_argument('--scan_doc_src', default = "/tmp/sort_scan_image/",
                    help = 'Old string to search and replace.')
parser.add_argument('--scan_doc_dest', default = "/tmp/sort_scan_image_dest/",
                    help = 'Old string to search and replace.')
parser.add_argument('--dict', default = "/tmp/sort_scan_image/",
                    help = 'Old string to search and replace.')
parser.add_argument('--db', default = "/tmp/sort_scan_image/",
                    help = 'Old string to search and replace.')

args = parser.parse_args()

paper = Paper(args.scan_doc_src, args.scan_doc_dest, args.dict, args.db)

# We create the database at first based on path hierarchy inside
# scan_doc_src: that way, it is easy(ier) to move files around
# than write category of documents in a text database.
if args.create_db:
    paper.create_db()
elif args.ocr:
    paper.parse_doc_scan(True)
else
    while (1):
        paper.parse_doc_scan(False)
        time.sleep(1)



