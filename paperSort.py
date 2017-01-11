from nltk.tokenize import WordPunctTokenizer
from nltk.corpus import stopwords

from treetaggerwrapper import NotTag, Tag, TreeTagger
from treetaggerwrapper import make_tags

from Stemmer import Stemmer

from sklearn import svm

from re import match, search
from os import walk, path
import codecs
import unicodedata
from unidecode import unidecode
import collections

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
		self.paper_nb = 0

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
	# TODO unique function with get_stem_count
	# words is no good.
	def get_words_count(self, lwords):
		dict_cnt = {}

		for word in lwords:
			if word in dict_cnt:
				dict_cnt[word] += 1
			else:
				dict_cnt[word] = 1

		return dict_cnt

	# TFC codage !
	# http://www.memoireonline.com/12/09/2917/m_Algorithmes-dapprentissage-pour-la-classification-de-documents0.html#toc1
	# paper_count_lemmas = # dict(lemma: count) in current paper.
	# lemmas_paper_nb = # dict(lemma: paper_count) nb of papers in which lemma appears.
	def __tfidf(self, count, paper_count):
		return (log(1 + count) * log(self.paper_nb / paper_count))

	def __tfc(self, tfidf, sigma_sqrt_tfidf):
		return tfidf / sigma_sqrt_tfidf

	def get_vector_tfc_paper(self, paper_count_lemmas, lemmas_paper_nb):
		# Compute TFxIDF
		dict_tfidf = {}
		for lem in self.lemmas_corpus:
			if lem in paper_count_lemmas:
				dict_tfidf[lem] = self.__tfidf(paper_count_lemmas[lem], lemmas_paper_nb[lem])
			else
				dict_tfidf[lem] = 0

		# Compute the denominateur for TFC encoding.
		sigma_sqrt_tfidf = 0
		for l, v in dict_tfidf:
			sigma_sqrt_tfidf += v
		sigma_sqrt_tfidf = sqrt(sigma_sqrt_tfidf)

		# Compute TFC vector that represents the paper :)
		dict_tfc = {}
		for lem in self.lemmas_corpus:
			dict_tfc[lem] = self.__tfc(dict_tfidf[lem], sigma_sqrt_tfidf)

		return sorted([ v for k, v in dict_tfc ])
		
	def lemma_in_dictionary(self, lem):
		return lem in self.dictionary

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
