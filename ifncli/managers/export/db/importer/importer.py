

import pandas as pd
import json
import duckdb
import os
from typing import Optional
from collections import OrderedDict
from .processor import BasePreprocessor
from .profile import ImporterProfile, Debugger
from .version_selector import VersionSelectorRule
from ..database import ExportDatabase, ExportMeta
from .base import SourceDataLoader, Writer

TYPE_COMPAT = {
    'int':['int','int32','int8','int64', 'float64','int16'],
    'text': ['str', 'object'],
    'varying': ['str', 'object'],
    'bool': ['bool', 'boolean'],
    'date': ['date', 'datetime64[ns]'],
    'timestamp with time zone': ['datetime64[ns]']
}

DuckTypePandaAlias = {
    'int64':'int8',
    'float64': 'float',
    'datetime64[ns]': 'TIMESTAMPTZ'
}

DEFAULT_COLUMNS = os.getenv('COLUMNS', 120)

def show_df(df: pd.DataFrame, max_width=None):
    """
        Show dataframe in a more compact form than pandas info()
    """
    if max_width is None:
        max_width = int(DEFAULT_COLUMNS)
    w = 0
    desc = []
    for column in df.columns:
        col = df[column]
        if isinstance(col, pd.Series):
            dtype = col.dtype
        else:
            dtype = type(col)
        s = "`{}` ({})".format(column, dtype)
        w = max(w, len(s))
        desc.append(s)
    width = w + 3
    cols = int(max_width / width)
    f = "| {:<" + str(width) + "} "
    c = 0
    for d in desc:
        print(f.format(d), end=" ")
        c += 1
        if c >= cols:
            print("")
            c = 0

class DuckDbWriter(Writer):
    """
        Writer to a duckdb database
    """
    
    def __init__(self, duckdb_file: str, table_name: str, debugger: Debugger, insert_mode:str="ignore"):
        super().__init__()
        self.conn = None
        self.duckdb_file = duckdb_file
        self.table_name = table_name
        self.first_batch = True
        self.insert_mode = insert_mode
        self.user_table = 'survey_surveyuser'
        self.debugger = debugger
        
    def debug(self, name):
        return self.debugger.has(name)

    def connect(self):
        if self.conn is not None:
            return self.conn
        self.conn = duckdb.connect(self.duckdb_file)  # ou ":memory:" pour en mémoire
        if self.has_table(self.table_name):
            self.first_batch = False
        if not self.has_table(self.user_table):
            self.execute("CREATE SEQUENCE survey_user_id_seq START 1")
            self.execute("CREATE TABLE {user_table} (id INTEGER DEFAULT nextval('survey_user_id_seq'), global_id TEXT)".format(user_table=self.user_table))
            self.execute("CREATE UNIQUE INDEX survey_user_global_id ON {user_table} (global_id)".format(user_table=self.user_table))     
        return self.conn
    
    def has_table(self,  table_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM information_schema.tables WHERE table_name = '{}'".format(table_name))
        r = cursor.fetchone()
        if r is None:
            return False
        return True
    
    def execute(self, query):
        """
            Excecute a statement
        """
        cursor = self.conn.cursor()
        r = cursor.execute(query)
        cursor.close()
        return r
         
    def update_index(self, table_name):
        query = 'INSERT INTO {user_table} (global_id) select global_id from "{table_name}" ON CONFLICT DO NOTHING'.format(user_table=self.user_table, table_name=table_name)
        r = self.conn.execute(query)
        return r.rowcount

    def table_schema(self):
        if not self.has_table(self.table_name):
            return {}
        table = self.conn.table(self.table_name)
        schema = {}
        for index, name in enumerate(table.columns):
            column_type = table.dtypes[index]
            schema[name] = column_type
        return schema
    
    def update_schema(self, df: pd.DataFrame):
        schema = self.table_schema()
        to_update = []
        columns = []
        for column in df.columns:
            columns.append(column)
            # Check if column in known
            if column in schema:
                continue
            dtype = df[column].dtype
            if dtype.name == "object":
                col_type = "text"
            else:
                if dtype.name in DuckTypePandaAlias:
                    col_type = DuckTypePandaAlias[dtype.name]
                else:
                    col_type = dtype.name
            to_update.append('ADD COLUMN "{}" {}'.format(column, col_type))
            
        if len(to_update) > 0:
            print("Adding columns :", to_update)
            for statement in to_update:
                self.conn.execute('ALTER TABLE "{}" {}'.format(self.table_name, statement))
        return columns

    def register_survey(self, survey_key: str, table_name: str):
        survey_table_name = "survey_response_table"
        if not self.table_exists(survey_table_name):
            query = 'CREATE TABLE {table_name} ("survey" TEXT, "table" TEXT, "type" TEXT, PRIMARY KEY(table))'.format(table_name=survey_table_name)
            self.execute(query)
        table_type = 'flat'
        self.conn.execute('INSERT OR IGNORE ("table", "survey", "type") INTO {} VALUES (?, ?, ?)'.format(survey_table_name), (survey_key, table_name, table_type))

    def create_table_index(self):
        self.conn.execute("ALTER TABLE {table} ADD PRIMARY KEY(id)".format(table=self.table_name))
        #self.conn.execute("CREATE UNIQUE INDEX {table}_id_idx ON {table} (id)".format(table=self.table_name))
        self.conn.execute("CREATE INDEX {table}_timestamp_idx ON {table} (timestamp)".format(table=self.table_name))
        self.conn.execute("CREATE INDEX {table}_globalid_idx ON {table} (global_id)".format(table=self.table_name))
    
    def append(self, df: pd.DataFrame):
        cnx = self.connect()
        if len(df) == 0:
            return
        cnx.register("temp_df", df)
        if self.first_batch:
            print("Registering new table {}".format(self.table_name))
            # Crée une table DuckDB avec le schéma du DataFrame
            cnx.execute("CREATE TABLE {} AS SELECT * FROM temp_df".format(self.table_name))
            self.create_table_index()
            self.first_batch = False
        else:
            columns = self.update_schema(df)
            # Append les données
            col_query = '"' + '","'.join(columns) + '"' 
            
            insert_or = ''
            if self.insert_mode == 'replace':
                insert_or = 'OR REPLACE'
            if self.insert_mode == 'ignore':
                insert_or = 'OR IGNORE'
            
            query = "INSERT {insert_or} INTO {table} ({columns}) SELECT * FROM temp_df".format(table=self.table_name, columns=col_query, insert_or=insert_or)
            
            if self.debug('query'):
                print(">>> # QUERY")
                print(query)
                print("---------- # QUERY")
            try:
                cnx.execute(query)
            except Exception as e:
                print("Error during inserting query", e)
                print(query)
                print("Dataframe")
                show_df(df)
                raise e
        self.update_index("temp_df")
        cnx.unregister("temp_df")
        
    def close(self):
        if self.conn is not None:
            self.conn.close()

class Counter:

    def __init__(self):
        self.counters = {}
    
    def add(self, name:str, count:int):
        prev = self.counters.get(name, 0)
        self.counters[name] = prev + count

    def percent(self, name, total:int):
        count = self.counters.get(name)
        if count is None:
            return None
        return 100 * count / total


class SourceDbQueryBuilder:
    """
        Build Query from the raw data database with profile criteria
    """
    def __init__(self, table_name:str, use_jsonb: bool, show_query: bool):
        self.table_name = table_name
        self.from_time: Optional[int] = None
        self.to_time: Optional[int] = None
        self.versions = None
        self.use_jsonb = use_jsonb
        self.show_query = show_query
        
    def resolve_versions(self, db: ExportDatabase, selector: VersionSelectorRule):
        w = []
        data: Optional[dict[str, str|int]] = {}
        if self.from_time is not None:
            w.append('submitted >= :from_time')
            data['from_time'] = self.from_time
        if self.to_time is not None:
            w.append('submitted <= :to_time')
            data['to_time'] = self.to_time
        
        query = "select distinct version from {}".format(self.table_name)
        if len(w) > 0:
            query += " WHERE ".join(w)
        else:
            data = None
        cur = db.cursor()
        res = cur.execute(query, data)
        versions = []
        for row in res.fetchall():
            v = row[0]
            if selector.is_version(v):
                versions.append(v)
        cur.close()
        return versions
            
    def build_query(self, select):
        w = []
        if self.from_time is not None:
            w.append('submitted >= {}'.format(self.from_time))
        if self.to_time is not None:
            w.append('submitted <= {}'.format(self.to_time))
        
        query = "SELECT {select} FROM {table_name} ".format(select=select, table_name=self.table_name)
        if len(w) > 0:
            query += " WHERE ".join(w)
        return query

    def query_data(self, batch_size:int, offset:int):
        """
            Return the query to fetch the data in raw tables
            Must return columns : data, version, id in this order
        """
        query = self.build_query('json(data) as data, version, id')
        query += "order by version, submitted LIMIT {batch_size} OFFSET {offset}".format(batch_size=batch_size, offset=offset)
        if self.show_query:
            print("  # QUERY Source query")
            print(query)
            print("---- QUERY")
        return query
    
    def query_count(self):
        return self.build_query('count(*)')

class SourceDbDataLoader(SourceDataLoader):
    """
        Load raw data from the Raw data database
    """

    def __init__(self, profile: ImporterProfile, meta:ExportMeta):
        
        query = SourceDbQueryBuilder(profile.source_table, meta.use_jsonb, profile.debugger.has('query_source'))
        
        if profile.versions is not None:
           query.resolve_versions(profile.source_db, profile.versions)

        if profile.from_time is not None:
            query.from_time = profile.from_time

        if profile.to_time is not None:
            query.to_time = profile.to_time   

        self.query = query
        self.source_db = profile.source_db
        self.debug_json = profile.debugger.has('json')
        
    def total_rows(self):
        count = self.profile.source_db.fetch_one(self.query.query_count())
        return count[0]

    def load(self, batch_size: int, offset:int):
        records = OrderedDict()

        cur = self.profile.source_db.cursor()
        res = cur.execute(self.query.query_data(batch_size=batch_size, offset=offset))

        count_fetched = 0
        for row in res:
            version = row[1]
            try:
                data = json.loads(row[0])
                if self.debug_json:
                    print("JSON at row {} (offset {})".format(count_fetched, offset + count_fetched))
                    print(data)
                    print("--- JSON")
                if version not in records:
                    records[version] = []
                records[version].append(data)
            except json.JSONDecodeError as e:
                print("Error parsing data for row {} : {}".format(row[2], e))
            count_fetched += 1
        cur.close()
        return (count_fetched, records)

class Importer:
    """
        Importer process the transformation from the raw data in a source database (usually SQLite) to another format, like Duckdb database
        through a Writer class
        Raw data are loaded as json an transformed into pandas DataFrame before to be transformed by processors and then importer using a Writer
    """
    def __init__(self, profile: ImporterProfile):
        self.profile = profile

    def debug(self, name:str):
        return self.profile.debugger.has(name)

    def run(self, loader: Optional[SourceDataLoader]=None, writer: Optional[Writer]=None):
        
        if writer is None:
            if self.profile.dry_run:
                writer = Writer()
            else:
                writer = DuckDbWriter(self.profile.target_db, self.profile.target_table, debugger=self.profile.debugger)

        meta = self.profile.source_db.get_meta()

        if loader is None:
            loader = SourceDbDataLoader(self.profile, meta)

        self.import_table(loader, writer)

    def import_table(self, loader: SourceDataLoader, writer: Writer):
        batch_size = self.profile.batch_size
        offset = self.profile.starting_offset
        
        total_rows = loader.total_rows()

        print("Fetching data of {} rows by {}".format(total_rows, batch_size))

        counts = Counter()

        debug_version = self.debug('version')
        debug_processors = self.debug('processors')
        
        writer.register_survey(self.profile.survey, self.profile.target_table)

        while True:
            
            count_fetched, records = loader.load(batch_size, offset)
            
            counts.add('fetched', count_fetched)

            if len(records) == 0:
                print("No record fetched, stopping")
                break
            
            print("> #BATCH - Offset {} {:.2f}%, found  {} versions, {} rows processing...".format(offset, counts.percent('fetched', total_rows), len(records), count_fetched))

            for version, rows in records.items():

                print(" >> #VERSION {}, {} rows from offset {}".format(version, len(rows), offset))

                counts.add(version, len(rows))

                df_struct = pd.DataFrame(rows)

                if debug_version:
                    print(show_df(df_struct))
                    print("----------------- #VERSION")
                    
                processors = self.profile.select_processors(version)

                for processor in processors:
                    if debug_processors:
                        print(">>> #PROCESSOR ", end=" ")
                        print(processor)
                    df_struct = processor.apply(df_struct)
                    if debug_processors:
                        print("   Dataframe after processor")
                        print(show_df(df_struct))
                        print("----------------------#PROCESSOR")
                if debug_version:
                    print("Appending {} rows for version '{}'".format(len(df_struct.index), version))
                writer.append(df_struct)
                
            offset += batch_size
        writer.close() 
        print(json.dumps(counts.counters, indent=2))