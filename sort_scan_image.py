#!/usr/bin/env python

# from sklearn import svm
from os import listdir
from os.path import isfile, join
from nltk.corpus import stopwords
# import subprocess
from paperDB import paperDB
from unidecode import unidecode
import codecs
import collections


def svm_init():
    return


def svm_content_ocr_file(path):
    try:
        fin = codecs.open(path, 'r', 'utf-8')
    except IOError:
        print("Problem opening file : %s" % path)
        return None
    else:
        with fin:
            content = fin.read()

    return content


# Tokenise content, remove accents, lower everything, remove stopwords and
# remove incoherent words coming from the ocr process.
def svm_tokenise_content(content):
    # I could use nltk to have a better tokenisation. TODO
    list_word_with_stop = content.split()
    # Now, I need to remove the maximum of 'senseless' words and
    # remove the accents and lower useful words.
    # 1/ Start with stopword
    list_word = [unidecode(word.lower()) for word in list_word_with_stop if word.lower() not in french_stopwords]
    # 2/ Incoherent words from OCR.
    # TODO

    return list_word


# TODO Comparison using simhash
def svm_vector_list_word(dictionary, list_content_word):
    vect_res = {}

    for dict_word in dictionary:
        vect_res[dict_word] = 0
        for word in list_content_word:
            if dict_word in word:
                vect_res[dict_word] += 1

    return vect_res


def svm_add_vector_db(vect_res, path, svm_category):
    # Here we directly insert the vector in the database with the
    # result of svm algo. Anyway, a notification will be sent to user with
    # the URL to the image and the category found. If the category is wrong,
    # the user will be able to modify it.
    # TODO Send the url, the list of category (html mail) so that in one click
    # we can send a notif to this program to change the category.
    file_name = path.split('/')[-1]
    # Get an ordered list of tuples corresponding to the dict vect_res.
    list_tuple_ordered = sorted(vect_res.items(), key=lambda v: v[0])
    # Get an ordered dict from the list above
    dict_vect = collections.OrderedDict(list_tuple_ordered)
    # Finally get an ordered list of values :)
    values_dict = dict_vect.values()
    if paper_db.file_name_exists("training_sample", file_name) is False:
        paper_db.table_add_vector("training_sample", values_dict,
                                    file_name,
                                    svm_category)


# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
def svm_sort(path, paper_db):
    # 1/ Open OCRised file and read its content.
    content = svm_content_ocr_file(path)
    if (content is None):
        return None

    # 2/ Tokenisation of the file content.
    list_content_word = svm_tokenise_content(content)

    # 3/ Generate vector.
    vect_res = svm_vector_list_word(dictionary, list_content_word)

    # 4/ Svm Magic :)
    # TODO Make svm magic here
    svm_category = "magic" # = svm_magic(vect_res)

    # 5/ Insert the vector with the category guessed by svm.
    svm_add_vector_db(vect_res, path, svm_category)


# Get french stopwords from nltk
french_stopwords = set(stopwords.words('french'))

# Load dictionary and remove accents (can't name table column with
# utf-8 character apparently).
with codecs.open("dictionary", 'r', 'utf-8') as fdict:
    dictionary = fdict.read().split()
dictionary = sorted([unidecode(word.lower()) for word in dictionary])

print("Dictionary : ")
print(dictionary)

# Path to scanned documents
scanned_doc_path = "/home/aghiti/sample_sorting_svm/sort_scan_image/"

# Get all the scanned images.
scanned_doc_list = [f for f in listdir(scanned_doc_path) if isfile(join(scanned_doc_path, f))]
for file_name in scanned_doc_list:
        if "scan_and_sort" not in file_name:
            scanned_doc_list.remove(file_name)

paper_db = paperDB(scanned_doc_path + "test.db", dictionary)

paper_db.table_create("training_sample")
# Get all vector from database if any
# print(paper_db.table_get_all_vector("training_sample"))

# Launch tesseract on it.
for file_name in scanned_doc_list:
        res = 1
        #if file_name.endswith("tmp"):
        #    print("Converting %s" % file_name)
        #    res = subprocess.call(["convert", file_name, file_name + ".jpg"])

        #res = subprocess.call(["tesseract",	scanned_doc_path + file_name,
        #                       scanned_doc_path + file_name,
        #                       "-l fra"])
        if (res != 0 and "txt" in file_name):
            print("Tesseract on %s ok." % file_name)
            svm_sort(scanned_doc_path + file_name, paper_db)
