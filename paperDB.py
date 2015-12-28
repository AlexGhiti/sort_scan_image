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

    def table_create(self, tab_name):
        str_list_dict = ' INTEGER ,'.join(self.dictionary) + " INTEGER"
        sql_cmd = "CREATE TABLE IF NOT EXISTS %s (%s)" % (tab_name, str_list_dict)

        print("\nCreate : " + sql_cmd)

        self.db_cursor.execute(sql_cmd)
        self.db_conn.commit()

    def table_delete(self, tab_name):
        self.db_cursor.execute("DROP TABLE " + tab_name)
        self.db_conn.commit()

    def table_update(tab_name, dictionary):
        return

    def table_add_column(tab_name):
        return

    def table_add_vector(self, tab_name, vect):
        str_list_value = ','.join(str(v) for v in vect)
        sql_cmd = "INSERT INTO %s VALUES (%s)" % (tab_name, str_list_value)

        print("\nVector : " + sql_cmd)
        self.db_cursor.execute(sql_cmd)
        self.db_conn.commit()

        return
