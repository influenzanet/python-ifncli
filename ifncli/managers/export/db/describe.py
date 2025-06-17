
duckdb_available = False
try:
    import duckdb
    duckdb_available = True
except ImportError:
    pass

import sqlite3

class DatabaseDescriber:

    def __init__(self):
        self.columns = ['table']
        self.data = []
    
    def append(self, d:dict):
        o = {}
        for k, v in d.items():
            if not k in self.columns:
                self.columns.append(k)
            value = self.format_column(k, v)
            o[k] = value
        self.data.append(o)
    
    def query_columns(self, table_name:str):
        return []
    
    def format_column(self, column:str, value):
        return value

    def show(self):
        for row in self.data:
            r = []
            for column in self.columns:
                if column in row:
                    r.append("{}={}".format(column, row[column]))
            print(", ".join(r))

def describe_database(path, describer=None, debug=False):
    db = None
    for dbtype in ['sqlite', 'duckdb']:
        try:
            db = open_db(path, dbtype)
        except Exception as e:
            if debug:
                print("Opening as {} : {}", dbtype, e)
            continue
    if db is None:
        raise Exception("Unable to open database")
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if describer is None:
        describer = DatabaseDescriber()
    for table_name in tables:
        cursor = db.cursor()
        columns = ['count(*) as count_rows']
        if describer is not None:
            columns.extend(describer.query_columns(table_name))
        cursor.execute("SELECT {} FROM {}".format(','.join(columns), table_name))
        fields = [field_md[0] for field_md in cursor.description]
        row = cursor.fetchone()
        d = dict(zip(fields,row)) 
        d["table"] = table_name
        describer.append(d)
    return describer

def open_db(path, dbtype):
    if dbtype == 'sqlite':
        return sqlite3.connect(path)
    if dbtype == 'duckdb':
        if duckdb_available:
            return duckdb.connect(path)
    raise Exception("Unknown db type")

