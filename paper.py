#!/usr/bin/env python

from sklearn import svm
import os
from os.path import isfile, join
from os import listdir
import errno
import subprocess
from paperDB import paperDB
from paperSort import paperSort


def get_scanned_doc_path():
    # Path to scanned documents
    scanned_doc_path = "/tmp/sort_scan_image/"
    # mkdir -p in case it does not exist.
    try:
        os.makedirs(scanned_doc_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(scanned_doc_path):
            pass
        else:
            raise

    return scanned_doc_path


def teach_svm(paper_db, dictionary):
    print(dictionary)
    # Get the list of vectors from db.
    (list_sample_vector, list_category) = paper_db.table_get_all_vector_for_svm("training_sample", dictionary)
    print(list_sample_vector)
    print(list_category)
    clf = svm.SVC()
    if len(list_sample_vector) != 0:
        clf.fit(list_sample_vector, [i[0] for i in list_category])

    return clf


def init():
    scanned_doc_path = get_scanned_doc_path()
    paper_sort = paperSort("dictionary")
    paper_db = paperDB("test.db", paper_sort.dictionary)
    paper_db.table_create("training_sample")
    # Init svm with database
    clf = teach_svm(paper_db, paper_sort.dictionary)

    return [scanned_doc_path, paper_db, paper_sort, clf]


def loop(scanned_doc_path, paper_db, paper_sort, clf):
    # Get all the scanned images.
    scanned_doc_list = [f for f in listdir(scanned_doc_path) if isfile(join(scanned_doc_path, f))]

    # Apply the whole process to any file in it !
    for file_name in scanned_doc_list:
        # TODO use regexp here.
        if "scan_and_sort" not in file_name and "tmp" not in file_name:
            continue

        print("Converting %s" % file_name)
        res = subprocess.call(["convert", scanned_doc_path + file_name,
                               scanned_doc_path + file_name + ".jpg"])

        print("OCRing %s" % file_name)
        res = subprocess.call(["tesseract",	scanned_doc_path + file_name,
                               scanned_doc_path + file_name,
                               "-l fra"])
        if (res == 0):
            print("Tesseract on %s ok." % file_name)
            paper_sort.svm_sort(clf, scanned_doc_path + file_name, paper_db)


# TODO a class of scan_and_sort
[scanned_doc_path, paper_db, paper_sort, clf] = init()
# while (1):
loop(scanned_doc_path, paper_db, paper_sort, clf)

