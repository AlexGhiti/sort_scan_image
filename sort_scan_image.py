#!/usr/bin/env python

# from sklearn import svm
from os import listdir
from os.path import isfile, join
from nltk.corpus import stopwords
#import subprocess
from paperDB import paperDB
from unidecode import unidecode
import codecs
import collections

def svm_init():
    return

# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
def svm_sort(path, paper_db):
    vect_res = {}

    with codecs.open(path, 'r', 'utf-8') as fin, codecs.open(path + '.tk', 'w', 'utf_8') as fout:
        content = fin.read()
        # I could use nltk to have a better tokenisation. TODO
        list_word_with_stop = content.split()
        # Now, I need to remove the maximum of 'senseless' words and
        # remove the accents and lower useful words.
        # 1/ Start with stopword
        list_word = [unidecode(word) for word in list_word_with_stop if word.lower() not in french_stopwords]
        for word in list_word:
            fout.write(word + "\n")
        # 2/ Incoherent words from OCR.
        # TODO
        # Comparison using simhash
        # TODO
        for dict_word in dictionary:
            vect_res[dict_word] = 0
            for word in list_word:
                if dict_word in word.lower():
                    vect_res[dict_word] += 1


        print(vect_res)
        paper_db.table_add_vector("test", collections.OrderedDict(sorted(vect_res.items(), key=lambda v: v[0])).values())


# Get french stopwords from nltk
french_stopwords = set(stopwords.words('french'))

# Load dictionary and remove accents (can't name table column with
# utf-8 character apparently).
with codecs.open("dictionary", 'r', 'utf-8') as fdict:
    dictionary = fdict.read().split()
dictionary = sorted([unidecode(word) for word in dictionary])

print("Dictionary : ")
print(dictionary)
# Path to scanned documents
scanned_doc_path = "/home/aghiti/sample_sorting_svm/"

# Get all the scanned images.
scanned_doc_list = [f for f in listdir(scanned_doc_path) if isfile(join(scanned_doc_path, f))]
for file_name in scanned_doc_list:
        if "scan_and_sort" not in file_name:
            scanned_doc_list.remove(file_name)

paper_db = paperDB(scanned_doc_path + "test.db", dictionary)
paper_db.table_delete("test")
paper_db.table_create("test")

svm_sort(scanned_doc_path + "scan_and_sort0.tmp.txt", paper_db) #, dictionary)

# # Launch tesseract on it.
# for file_name in scanned_doc_list:
#         res = 1
#         print(file_name)
#         #if file_name.endswith("tmp"):
#         #    print("Converting %s" % file_name)
#         #    res = subprocess.call(["convert", file_name, file_name + ".jpg"])
#
#         #res = subprocess.call(["tesseract",	scanned_doc_path + file_name,
#         #                       scanned_doc_path + file_name,
#         #                       "-l fra"])
#         if (res != 0 and "txt" in file_name):
#                 print("Tesseract on %s ok\n" % file_name)
#                 svm_sort(scanned_doc_path + file_name)
#         else:
#                 print("Tesseract on %s ok\n" % file_name)
