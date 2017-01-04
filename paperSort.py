import codecs
import treetaggerwrapper
from sklearn import svm
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
		self.tagger = treetaggerwrapper.TreeTagger(TAGLANG='fr', TAGDIR='/disk/nfs/wip/treetagger')
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

	# Tokenise content with TreeTagger.
	def tokenise_content(self, content):
		list_remove_token = [ "ADV", "DET.*", "INT", "KON", "PRO.*", "PRP.*", 
							"PUN.*", "SENT.*" ]

		# 1/ Start with applying treetagger algorithm.
		tags = self.tagger.tag_text(content)

		# 2/ Returns list of named tuple Tag.
		named_tags = treetaggerwrapper.make_tags(tags)

		return named_tags

	def get_vector_list_word(self, dictionary, list_content_word):
		dict_res = {}

		for dict_word in dictionary:
			dict_res[dict_word] = 0
			for word in list_content_word:
				if dict_word in word:
					dict_res[dict_word] += 1

		# Get an ordered list of tuples corresponding to the dict vect_res.
		list_tuple_ordered = sorted(list(dict_res.items()), key=lambda v: v[0])
		# Get an ordered dict from the list above
		dict_vect = collections.OrderedDict(list_tuple_ordered)
		# Finally get an ordered list of values :)
		values_dict = list(dict_vect.values())

		return values_dict

# TODO Take care that some words are truncated by tokenisation
# and bad ocr: try to fusion two consecutive words to see if
# better results. http://blog.fouadhamdi.com/introduction-a-nltk/
