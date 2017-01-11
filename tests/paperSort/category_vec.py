import sys, os
from re import match, search
from pprint import pprint
sys.path.append(os.path.abspath(os.path.join('..', '..')))
from paperSort import paperSort
import nltk

# psy, smile contrat, 
except_file = [ "Salaire_30122016-125838.txt", "Medical_19122016-194520.txt", "Salaire_11122016-171444.txt" ]

def __get_category_path(path):
        category_path = [] 
        for root, directories, filenames in os.walk(path):
            category_path += [ os.path.join(root, dir) for dir in directories ]

        return category_path

# list_category_path = __get_category_path("/disk/owncloud/AlexGhiti/files/common/papers/")
# { category name: category path }
category = { cat.split("/")[-1]: cat for cat in __get_category_path("/disk/owncloud/AlexGhiti/files/common/papers/") }

s = paperSort("/disk/nfs/wip/sort_scan_image/dictionaries")

set_lemmas = set()
set_stems = set()

# USELESS FOR NOW.
# # Number of occurences of one lemma/stem by category.
# cat_count_lemmas = {}
# cat_count_stems = {}

# Number of occurences of one lemma/stem by paper.
paper_count_lemmas = {}
paper_count_stems = {}

# Number of time a lemma/stem appears at least once
# in a paper.
lemmas_paper_nb = {}
stems_paper_nb = {}

# Total number of papers in learning corpus.
paper_nb = 0

for cat, path in category.items():
	# cat_count_lemmas[cat] = {}
	# cat_count_stems[cat] = {}
	for r, d, filenames in os.walk(path):
		for f in filenames:
			if match(".*txt", f) and f not in except_file:
				paper_nb += 1
				paper_name = search("(.+?).txt", f).group(1) 
				#print(paper_name)

				text = s.read_content_ocr_file(os.path.join(r, f))
				tokens = s.get_tokens(text)
				tokens_no_sw = s.remove_stopwords(tokens)
				tags = s.get_tags(tokens_no_sw)
	
				list_lemmas = s.get_lemmas(tags)
				paper_count_lemmas[paper_name] = s.get_words_count(list_lemmas)	

				list_stems = s.get_stems(list_lemmas)
				paper_count_stems[paper_name] = s.get_words_count(list_stems)

				# Compute : the number of time a lemma appears in a paper
				# and add each new stem to the global set of stems that will
				# be used to describe space for the classifier (ie the coordinates
				# of each documents).
				for lem in paper_count_lemmas[paper_name]:
					if lem in lemmas_paper_nb:
						lemmas_paper_nb[lem] += 1
						# Add lem to global set of stems only if it appears at least
						# in two documents (that should remove lots of bad ocr text)
						if lem not in set_lemmas:
							set_lemmas.add(lem)
					else:
						lemmas_paper_nb[lem] = 1

				for st in paper_count_stems[paper_name]:
					if st in stems_paper_nb:
						stems_paper_nb[st] += 1
						# Add lem to global set of stems only if it appears at least
						# in two documents (that should remove lots of bad ocr text)
						if st not in set_stems:
							set_stems.add(st)
					else:
						stems_paper_nb[st] = 1

#print("======== STEMMAS =================")
#for word in set_stems:
#	print(word)

#print("========== LEMMAS ================")
for word in set_lemmas:
	if s.lemma_in_dictionary(word):
		print(word)

s.lemmas_corpus = sorted([ lem for lem in set_lemmas if s.lemma_in_dictionary(lem) ])
s.paper_nb = paper_nb


# 
# 	print("******", path, "******")
# 	print("LEMMA")
# 	nb_lemma = 0
# 	for lem, count in cat_count_lemmas[cat].items():
# 		if count > 15:
# 			print(lem, count)
# 			nb_lemma += 1
# 	
# 	print("STEM")
# 	nb_stem = 0
# 	for st, count in cat_count_stems[cat].items():
# 		if count > 15:
# 			print(st, count)
# 			nb_stem += 1
# 
# 	print("nb_lemma ", nb_lemma)
# 	print("nb_stem ", nb_stem)
# 	print("********************")
# 
# 
# print("==================================")
# print("==================================")
# print("==================================")
# print("======== STEMMAS =================")
# for word in set_stems:
# 	print(word)
# 
# print("LENGTH => ", len(set_stems))
# 
# print("==================================")
# print("==================================")
# print("==================================")
# print("========== LEMMAS ================")
# for word in set_lemmas:
# 	print(word)
# 
# print("LENGTH => ", len(set_lemmas))
