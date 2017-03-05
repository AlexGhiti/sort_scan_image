import numpy as np
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram, linkage

from matplotlib import pyplot as plt
import pygraphviz as pgv

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
		self.label_clustering(Z, len(self.papers_corpus))

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
						annotate_above = 0,
						max_d = 1.5,
			)

			plt.show()

	# N = nb of papers.
	# Z(i, 0) + Z(i, 1) form new cluster i + N
	# distance between Z(i, 0) and Z(i, 1) = Z(i, 2)
	# Z(i, 3) = number of papers in new cluster i + N
	def label_clustering(self, Z, N):
		# vect contains tfc vectors all the clusters, not just
		# single papers.
		vect = [None] * (N + len(Z)) 

		# Initialize cluster_labels list.
		for i in range(N + len(Z)):
			self.cluster_labels.append([])

		# Graphviz init.
		tree = pgv.AGraph(directed = True)

		# Go through the tree to compute vect and self.cluster_labels.
		self.nb_clusters = 0
		self.label_clusters_in_tree(Z, N + len(Z) - 1, N, vect, tree)
		if self.nb_clusters < len(Z):
			print("[WARNING] Missing clusters, clusters: ", self.nb_clusters)
		else:
			print("clusters: ", self.nb_clusters)

		# Output graphviz file.
		tree.layout(prog = "dot")
		tree.draw("tree.png")


	# Go through the tree, and compute the representing words when going back up
	# the tree
	# Z: output of linkage (index base is 0 !)
	# i: ith element in Z
	def label_clusters_in_tree(self, Z, num_cluster, N, vect, tree):
		# If already computed, returns the result.
		if vect[num_cluster] != None:
			return vect[num_cluster]

		self.nb_clusters += 1

		idx_z = num_cluster - N
		left = int(Z[idx_z, 0])
		right = int(Z[idx_z, 1])
		dist_lr = Z[idx_z, 2]
		print(num_cluster, ": ", left, right, dist_lr)

		if left >= N:
			vect[left] = self.label_clusters_in_tree(Z, left, N, vect, tree)
		else:
			vect[left] = self.papers_corpus[left].tfc

		if right >= N:
			vect[right] = self.label_clusters_in_tree(Z, right, N, vect, tree)
		else:
			vect[right] = self.papers_corpus[right].tfc

		# Here we compute the most 3 (TODO) significant dimensions
		# that both children have in common
		# and returns a tfc vector representing the cluster i.
		# TODO at the moment, it is just a mean between both
		# vector, find better if there is ?
		vect[num_cluster] = self.compute_like(num_cluster, vect[left], vect[right])
		
		# Create graphviz view.
		tree.add_node(num_cluster)
		node_cluster = tree.get_node(num_cluster)
		node_cluster.attr["label"] = str(num_cluster) + " " + " ".join(self.cluster_labels[num_cluster])
		if left not in tree.nodes():
			tree.add_node(left)
		if left not in tree.nodes():
			tree.add_node(right)
		tree.add_edge(num_cluster, left)
		tree.add_edge(num_cluster, right)

		return vect[num_cluster]

	# Returns the 3 composantes whose distance is max.
	def compute_like(self, num_cluster, vect_left, vect_right):
		# Retains the 3 closest points between vect_left and vect_right.
		# idx is the index in vect_left/right and thus gives the associated word
		# dist is the corresponding distance.
		dist = [ { "idx": -1, "dist": 0 },
				{ "idx": -1, "dist": 0 },
				{ "idx": -1, "dist": 0 } ]

		vect_tfc_cluster = []
		for idvect, (l, r) in enumerate(zip(vect_left, vect_right)):
			# TODO Is this mean good ? 
			vect_tfc_cluster.append((l + r) / 2)
			# TODO distance function should be the same used by linkage ?
			dist_lr = abs(l - r) 
			for d in dist:
				if dist_lr > d["dist"]:
					d["dist"] = dist_lr
					d["idx"] = idvect
					break

		for d in dist:
			self.cluster_labels[num_cluster].append(self.lemmas_corpus[d["idx"]])

		print("num_cluster ", num_cluster, num_cluster + 33, ": ", self.cluster_labels[num_cluster]) 

		return vect_tfc_cluster 

	#def node_label_func(self, id):
	#	if id < len(self.papers_corpus):
	#		return self.papers_corpus[id].name
	#	else:
	#		return self.cluster_labels[id]

	# https://joernhees.de/blog/2015/08/26/scipy-hierarchical-clustering-and-dendrogram-tutorial/
	def fancy_dendrogram(self, *args, **kwargs):
		max_d = kwargs.pop('max_d', None)
		if max_d and 'color_threshold' not in kwargs:
			kwargs['color_threshold'] = max_d
		annotate_above = kwargs.pop('annotate_above', 0)
		
		#ddata = dendrogram(*args, leaf_label_func=self.node_label_func, **kwargs)
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
