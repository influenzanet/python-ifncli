import sqlite3
import os
from typing import List


class DbError(Exception):
    pass

class SqliteDb:
    """
    Simple helper class to manage a little Sqlite database. 
    It wraps sqlite db to expose simpler API
    """    
    def __init__(self, db_path, allow_create=True):
        if db_path != ':memory:':
            db_exists = os.path.exists(db_path)
        else:
            db_exists = False 
        self.db = sqlite3.connect(db_path)
        if not db_exists and not allow_create:
            raise DbError("Database '%s' doesnt exists" % (db_path))
        self.setup(not db_exists)

    def setup(self, empty_db:bool):
        """
            This method can be overriden by child class to create the empty db
            empty_db is True if db has just been created
        """
        pass
    
    def table_exists(self, table_name):
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'".format(table_name=table_name)
        r = self.fetch_one(query)
        return r is not None and len(r) == 1

    def fetch_one(self, query, data=()): 
        cur = self.db.cursor() 
        res = cur.execute(query, data)
        r = res.fetchone()
        cur.close()
        return r
    
    def fetch_all(self, query, data=()): 
        cur = self.db.cursor()
        try:
            res = cur.execute(query, data)
            return res.fetchall()
        finally:
            cur.close()
        
    def execute(self, query, data=(), commit=True):
        cur = self.db.cursor()
        cur.execute(query, data)
        if commit:
            self.db.commit()
        cur.close()

    def execute_many(self, query, data:List, commit=True):
        cur = self.db.cursor()
        cur.executemany(query, data)
        if commit:
            self.db.commit()
        cur.close()

    def cursor(self):
        return self.db.cursor()
