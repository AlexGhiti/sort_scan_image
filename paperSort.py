import numpy as np
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram

from matplotlib import pyplot as plt

from re import match, search
from os import walk, path
import codecs
from unidecode import unidecode

import itertools

from pprint import pprint

from paper import Paper

# TODO Rename to paperCorpus ? Seems more appropriate
class paperSort:
	def __init__(self, dictionary_path):
		# All dictionaries are in dictionaries/.
		self.dictionary = []
		for r, d, filenames in walk(dictionary_path):
			for f in filenames:
				with codecs.open(path.join(r, f), 'r', 'iso8859') as fdict:
					self.dictionary += fdict.readlines()
		# Sort dictionary and remove accents, too much words are correct except
		# an accent.
		self.dictionary = sorted([ unidecode(word.lower().rstrip()) for word in self.dictionary ])
		# Sorted list of words from dictionary (!!) in the corpus.
		self.lemmas_corpus = []
		self.lemmas_corpus_in_dict = []
		# Learning corpus infos (list of Paper objects).
		self.papers_corpus = [] 
		# Number of time a lemma appears at least once
		# in a paper.
		self.lemmas_paper_nb = {}

	# Add paper that needs preprocessing.
	def add_raw_paper_to_corpus(self, paper_name, path):
		p = Paper(paper_name, path)
		self.papers_corpus.append(p)

	# Add paper whose tfc vector has already been computed (ie.
	# stored in database or other).
	def add_lemmatized_paper_to_corpus(self, paper_name, path, lemmas_count):
		p = Paper(paper_name, path, lemmas_count)
		self.papers_corpus.append(p)

	def add_tfc_paper_to_corpus(self, paper_name, path, tfc):
		p = Paper(paper_name, path, tfc = tfc)
		self.papers_corpus.append(p)

	def is_lemma_in_dictionary(self, lem):
		return lem in self.dictionary

	def __get_category(self):
		set_category = set()
		for pname, p in self.papers_corpus.items():
			if p.category not in set_category:
				set_category.add(p.category)

		return set_category

	# TODO serialize the output of that, can't learn at each 
	# launch, too long => USE DB.
	def learn(self, debug = False):
		# 1/ Get the lemmas that represent the corpus.
		for p in self.papers_corpus:
			# Store for each lemma in corpus the number of papers it appears in.
			# And add the lemma to the global only if it appears at least in 2
			# papers and in dictionaries.
			for lem in p.lemmas_count:
				if lem in self.lemmas_paper_nb:
				    self.lemmas_paper_nb[lem] += 1
				    if lem not in self.lemmas_corpus and self.is_lemma_in_dictionary(lem):
				        self.lemmas_corpus += [ lem ]
				else:
				    self.lemmas_paper_nb[lem] = 1

		# 2/ Sort lemmas in corpus. 
		self.lemmas_corpus.sort()

		# Now we have all the lemmas in the corpus, we can compute the vectors
		# that represent each paper in the corpus and hand it to classifier.
		# 3/ Extend lemmas_count_paper at all the lemmas in the corpus
		#    (until then it contained only its own lemmas).
		for p in self.papers_corpus:
			p.extend_lemmas_count(self.lemmas_corpus)

		# 4/ Generate TFC vector for each paper.	
		for p in self.papers_corpus:
			p.compute_vector_tfc_paper(self.lemmas_corpus, self.lemmas_paper_nb)
			
		if debug == True:
			print(self.lemmas_corpus)
			print("Number of lemmas   : ", len(self.lemmas_corpus))
			print("Number of papers   : ", len(self.papers_corpus))
			for p in self.papers_corpus:
				print(p.name, end = " ")

		# 5/ Give all the datas to clustering algo.
		self.fit_corpus(debug)

	def fit_corpus(self, debug):
		# Last, fit paper_tfc_vector !
		# 1/ Create a list from dictionary paper_tfc_vector.
		X = []
		Yname = []
		for p in self.papers_corpus:
			X.append(p.tfc)
			Yname.append(p.name)

		if debug == True:
			print("List to fit : ", X)

		# 2/ Fit with AgglomerativeClustering
		# Try with n_clusters = 1 and check the tree.
		model = AgglomerativeClustering(linkage = 'ward', n_clusters = 4)
		model.fit(X)
		ii = itertools.count(len(self.papers_corpus))
		tree = [{'node_id': next(ii), 'left': x[0], 'right':x[1]} for x in model.children_]
		if debug == True:
			pprint(tree)
			self.visualize(model, Yname)

	# Visualization from https://github.com/scikit-learn/scikit-learn/blob/70cf4a676caa2d2dad2e3f6e4478d64bcb0506f7/examples/cluster/plot_hierarchical_clustering_dendrogram.py
	def visualize(self, model, labels):
		plt.title('Hierarchical Clustering Dendrogram')
		self.plot_dendrogram(model, labels = labels)
		plt.show()

	def plot_dendrogram(self, model, **kwargs):
	    # Children of hierarchical clustering
	    children = model.children_
	
	    # Distances between each pair of children
	    # Since we don't have this information, we can use a uniform one for plotting
		# shape[0] => nb of vectors in children
		# shape[1] => vector dimension
		# arange => 0..shape[0]
	    distance = np.arange(children.shape[0])
		
	    # The number of observations contained in each cluster level
	    no_of_observations = np.arange(2, children.shape[0] + 2)
	
	    # Create linkage matrix and then plot the dendrogram
	    linkage_matrix = np.column_stack([children, distance, no_of_observations]).astype(float)
	
	    # Plot the corresponding dendrogram
	    dendrogram(linkage_matrix, **kwargs)

# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
