#!/usr/bin/env python

import sqlite3

# One instance of paperDB deals with one database (as much table
# as wanted yet).
class paperDB:

    def __init__(self, db_path, dictionary):
        # Attribute definition
        # Path where are stored papers. (eg Owncloud data path).
        # Maybe useless...
        # Necessary
        self.db_conn = sqlite3.connect(db_path)
        self.db_cursor = self.db_conn.cursor()
        self.dictionary = dictionary

    # Table contains vector for svm learning, the filename of the image and
    # the category in which it is stored.
    def table_create(self, tab_name):
        str_list_dict = ' INTEGER ,'.join(self.dictionary) + " INTEGER"
        str_list_dict += ', file_name STRING'
        str_list_dict += ', category STRING'
        sql_cmd = "CREATE TABLE IF NOT EXISTS %s (%s)" % (tab_name, str_list_dict)

        self.db_cursor.execute(sql_cmd)
        self.db_conn.commit()

    def table_delete(self, tab_name):
        self.db_cursor.execute("DROP TABLE IF EXISTS " + tab_name)
        self.db_conn.commit()

    def table_update(tab_name, dictionary):
        return


    def table_add_column(tab_name):
        return

    # Raw accessors to database
    def table_add_vector(self, tab_name, vect, file_name, category):
        print("New vect ")
        print(vect)
        str_list_value = ','.join(str(v) for v in vect)
        sql_cmd = "INSERT INTO %s VALUES (%s, \"%s\", \"%s\")" % (tab_name,
                                                                  str_list_value,
                                                                  file_name,
                                                                  category)

        self.db_cursor.execute(sql_cmd)
        self.db_conn.commit()

        return

    def table_get_all_vector(self, tab_name):
        sql_cmd = "SELECT * FROM %s" % tab_name
        self.db_cursor.execute(sql_cmd)

        return self.db_cursor.fetchall()


    # Smart accessors to database
    def table_get_vector_by_name(self, tab_name, file_name):
        sql_cmd = "SELECT * FROM %s v WHERE v.file_name = %s" % (tab_name,
                                                                 file_name)
        self.db_cursor.execute(sql_cmd)

        return self.db_cursor.fetchall()

    # List of useful query
    def file_name_exists(self, tab_name, file_name):
        sql_cmd = "SELECT file_name FROM %s WHERE file_name = '%s'" % (tab_name,
                                                                file_name)
        self.db_cursor.execute(sql_cmd)
        return (self.db_cursor.fetchone() != None)
