#!/usr/bin/env python

import sqlite3

# One instance of paperDB deals with one database (as much table
# as wanted yet).
class paperDB:

    def __init__(self, db_path, dictionary):
        # Attribute definition
        # Path where are stored papers. (eg Owncloud data path).
        # Maybe useless...
        self.dictionary = dictionary
        # Necessary
        try:
            self.db_conn = sqlite3.connect(db_path)
            self.db_cursor = self.db_conn.cursor()
        except sqlite3.OperationalError:
            print('Erreur la table existe déjà')
        except Exception as e:
            print("Erreur")
            conn.rollback()
            # raise e

    # Table contains vector for svm learning, the filename of the image and
    # the category in which it is stored.
    def table_create(self, tab_name):
        print("*** Creating table %s..." % "paper", end = "", flush = True)

        str_list_dict = ' INTEGER ,'.join(self.dictionary) + " INTEGER"
        str_list_dict += ', file_name STRING'
        str_list_dict += ', category STRING'
        # sql_cmd = "CREATE TABLE IF NOT EXISTS %s (%s)" % (tab_name, str_list_dict)
        sql_cmd = "CREATE TABLE %s (%s)" % (tab_name, str_list_dict)

        try:
            self.db_cursor.execute(sql_cmd)
            self.db_conn.commit()
        except sqlite3.OperationalError:
            print("Already exists. OK.")
        except Exception as e:
            print("Error creating table. (%s)", e.__class__.__name__)
            self.db_conn.rollback()
        else:
            print("OK.")

    def table_delete(self, tab_name):
        print("*** Deleting table %s..." % "paper")
        self.db_cursor.execute("DROP TABLE IF EXISTS " + tab_name)
        self.db_conn.commit()

    def table_update(tab_name, dictionary):
        return

    def table_add_column(tab_name):
        return

    # Raw accessors to database
    def table_add_vector(self, tab_name, vect, file_name, category):
        print("*** Adding file %s into category \"%s\" (table \"%s\")..." % (file_name,
                                                                category,
                                                                "paper"), end = "",
                                                                flush = True)
        str_list_value = ','.join(str(v) for v in vect)
        sql_cmd = "INSERT INTO %s VALUES (%s, \"%s\", \"%s\")" % (tab_name,
                                                                  str_list_value,
                                                                  file_name,
                                                                  category)

        try:
            self.db_cursor.execute(sql_cmd)
            self.db_conn.commit()
        except Exception as e:
            print("Error inserting vector. (%s)", e.__class__.__name__)
            self.db_conn.rollback()
        else:
            print("OK.")

        return

    def table_get_all_vector(self, tab_name):
        sql_cmd = "SELECT * FROM %s" % tab_name
        self.db_cursor.execute(sql_cmd)

        return self.db_cursor.fetchall()

    def table_get_all_vector_for_svm(self, tab_name, dictionary):
        # First retrieve numerical vector parts to give as
        # support vectors. And then retrieve their category.
        # That's why requests are ordered, because I make it
        # in two steps (TODO check if not possible to make it
        # one request).
        str_list_word = ','.join(dictionary)
        sql_cmd = "SELECT %s FROM %s v ORDER BY file_name"
        sql_cmd %= (str_list_word, tab_name)
        self.db_cursor.execute(sql_cmd)
        svm_vector = self.db_cursor.fetchall()

        sql_cmd = "SELECT category FROM %s v ORDER BY file_name"
        sql_cmd %= tab_name
        self.db_cursor.execute(sql_cmd)
        list_category = self.db_cursor.fetchall()

        return (svm_vector, list_category)

    # Smart accessors to database
    def table_get_vector_by_name(self, tab_name, file_name):
        sql_cmd = "SELECT category FROM %s v WHERE v.file_name = \"%s\"" % (tab_name,
                                                                 file_name)
        self.db_cursor.execute(sql_cmd)

        return self.db_cursor.fetchall()

    # List of useful query
    def file_name_exists(self, tab_name, file_name):
        sql_cmd = "SELECT file_name FROM %s WHERE file_name = '%s'" % (tab_name,
                                                                file_name)
        self.db_cursor.execute(sql_cmd)
        return (self.db_cursor.fetchone() != None)


    def add_vector_db(self, vect_res, path, svm_category):
        # Here we directly insert the vector in the database with the
        # result of svm algo. Anyway, a notification will be sent to user with
        # the URL to the image and the category found. If the category is wrong,
        # the user will be able to modify it.
        # TODO Send the url, the list of category (html mail) so that in one click
        # we can send a notif to this program to change the category.
        file_name = path.split('/')[-1]
        if self.file_name_exists("paper", file_name) is False:
            self.table_add_vector("paper", vect_res, file_name,
                                        svm_category)
