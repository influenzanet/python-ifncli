

import sqlite3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
import duckdb
from typing import Optional
from collections import OrderedDict
from .processor import BasePreprocessor
from .profile import ImporterProfile
from .version_selector import VersionSelector
from ..database import ExportDatabase

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

class Writer:

    def __init__(self):
        pass

    def close(self):
        pass

    def append(self, df: pd.DataFrame):
        pass    

class ParquerWriter(Writer):

    def __init__(self, parquet_file):
        super().__init__()
        self.parquet_writer = None
        self.parquet_file = parquet_file
        self.row_version = None

    def append(self, df: pd.DataFrame):
        # Convertir en Arrow Table
        table = pa.Table.from_pandas(df)

        # Initialiser le ParquetWriter une seule fois
        if self.parquet_writer is None:
            self.parquet_writer = pq.ParquetWriter(self.parquet_file, table.schema)

        self.parquet_writer.write_table(table)

    def close(self):
        if self.parquet_writer is not None:
            self.parquet_writer.close()

class DuckDbWriter(Writer):
    
    def __init__(self, duckdb_file: str, table_name: str, insert_mode:str="ignore"):
        super().__init__()
        self.conn = None
        self.duckdb_file = duckdb_file
        self.table_name = table_name
        self.first_batch = True
        self.insert_mode = insert_mode
        self.user_table = 'survey_surveyuser'
        
    def connect(self):
        self.conn = duckdb.connect(self.duckdb_file)  # ou ":memory:" pour en mémoire
        if self.has_table(self.table_name):
            self.first_batch = False
        if not self.has_table(self.user_table):
            self.execute("CREATE SEQUENCE survey_user_id_seq START 1")
            self.execute("CREATE TABLE {user_table} (id INTEGER DEFAULT nextval('survey_user_id_seq'), global_id TEXT)".format(user_table=self.user_table))
            self.execute("CREATE UNIQUE INDEX survey_user_global_id ON {user_table} (global_id)".format(user_table=self.user_table))     

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

    def create_table_index(self):
        self.conn.execute("ALTER TABLE {table} ADD PRIMARY KEY(id)".format(table=self.table_name))
        #self.conn.execute("CREATE UNIQUE INDEX {table}_id_idx ON {table} (id)".format(table=self.table_name))
        self.conn.execute("CREATE INDEX {table}_timestamp_idx ON {table} (timestamp)".format(table=self.table_name))
        self.conn.execute("CREATE INDEX {table}_globalid_idx ON {table} (global_id)".format(table=self.table_name))

    def append(self, df: pd.DataFrame):
        if self.conn is None:
            self.connect()
        if len(df) == 0:
            return
        self.conn.register("temp_df", df)
        if self.first_batch:
            print("Registering new table {}".format(self.table_name))
            # Crée une table DuckDB avec le schéma du DataFrame
            self.conn.execute("CREATE TABLE {} AS SELECT * FROM temp_df".format(self.table_name))
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
            self.conn.execute(query)
        self.update_index("temp_df")
        self.conn.unregister("temp_df")
        
    def close(self):
        if self.conn is not None:
            self.conn.close()

class SourceQuery:
    """
        Query raw data
    """
    def __init__(self, table_name:str):
        self.table_name = table_name
        self.from_time = None
        self.to_time = None
        self.versions = None
        
    def resolve_versions(self, db: ExportDatabase, selector: VersionSelector):
        w = []
        data = {}
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
        return query
    
    def query_count(self):
        return self.build_query('count(*)')

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


class Importer:

    def __init__(self, profile: ImporterProfile, debug=False):
        self.debug = debug
        self.profile = profile

    def run(self):
        
        writer = DuckDbWriter(self.profile.target_db, self.profile.target_table)

        query = SourceQuery(self.profile.source_table)
        
        if self.profile.versions is not None:
           query.resolve_versions(self.profile.source_db, self.profile.versions)

        if self.profile.from_time is not None:
            query.from_time = self.profile.from_time

        if self.profile.to_time is not None:
            query.to_time = self.profile.to_time        

        self.import_table(query, writer)

    def import_table(self, query: SourceQuery, writer: Writer):
        batch_size = self.profile.batch_size
        offset = 0
        
        count = self.profile.source_db.fetch_one(query.query_count())
        total_rows = count[0]

        print("Fetching data of {} rows by {}".format(total_rows, batch_size))

        counts = Counter()

        while True:
            records = OrderedDict()

            cur = self.profile.source_db.cursor()
            res = cur.execute(query.query_data(batch_size=batch_size, offset=offset))
            
            count_fetched = 0
            for row in res:
                version = row[1]
                try:
                    data = json.loads(row[0])
                    if version not in records:
                        records[version] = []
                    records[version].append(data)
                except json.JSONDecodeError as e:
                    print("Error parsing data for row {} : {}".format(row[2], e))
                count_fetched += 1
            cur.close()
            
            counts.add('fetched', count_fetched)

            if len(records) == 0:
                print("No record fetched, stopping")
                break
            
            print("Offset {} {:.2f}%, found  {} versions, {} rows processing...".format(offset, counts.percent('fetched', total_rows), len(records), count_fetched))

            for version, rows in records.items():

                counts.add(version, len(rows))

                if self.debug:
                    print(version)

                processors = self.profile.select_processors(version)

                df_struct = pd.DataFrame(rows)

                for processor in processors:
                    if self.debug:
                        print(processor)
                    df_struct = processor.apply(df_struct)
                    if self.debug:
                        print(df_struct.info())
                if self.debug:
                    print("Appending {} rows for version '{}'".format(len(df_struct.index), version))
                writer.append(df_struct)
                
            offset += batch_size
        writer.close() 
        print(json.dumps(counts.counters, indent=2))