from nltk.tokenize import WordPunctTokenizer

from treetaggerwrapper import NotTag, Tag, TreeTagger
from treetaggerwrapper import make_tags

from Stemmer import Stemmer

from sklearn import svm

from re import match, search
import codecs
import collections

class paperSort:
	def __init__(self, dictionary_path):
		# Get french stopwords from nltk
		#self.french_stopwords = set(stopwords.words('french'))
		# Load dictionary and remove accents (can't name table column with
		# utf-8 character apparently).
		with codecs.open(dictionary_path, 'r', 'utf-8') as fdict:
			self.dictionary = fdict.read().split()
		self.dictionary = sorted([word.lower() for word in self.dictionary])
		self.tokenizer = WordPunctTokenizer()
		self.tagger = TreeTagger(TAGLANG='fr', TAGDIR='/disk/nfs/wip/treetagger')
		self.stemmer = Stemmer('french')
		self.clf = svm.SVC()

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

		# set is unordered collection of *distinct* objects, then
		# this removes duplicates. TODO remove duplicates later,
		# we need them for now for learning/categorizing.
		# return list(set(list_lemma))
		return list_lemma

	def get_stems(self, lemmas):
		# dict_stem = { lemma:  self.stemmer.stemWord(lemma) for lemma in lemmas }
		# dict removes duplicates this way...
		#Stem = collections.namedtuple('Stem', 'stem count')
		#dict_stem = {}
		#for lem in lemmas:
		#	st = self.stemmer.stemWord(lem)
		#	if lem in dict_sem:
		#		dict_stem[lem].count += 1
		#	else
		#		dict_stem[lem].stem = st
		list_stem = [ self.stemmer.stemWord(lem) for lem in lemmas ]

		return list_stem

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
