import numpy as np
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram, linkage

from matplotlib import pyplot as plt

from re import match, search
from os import walk, path
import codecs
from unidecode import unidecode
from collections import namedtuple

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
		# TODO: What is that for ?!
		# self.lemmas_corpus_in_dict = []
		# Learning corpus infos (list of Paper objects).
		self.papers_corpus = [] 
		# Number of time a lemma appears at least once
		# in a paper.
		self.lemmas_paper_nb = {}
		# A list of 3-dimension vector containing 3 words representing each
		# cluster obtained from linkage.
		self.cluster_labels = []

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
		# 1/ Create data vector for AgglomerativeClustering.
		X = []
		Yname = []
		for p in self.papers_corpus:
			X.append(p.tfc)
			Yname.append(p.name)

		# 2/ Fit with AgglomerativeClustering
		#model = AgglomerativeClustering(linkage = 'complete', affinity = 'cosine', n_clusters = 1)
		#model.fit(X)
		#ii = itertools.count(len(self.papers_corpus))
		#tree = [{'node_id': next(ii), 'left': x[0], 'right':x[1]} for x in model.children_]

		# 2bis/ Use scipy library, returns easier/more infos than scikit-learn.
		Z = linkage(X, "complete")
		print(Z)

		# 3/ Label every node (except leaves) in the resulting tree.
		self.label_clustering(Z)

		if debug == True:
			# calculate full dendrogram
			plt.figure(figsize=(25, 10))
			plt.title('Hierarchical Clustering Dendrogram')
			plt.xlabel('sample index')
			plt.ylabel('distance')
			self.fancy_dendrogram(
					    Z,
					    leaf_rotation=90.,  # rotates the x axis labels
					    leaf_font_size=8.,  # font size for the x axis labels
						#labels = Yname,
						annotate_above = 0.5,
						max_d = 1.5,
			)

			plt.show()

	# n = nb of papers.
	# Z(i, 0) + Z(i, 1) form new cluster i + n
	# distance between Z(i, 0) and Z(i, 1) = Z(i, 2)
	# Z(i, 3) = number of papers in new cluster i + n
	def label_clustering(self, Z):
		# Start with head of tree which is node number n + len(Z)
		# but which is in the last element of Z (TODO Check)
		vect = {}
		self.label_clusters_in_tree(Z, n + len(Z), len(self.papers_corpus), vect)

	# Go through the tree, and compute the representing words when going back up
	# the tree
	# Z: output of linkage
	# i: ith element in Z
	def label_clusters_in_tree(self, Z, i, N, vect):
		# If already computed, returns the result.
		if i in vect:
			return vect[i]

		left = Z[i, 0]
		right = Z[i, 1]

		if left > N:
			vect[left] = self.label_clusters_in_tree(self, Z, left - N)
		else:
			# Returns the vect that represents best a paper: simply returns its
			# TFC vector :)
			# TODO Check if lists are indexed at 0 or 1...??
			return self.papers_corpus[left].tfc

		if right > N:
			vect[right] = self.label_clusters_in_tree(self, Z, right - N)
		else:
			return self.papers_corpus[right].tfc

		# Here we compute the most 3 (TODO) significant dimensions
		# that both children have in common
		# and returns a tfc vector representing the cluster i.
		# TODO at the moment, it is just a mean between both
		# vector, find better if there is ?
		vect[i] = compute_like(i, vect[left], vect[right])

		return vect[i]

	# Returns the 3 composantes whose distance is max.
	def compute_like(self, num_cluster, vect_left, vect_right):
		Dist = namedtuple(Dist, "idx dist")

		# Retains the 3 closest points between vect_left and vect_right.
		# idx is the index in vect_left/right and thus gives the associated word
		# dist is the corresponding distance.
		dist = [ Dist(idx = -1, dist = 0),
				 Dist(idx = -1, dist = 0),
				 Dist(idx = -1, dist = 0) ]

		vect_tfc_cluster = []
		for idvect, l, r in enumerate(zip(vect_left, vect_right)):
			# TODO Is this mean good ? 
			vect_tfc_cluster.append((l + r) / 2)
			# TODO distance function should be the same used by linkage ?
			dist_lr = abs(l - r) 
			for iddist, d in enumerate(dist):
				if dist_lr > d.dist:
					dist[iddist].dist = dist_lr
					dist[iddist].idx = idvect
					break
			
		for d in dist:
			self.cluster_labels[num_cluster].append(self.lemmas_corpus[d.idx])

		print("num_cluster ", num_cluster, ": ", self.cluster_labels[num_cluster]) 

		return vect_tfc_cluster 

	# https://joernhees.de/blog/2015/08/26/scipy-hierarchical-clustering-and-dendrogram-tutorial/
	def fancy_dendrogram(self, *args, **kwargs):
	    max_d = kwargs.pop('max_d', None)
	    if max_d and 'color_threshold' not in kwargs:
	        kwargs['color_threshold'] = max_d
	    annotate_above = kwargs.pop('annotate_above', 0)
	
	    ddata = dendrogram(*args, **kwargs)
	
	    if not kwargs.get('no_plot', False):
	        plt.title('Hierarchical Clustering Dendrogram (truncated)')
	        plt.xlabel('sample index or (cluster size)')
	        plt.ylabel('distance')
	        for i, d, c in zip(ddata['icoord'], ddata['dcoord'], ddata['color_list']):
	            x = 0.5 * sum(i[1:3])
	            y = d[1]
	            if y > annotate_above:
	                plt.plot(x, y, 'o', c=c)
	                plt.annotate("%.3g" % y, (x, y), xytext=(0, -5),
	                             textcoords='offset points',
	                             va='top', ha='center')
	        if max_d:
	            plt.axhline(y=max_d, c='k')
	    return ddata	

# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
