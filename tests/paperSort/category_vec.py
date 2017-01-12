import sys, os
from re import match, search
sys.path.append(os.path.abspath(os.path.join('..', '..')))
from paperSort import paperSort

# psy, smile contrat, 
except_file = [ "Salaire_30122016-125838.txt", "Medical_19122016-194520.txt", "Salaire_11122016-171444.txt" ]

def __get_category_path(path):
        category_path = [] 
        for root, directories, filenames in os.walk(path):
            category_path += [ os.path.join(root, dir) for dir in directories ]

        return category_path

# { category name: category path }
category = { cat.split("/")[-1]: cat for cat in __get_category_path("/disk/owncloud/AlexGhiti/files/common/papers/") }

s = paperSort("/disk/nfs/wip/sort_scan_image/dictionaries")

# Add papers to learning corpus.
for cat, path in category.items():
	for r, d, filenames in os.walk(path):
		for f in filenames:
			if match(".*txt", f) and f not in except_file:
				paper_name = search("(.+?).txt", f).group(1)
				s.add_paper_to_corpus(paper_name, cat, os.path.join(r, f))

# Start learning from this corpus.
s.learn(debug = True)
