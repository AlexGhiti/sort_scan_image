#!/usr/bin/env python



import os
import re
import subprocess
import shutil
import argparse
from unidecode import unidecode
import pyinotify
import datetime

import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from paperDB import paperDB
from paperSort import paperSort

# "tmp" extension is necessary to identify scanned doc from categorized doc.
class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        if re.match(".*tmp$", event.pathname):
            if (os.path.isfile(event.pathname + ".txt") == False):
                paper.ocr(event.pathname)
            (category, new_paper_name) = paper.add_to_db_with_svm(event.pathname + ".txt")
            if (category, new_paper_name) == (None, None):
                return
            paper.move_doc(event.pathname, category, new_paper_name)
            paper.teach_svm()

    def process_IN_MOVED_TO(self, event):
        # Do something only when moving papers images.
        if re.match(".*_[0-9]*-[0-9]*$", event.pathname):
            from_category = event.src_pathname.split('/')[-2]
            to_category = event.pathname.split('/')[-2]
            paper.send_mail_result(from_category, to_category, event.pathname)
            # Update database and SVM
            # 1/ Database only if not from unknown (which means it is just after scan
            #    and then it is not in db yet, the "unknown" case is handled by
            #    create inotify hook).
            if args.no_use_db:
                return

            if from_category != "unknown":
                vect_res = paper.paper_db.table_remove_vector("paper",  
                                                event.src_pathname.split('/')[-1])
                if vect_res == -1:
                    return

                paper.paper_db.table_add_vector("paper", vect_res,
                                                event.pathname.split('/')[-1],
                                                to_category)

            # 2/ SVM in any case. TODO
            paper.teach_svm()

class Paper:
    # scan_paper_dest may be an url or a local dest.
    def __init__(self, scan_paper_src, scan_paper_dest,
                    dict_path):
        self.scan_paper_src = scan_paper_src
        self.scan_paper_dest = scan_paper_dest
        self.paper_sort = paperSort(dict_path)
        self.paper_db = paperDB(self.paper_sort.dictionary)
        self.log_file = open("log.txt", "w")

    # TODO move that to paper_sort, all called functions are from there
    def __parse_ocr_paper(self, ocr_paper_path):
        # 1/ Open OCRised file and read its content.
        content = self.paper_sort.read_content_ocr_file(ocr_paper_path)
        if (content is None):
            return None

        # 2/ Tokenisation of the file content.
        list_content_word = self.paper_sort.tokenise_content(content)

        # 3/ Generate vector of words according to current directory.
        vect_res = self.paper_sort.get_vector_list_word(self.paper_sort.dictionary, list_content_word)

        return vect_res

    def __get_category_list(self):
        category_list = []
        for root, directories, filenames in os.walk(self.scan_paper_src):
            category_list.extend(directories)

        return category_list

    # Returns the list of .tmp file only.
    def __get_paper_list(self):
        paper_list = []
        for root, directories, filenames in os.walk(self.scan_paper_src):
            if not "unknown" in root:
                paper_list.extend([os.path.join(root, f) for f in filenames if f != "dictionary" and not "txt" in f ])

        return paper_list
    
    def ocr(self, fname):
        #print("%s" % ["convert", fname, "{0}.jpg".format(fname)])
        #res = subprocess.call(["convert", fname,
        #                                "{0}.jpg".format(fname)])
        print("*** OCRing %s..." % fname)
        res = subprocess.call(["tesseract", "{0}".format(fname),
                                            "{0}".format(fname),
                                            "-l fra"],
                                            stdout = self.log_file,
                                            stderr = self.log_file)
        if res != 0:
            print("*** Tesseract failed on %s." % fname)

    # TODO: Sending mail with html obliges us to use dashboard or any server...Ok or not?
    # Request to modify category: /move/to_category/ANY_category/new_paper_name
    def send_mail_result(self, from_category, to_category, new_paper_path):
        print("*** Sending notification mail to %s..." % "alexandre@ghiti.fr", end = "")

        new_paper_name = new_paper_path.split('/')[-1]
        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        with open("pass", "r") as f:
            content_pass = f.readlines()

        server = content_pass[0].strip('\n')
        port = content_pass[1].strip('\n')
        user = content_pass[2].strip('\n')
        mdp = content_pass[3].strip('\n')

        msg_root = MIMEMultipart('mixed')
        msg_root['Subject'] = "%s -> %s" % (from_category, to_category)
        msg_root['From'] = user
        msg_root['To'] = "alexandre@ghiti.fr"

        # 1/ HTML part to easily chose new category.
        text = "This paper has been moved from category \"%s\" to the category \"%s\".\n" % (from_category, to_category)
        text += "If this seems like an error for you, please choose below the right "
        text += "category."
        # Create a link for each category
        html = """\
                <html>
                    <head></head>
                    <body>\n
                """
        category_list = self.__get_category_list()
        for category in category_list:
            if category != to_category:
                html += "       <a href=\"http://192.168.0.12:3030/move/"
                html +=                        to_category    + "/"
                html +=                        category      + "/"
                html +=                        new_paper_name
                html +=                       "\">" + category + "</a><br>"
        
        html += """    </p>
                    </body>
                </html>
                """
        msg_root.attach(MIMEText(text, 'plain'))
        msg_root.attach(MIMEText(html, 'html'))

        # 2/ Send the paper in the mail.
        # Convert the pnm to jpg (and maybe shrink to save space).
        # Moved paper path.
        ret = subprocess.call(["convert", new_paper_path,
                                        "-resize", "20%",
                                        new_paper_path + ".jpg"])
        if ret != 0:
            print("Error converting paper (%d)." % ret)
            return
      
        with open(new_paper_path + ".jpg") as fpaper_jpg:
            mail_jpg = MIMEImage(fpaper_jpg.read())
            fpaper_jpg.close()
            msg_root.attach(mail_jpg)

        # Remove the jpg.
        os.remove(new_paper_path + ".jpg")

        # 3/ Effectively send the mail.
        try:
            s = smtplib.SMTP_SSL(server, port, None, None, None, 10)
            s.login(user, mdp)
            ret = s.sendmail(user, ["alexandre@ghiti.fr"], msg_root.as_string())
            s.quit()
        except smtplib.SMTPException as e:
            print("Error sending email (%s)." % e.__class__.__name__)
        except Exception as e:
            print(e.message)
        else:
            print("Ok.")

    # Move and rename files at the same time.
    def move_doc(self, paper_path, category, new_paper_name):
        print("*** Moving paper %s..." % paper_path, end = "")

        try:
            if args.no_use_db:
                new_paper_name = "test_" + new_paper_name
            
            if os.path.isfile(os.path.join(self.scan_paper_dest, category, new_paper_name)):
                print("Error, file already exists !")
                return 

            shutil.move(paper_path, os.path.join(self.scan_paper_dest, category, new_paper_name))
            shutil.move(paper_path + ".txt", os.path.join(self.scan_paper_dest, category, new_paper_name + ".txt"))
        except Exception as e:
            print("Error moving paper (%s: %s)." % (e.__class__.__name__, e.message))
        else:
            print("Ok.")
    
    def __format_time(self):
      return datetime.datetime.now().strftime('%d%m%Y-%H%M%S')

    # TODO this is not the right place for those functions;
    # Do 'cleanup' on ocr text and adds the result to db.
    # Returns None in case of error, new_paper_name otherwise.
    def add_to_db_with_category(self, ocr_paper_path, category):
        vect_res = self.__parse_ocr_paper(ocr_paper_path);
        # Rename the file to remain consistent
        new_paper_name = "%s_%s" % (category, self.__format_time())
        # Check if a file does have this name already;
        paper_suffix = ""
        num_paper_suffix = 1
        while (os.path.isfile(os.path.join(self.scan_paper_dest, category, new_paper_name + paper_suffix))):
            paper_suffix = "_%d" % num_paper_suffix
            num_paper_suffix += 1
        new_paper_name = new_paper_name + paper_suffix
        print(new_paper_name)

        if args.no_use_db:
            return new_paper_name

        if self.paper_db.table_add_vector("paper", vect_res, new_paper_name, category):
            return None

        # TODO Pass paper_path rather than ocr_paper_path, it is not normal
        # to add .txt in the call and remove it here. NOT PRETTY AT ALL.
        self.move_doc(ocr_paper_path.rsplit(".txt")[0], category, new_paper_name)

        return new_paper_name

    def add_to_db_with_svm(self, ocr_paper_path):
        vect_res = self.__parse_ocr_paper(ocr_paper_path)
        svm_category = unidecode(self.paper_sort.clf.predict(vect_res)[0])
        new_paper_name = "%s_%s" % (svm_category, self.__format_time())
        # Check if a file does have this name already;
        paper_suffix = ""
        num_paper_suffix = 1
        while (os.path.isfile(os.path.join(self.scan_paper_dest, svm_category, new_paper_name + paper_suffix))):
            paper_suffix = "_%d" % num_paper_suffix
            num_paper_suffix += 1
        new_paper_name = new_paper_name + paper_suffix

        if args.no_use_db:
            return (svm_category, new_paper_name)

        if self.paper_db.table_add_vector("paper", vect_res, new_paper_name, svm_category):
            return (None, None)

        return (svm_category, new_paper_name)

    # May be to discuss, but I prefer sorting documents in
    # directory by hand rather than writing a document giving
    # the category name of each document.
    def create_db(self, ocr):
        if self.paper_db.table_create("paper"):
            return

        paper_list = self.__get_paper_list()
        for p in paper_list:
            if ocr:
                self.ocr(p)
            
            category = p.split('/')[-2]
            new_paper_name = self.add_to_db_with_category(p + ".txt", category)

    # TODO Reteach after all modifs in db (especially when a 
    # new paper has been classified with classification from the user !
    def teach_svm(self):
        # Get the list of vectors from db.
        (list_sample_vector, list_category) = self.paper_db.table_get_all_vector_for_svm(
                                                "paper", self.paper_sort.dictionary)

        if len(list_sample_vector) != 0:
            self.paper_sort.clf.fit(list_sample_vector, [ i[0] for i in list_category ])

        print("*** Teaching svm...Ok.")


parser = argparse.ArgumentParser(description = 'Process grep_and_sed arguments.')
# Create db from existing OCRised paper.
parser.add_argument('--create_db', action='store_true',
                    help = 'Create db from already ocrised paper.')
# Use this option to OCRise all paper to use in create_db option.
parser.add_argument('--create_db_with_ocr', action='store_true',
                    help = 'Create db from raw image (ie. : call ocr).')
parser.add_argument('--no_use_db', action='store_true',
                    help = 'Do not add paper to db (allows to test without messing'
                            'the database).')
parser.add_argument('--scan_paper_src', default = "/tmp/sort_scan_image/",
                    help = 'With create_db* = true: path where documents are '
                           'already classified.\n'
                            'With create_db* = false: path where freshly '
                            'scanned papers are copied after scan.')
parser.add_argument('--scan_paper_dest', default = "",
                    help = 'Only used with create_db* = false: root path (local '
                            'or remote) where classified papers must be sent '
                            '(Your server for example).')
parser.add_argument('--dict', default = "dictionary",
                    help = 'Dictionary filename to use to classify.')

args = parser.parse_args()

if args.scan_paper_dest == "":
    args.scan_paper_dest = args.scan_paper_src

paper = Paper(args.scan_paper_src, args.scan_paper_dest,
            os.path.join(args.scan_paper_src, args.dict))

wm = pyinotify.WatchManager()
# IN_MOVED_FROM must be watched to get src_pathname in IN_MOVED_TO.
mask = pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM

# We create the database at first based on path hierarchy inside
# scan_paper_src: that way, it is easy(ier) to move files around
# than write category of documents in a text database.
if args.create_db:
    paper.create_db(ocr = False)
elif args.create_db_with_ocr:
    paper.create_db(ocr = True)
else:
    # Main use: as a daemon which waits for new file
    # to classify.
    # Here we start by teaching svm, and then we loop forever.
    paper.teach_svm()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(args.scan_paper_src, mask, rec = True)

    notifier.loop()
