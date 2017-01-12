from nltk.tokenize import WordPunctTokenizer
from nltk.corpus import stopwords

from treetaggerwrapper import NotTag, Tag, TreeTagger
from treetaggerwrapper import make_tags

from Stemmer import Stemmer

from sklearn import svm
from math import sqrt, log

from re import match, search
from os import walk, path
import codecs
import unicodedata
from unidecode import unidecode

from collections import namedtuple

Paper = namedtuple('Paper', [ 'category', 'path' ])

class paperSort:
	def __init__(self, dictionary_path):
		# Get french stopwords from nltk
		self.french_stopwords = set(stopwords.words('french'))
		# All dictionaries are in dictionaries/.
		self.dictionary = []
		for r, d, filenames in walk(dictionary_path):
			for f in filenames:
				with codecs.open(path.join(r, f), 'r', 'iso8859') as fdict:
					self.dictionary += fdict.readlines()
		# Sort dictionary and remove accents, too much words are correct except
		# an accent.
		self.dictionary = sorted([ unidecode(word.lower().rstrip()) for word in self.dictionary ])
		self.tokenizer = WordPunctTokenizer()
		self.tagger = TreeTagger(TAGLANG='fr', TAGDIR='/disk/nfs/wip/treetagger')
		self.stemmer = Stemmer('french')
		self.clf = svm.SVC()

		# Sorted list of significant words for the corpus: this vector is used
		# for describing vectors for SVM.
		self.lemmas_corpus = []
		# Learning corpus infos.	
		# { paper_name: 'namedtuple Paper' }
		self.papers_corpus = {} 
		# TODO change those variable names, I can't remember them !!
		# Number of occurences of one lemma by paper in the learning corpus.
		# { lemma: count in paper }
		self.lemmas_count_paper = {}
		# Number of time a lemma appears at least once
		# in a paper.
		self.lemmas_paper_nb = {}
		# Vector that will feed SVM for each paper in corpus.
		self.paper_tfc_vector = {}

	def add_paper_to_corpus(self, paper_name, category, path):
		p = Paper(category = category, path = path)
		self.papers_corpus[paper_name] = p

	# TODO Use psort et pdb
	def read_content_ocr_file(self, path):
		try:
			#fin = codecs.open(path, 'r', 'utf-8')
			fin = open(path, 'r')
		except IOError:
				print(("Problem opening file : %s" % path))
				return None
		else:
				with fin:
						content = fin.read()

		return content

	def remove_stopwords(self, tokens):
		return [ tk for tk in tokens if tk not in self.french_stopwords ]

	# http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string
	def __remove_accents(self, lemmas):
		return [ lem for lem in unicodedata.normalize('NFD', ' '.join(lemmas)) if unicodedata.category(lem) != 'Mn' ]

	# Problem with WordPunctTokenizer is that it splits 
	# web addresses whereas they are very relevant...
	def get_tokens(self, content):
		return self.tokenizer.tokenize(content)

	def get_tags(self, tokens):
		list_ntoken = [ "ADV", "DET.*", "INT", "KON", "NUM", "PRO.*", "PRP.*",	"PUN.*", "SENT.*" ]

		# 1/ Lower case every token 
		lower_tokens = [ tk.lower() for tk in tokens ]

		# 2/ Taggetize everything
		tags = self.tagger.tag_text(lower_tokens)
		named_tags = make_tags(tags)

		# 3/ And select only words that are not in list_remove_token
		#	 to keep only significant words (I assume..).
		sig_named_tags = []
		for tag in named_tags:
			if type(tag) is NotTag:
				sig_named_tags += [ tag ]
				continue

			rm_token = False

			for ntoken in list_ntoken:
				if match(ntoken, tag.pos):
					rm_token = True
					break
			
			if rm_token == False:
				sig_named_tags += [ tag ]

		return sig_named_tags

	def get_lemmas(self, tags):
		# Remove @card@ and split 'xy|zw' in two
		list_lemma = []
		for tag in tags:
			if type(tag) is not NotTag and tag.lemma != "@card@":
				spl = tag.lemma.split('|')
				if len(spl) > 1:
					if len(spl[0]) > 1:
						list_lemma += [ spl[0] ]
					if len(spl[1]) > 1:
						list_lemma += [ spl[1] ]
				elif len(spl) == 1:
					if len(spl[0]) > 1:
						list_lemma += [ tag.lemma ]

		# extract lemma from "<rep*** text="XXXX" />
		regexp = "<rep.*text=\"(.+?)\" />"
		list_lemma += [ search(regexp, tag.what).group(1) for tag in tags if type(tag) is NotTag ]

		# TODO I'm scared TreeTagger would not work correctly without
		# accent, so I remove them now.
		list_lemma_no_accent = [ unidecode(lem) for lem in list_lemma ]

		return list_lemma_no_accent

	def get_stems(self, lemmas):
		list_stem = [ self.stemmer.stemWord(lem) for lem in lemmas ]

		return list_stem

	# content: content of a paper from get_lemma.
	# returns dict { lemma: count }
	def get_lemmas_count(self, lwords):
		dict_cnt = {}

		for word in lwords:
			if word in dict_cnt:
				dict_cnt[word] += 1
			else:
				dict_cnt[word] = 1

		return dict_cnt

	# TFC codage !
	# http://www.memoireonline.com/12/09/2917/m_Algorithmes-dapprentissage-pour-la-classification-de-documents0.html#toc1
	# lemmas_count_paper = # dict(lemma: count) in current paper.
	# lemmas_paper_nb = # dict(lemma: paper_count) nb of papers in which lemma appears.
	# Those formulas can be found in http://theses.univ-lyon2.fr/documents/lyon2/2003/jalam_r/pdf/jalam_r-TH.2.pdf
	def __tfidf(self, count, paper_count):
		return (log(1 + count) * log(len(self.papers_corpus) / paper_count))

	def __tfc(self, tfidf, sqrt_sigma_tfidf):
		return tfidf / sqrt_sigma_tfidf

	def get_vector_tfc_paper(self, pname):
		# Compute TFxIDF
		dict_tfidf = {}
		for lem in self.lemmas_corpus:
			dict_tfidf[lem] = self.__tfidf(self.lemmas_count_paper[pname][lem], self.lemmas_paper_nb[lem])

		# Compute the denominateur for TFC encoding.
		sqrt_sigma_tfidf = 0
		for l, v in dict_tfidf.items():
			sqrt_sigma_tfidf += v * v
		sqrt_sigma_tfidf = sqrt(sqrt_sigma_tfidf)

		# Compute TFC vector that represents the paper :)
		dict_tfc = {}
		for lem in self.lemmas_corpus:
			dict_tfc[lem] = self.__tfc(dict_tfidf[lem], sqrt_sigma_tfidf)

		return sorted([ v for k, v in dict_tfc.items() ])
		
	def lemma_in_dictionary(self, lem):
		return lem in self.dictionary

	def __get_category(self):
		set_category = set()
		for pname, p in self.papers_corpus.items():
			if p.category not in set_category:
				set_category.add(p.category)

		return set_category

	# TODO serialize the output of that, can't learn at each 
	# launch, too long.
	def learn(self, debug = False):
		# Get the lemmas that represent the corpus.
		for pname, p in self.papers_corpus.items():
			# Read file.
			text = self.read_content_ocr_file(p.path)
			# 1/ Tokenize.
			tokens = self.get_tokens(text)
			# 2/ Remove stopwordself.
			tokens_no_sw = self.remove_stopwords(tokens)
			# 3/ Tag.
			tags = self.get_tags(tokens_no_sw)
			# 4/ Lemmatize.
			list_lemmas = self.get_lemmas(tags)
			# 5/ Store for each paper a dict { lemma: count }.
			self.lemmas_count_paper[pname] = self.get_lemmas_count(list_lemmas)
			if len(self.lemmas_count_paper[pname]) == 0:
				print("WARNING: ", pname, " does not contain any lemma in the corpus !")
			# 6/ Store for each lemma in corpus the number of papers it appears in.
			#    And add the lemma to the global only if it appears at least in 2
			#    papers and in dictionaries.
			for lem in self.lemmas_count_paper[pname]:
				if lem in self.lemmas_paper_nb:
				    self.lemmas_paper_nb[lem] += 1
				    if lem not in self.lemmas_corpus and self.lemma_in_dictionary(lem):
				        self.lemmas_corpus += [ lem ]
				else:
				    self.lemmas_paper_nb[lem] = 1
			# 7/ Sort lemmas in corpus. 
			self.lemmas_corpus.sort()

		# Now we have all the lemmas in the corpus, we can compute the vectors
		# that represent each paper in the corpus and hand it to SVM.
		for pname, p in self.papers_corpus.items():
			# 1/ Extend lemmas_count_paper at all the lemmas in the corpus
			#    (until then it contained only its own lemmas).
			for lem in self.lemmas_corpus:
				if lem not in self.lemmas_count_paper[pname]:
					self.lemmas_count_paper[pname][lem] = 0
			# 2/ Generate TFC vector.	
			self.paper_tfc_vector[pname] = self.get_vector_tfc_paper(pname)
			 
			
		if debug == True:
			print(self.lemmas_corpus)
			print("Number of lemmas   : ", len(self.lemmas_corpus))
			print("Number of papers   : ", len(self.papers_corpus))
			cat = self.__get_category()
			print("Category : ", ' '.join(cat))
			print("Number of category : ", len(cat))
			for pname, p in self.papers_corpus.items():
				print(pname, p.category)
				print(self.paper_tfc_vector[pname])
			

	#def get_vector_list_word(self, dictionary, list_content_word):
	#	dict_res = {}

	#	for dict_word in dictionary:
	#		dict_res[dict_word] = 0
	#		for word in list_content_word:
	#			if dict_word in word:
	#				dict_res[dict_word] += 1

	#	# Get an ordered list of tuples corresponding to the dict vect_res.
	#	list_tuple_ordered = sorted(list(dict_res.items()), key=lambda v: v[0])
	#	# Get an ordered dict from the list above
	#	dict_vect = collections.OrderedDict(list_tuple_ordered)
	#	# Finally get an ordered list of values :)
	#	values_dict = list(dict_vect.values())

	#	return values_dict

# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
