from nltk.tokenize import WordPunctTokenizer
from nltk.corpus import stopwords
from treetaggerwrapper import NotTag, Tag, TreeTagger
from treetaggerwrapper import make_tags
from Stemmer import Stemmer

from math import sqrt, log

from unidecode import unidecode
import codecs

from collections import OrderedDict 

from pprint import pprint

from re import match, search

class Paper:
	french_stopwords = set(stopwords.words('french'))
	tokenizer = WordPunctTokenizer()
	tagger = TreeTagger(TAGLANG='fr', TAGDIR='/disk/nfs/wip/treetagger')
	stemmer = Stemmer('french')

	# At init, lemmas_count is initialized because it depends only
	# on the paper itself.
	# tfc vector othrwise depends on the corpus of papers and must 
	# be called later with necessary infos !
	def __init__(self, name, path, lemmas_count = {}, tfc = []):
		self.name = name
		self.path = path
		# Dict representing ALL lemmas, not only from dictionaries.
		if len(lemmas_count) == 0:
			self.set_lemmas_count()
		else:
			self.lemmas_count = lemmas_count
		self.tfc = tfc

	def read_paper(self, path):
		try:
			fin = open(path, 'r')
		except IOError:
			print(("Problem opening file : %s" % path))
			return None
		else:
			with fin:
				content = fin.read()

		return content

	def remove_stopwords(self, tokens):
		return [ tk for tk in tokens if tk not in Paper.french_stopwords ]

	# Problem with WordPunctTokenizer is that it splits 
	# web addresses whereas they are very relevant...
	def get_tokens(self, content):
		return Paper.tokenizer.tokenize(content)

	def get_tags(self, tokens):
		list_ntoken = [ "ADV", "DET.*", "INT", "KON", "NUM", "PRO.*", "PRP.*",	"PUN.*", "SENT.*" ]

		# 1/ Lower case every token 
		lower_tokens = [ tk.lower() for tk in tokens ]

		# 2/ Taggetize everything
		tags = Paper.tagger.tag_text(lower_tokens)
		named_tags = make_tags(tags)

		# 3/ And select only words that are not in list_remove_token
		#		 to keep only significant words (I assume..).
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
		list_stem = [ Paper.stemmer.stemWord(lem) for lem in lemmas ]

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

	# Extend the lemmas_count tab to take into account words
	# from other papers and have a complete vector for learning.
	def extend_lemmas_count(self, lemmas_corpus):
		for lem in lemmas_corpus:
			if lem not in self.lemmas_count:
				self.lemmas_count[lem] = 0

	# http://www.memoireonline.com/12/09/2917/m_Algorithmes-dapprentissage-pour-la-classification-de-documents0.html#toc1
	# lemmas_paper_nb = # dict(lemma: paper_count) nb of papers in which lemma appears.
	# Those formulas can be found in http://theses.univ-lyon2.fr/documents/lyon2/2003/jalam_r/pdf/jalam_r-TH.2.pdf
	def __tfidf(self, len_corpus, count, paper_count):
		return (log(1 + count) * log(len_corpus / paper_count))

	def __tfc(self, tfidf, sqrt_sigma_tfidf):
		return tfidf / sqrt_sigma_tfidf

	# Compute TFC
	# Note: TFC depends on corpus informations, number of papers in the corpus
	# and number of papers in which each lemma appears.
	def compute_vector_tfc_paper(self, lemmas_corpus, lemmas_paper_nb):
		dict_tfidf = {} 
		for lem in lemmas_corpus:
			dict_tfidf[lem] = self.__tfidf(len(lemmas_corpus), self.lemmas_count[lem], lemmas_paper_nb[lem])

		# Compute the denominateur for TFC encoding.
		sqrt_sigma_tfidf = 0
		for l, v in dict_tfidf.items():
			sqrt_sigma_tfidf += v * v
		sqrt_sigma_tfidf = sqrt(sqrt_sigma_tfidf)

		# Compute TFC vector that represents the paper :)
		dict_tfc = {}
		for lem in lemmas_corpus:
			dict_tfc[lem] = self.__tfc(dict_tfidf[lem], sqrt_sigma_tfidf)

		# Sort by alphabetical order on lemmas.
		# Get an ordered list of tuples corresponding to the dict vect_res.
		tuple_ordered_dict_tfc = sorted(list(dict_tfc.items()), key=lambda v: v[0])
		# Get an ordered dict from the list above
		ordered_dict_tfc = OrderedDict(tuple_ordered_dict_tfc)
		# Finally get an ordered list of values :)
		self.tfc = list(ordered_dict_tfc.values())

	def set_lemmas_count(self):
		# Read file.
		text = self.read_paper(self.path)
		# 1/ Tokenize.
		tokens = self.get_tokens(text)
		# 2/ Remove stopwordself.
		tokens_no_sw = self.remove_stopwords(tokens)
		# 3/ Tag.
		tags = self.get_tags(tokens_no_sw)
		# 4/ Lemmatize.
		list_lemmas = self.get_lemmas(tags)
		# 5/ Store for each paper a dict { lemma: count }.
		self.lemmas_count = self.get_lemmas_count(list_lemmas)
		if len(self.lemmas_count) == 0:
			print("WARNING: ", self.name, " does not contain any lemma in the corpus !")


