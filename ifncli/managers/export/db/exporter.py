import os
import json
from datetime import datetime, timedelta
from typing import Dict,List,Optional
from ....utils import ISO_TIME_FORMAT, from_iso_time, to_iso_time
from ....utils.sqlite import SqliteDb
from .. import ExportProfile
from .database import ExportDatabase
import os

from influenzanet.api import SurveyResponseJSONPaginated

def midnight(d:datetime):
    return d.replace(hour=0, minute=0, second=0)

class ExportCatalogDb:
    """
        Export Catalog manage list of downloaded response file batches and their period (min,max time)
    """

    def __init__(self, db, start_time:datetime, max_time:datetime, period: int):
        self.current_end = start_time
        self.min_time = self.midnight(start_time)
        self.max_time = max_time
        self.period = period
               
    def append(self, start_time, end_time):
        self.current_end = end_time
        self.current_start = start_time

    def get_last_time(self):
        return self.current_end

    def get_start_time(self, now: datetime):
        if len(self.catalog) == 0:
            return self.midnight(self.min_time)
        times = sorted(self.catalog.keys())
        for time in times:
            entry = self.catalog[time]
            last_start = entry['start']
            if entry['end'] < now:
                continue
            if now >= entry['start'] and  now <= entry['end']:
                # Current entry has the now time, then the previous end is to be used
                return self.midnight(entry['start'])
            
        return self.midnight(last_start)

class ExportSqlite(ExportDatabase):
    
    def setup(self, empty_db:bool):
        import_table = self.import_log_table()
        if not self.table_exists(import_table):
            self.execute("CREATE TABLE {}(time INT, survey_key TEXT, start INT, end INT)".format(import_table))
        meta = self.export_meta_table()
        if not self.table_exists(meta):
            self.execute("CREATE TABLE {}(id INTEGER PRIMARY KEY CHECK (id = 0), key_separator TEXT, use_jsonb INT)".format(meta))

    def supports_jsonb(self):
        r = self.fetch_one("select exists(select 1 from pragma_function_list where name='jsonb')")
        return int(r[0])

    def setup_meta(self, key_separator):
        meta_table = self.export_meta_table()
        meta = self.fetch_one('select key_separator from {}'.format(meta_table))
        if meta is not None:
            if meta[0] != key_separator:
                raise ValueError("Cannot defined key_separator '{}' as its already defined to '{}'".format(key_separator, meta[0]))
        else:
            use_jsonb = self.supports_jsonb()
            self.execute("INSERT INTO {}(id, key_separator, use_jsonb) VALUES (0, ?, ?)".format(meta_table), (key_separator, use_jsonb))
        return self.get_meta()    
    
    def setup_surveyinfo(self):
        table_name = "survey_info"
        if not self.table_exists(table_name):
            query = "CREATE TABLE {table_name} (survey TEXT, version TEXT, data TEXT, PRIMARY KEY(survey,version))".format(table_name=table_name)
            self.execute(query)

    def register_survey_table(self, survey, table, table_type):
        table_name = "survey_response_table"
        if not self.table_exists(table_name):
            query = 'CREATE TABLE {table_name} ("survey" TEXT, "table" TEXT, "type" TEXT, PRIMARY KEY(table))'.format(table_name=table_name)
            self.execute(query)
        self.execute('INSERT OR IGNORE ("table", "survey", "type") VALUES (?, ?, ?)', (survey, table, table_type))

class DbExporter:

    def __init__(self, profile:ExportProfile, client, study_key, db_path: str, page_size:int):
        self.profile = profile
        self.client = client
        self.study_key = study_key
        self.db = ExportSqlite(db_path, allow_create=True)
        self.page_size = page_size
        
    def register_import(self, survey_key:str, start_time: Optional[datetime], end_time: Optional[datetime]):
        query = 'INSERT INTO import_log("time", "survey_key", "start", "end") VALUES (unixepoch(),?,?,?)'
        data = (
                survey_key, 
                int(start_time.timestamp()) if start_time is not None else 0, 
                int(end_time.timestamp()) if end_time is not None else 0, 
                )
        self.db.execute(query, data)

    def survey_response_table(self, survey_key:str):
        return self.db.response_table(survey_key)

    def time_range(self, survey_key:str):
        table_name = self.survey_response_table(survey_key)
        if not self.db.table_exists(table_name):
            return (None, None)
        query = "SELECT min(submitted), max(submitted) from {table_name}".format(table_name=table_name)
        r = self.db.fetch_one(query)
        if r is None or r[0] is None:
            return (None, None)
        start = datetime.fromtimestamp(r[0])
        end = datetime.fromtimestamp(r[1])
        return (start, end)

    def export(self, start_time: Optional[datetime], end_time: Optional[datetime]):
        
        profile = self.profile
        
        survey_key = profile.survey_key
        
        table_name = self.survey_response_table(survey_key)
        
        if not self.db.table_exists(table_name):
            query = "CREATE TABLE {table_name} (id TEXT, submitted INT, version TEXT, data BLOB, PRIMARY KEY(id))".format(table_name=table_name)
            self.db.execute(query)
            query = "CREATE INDEX {table_name}_submitted ON {table_name}(submitted)".format(table_name=table_name)
            self.db.execute(query)
            self.db.register_survey_table(survey_key, table_name, 'raw')

        if not profile.short_keys:
            print("Disabling Short keys is ignored")

        args = {
            'short_keys': True,
            'key_separator': profile.key_separator
        }

        meta = self.db.setup_meta(profile.key_separator)

        if start_time is not None:
            args['start'] = int(start_time.timestamp())
        if end_time is not None:
            args['end'] = int(end_time.timestamp())

        pager = SurveyResponseJSONPaginated(self.client, page_size=self.page_size, study_key=self.study_key, survey_key=survey_key, **args)

        if meta.use_jsonb:
            json_expr = 'jsonb(?)'
        else:
            json_expr = '?'

        insert_query = "INSERT OR IGNORE INTO {table_name} (id, submitted, version, data) VALUES (?, ?, ?, {json_expr}) ".format(table_name=table_name, json_expr=json_expr)

        inserted_count = 0
        for r in pager:
            print("Fetched page %d width %d items" % (r.page, len(r)))
            if(len(r) == 0):
                break
            data = []
            for item in r:
                submitted = item['submitted']

                if isinstance(item, dict):
                    # Recode TRUE/FALSE to boolean values to reduce space & avoid later trans
                    for k, v in item.items():
                        if v == 'TRUE':
                            item[k] = True
                        if v == 'FALSE':
                            item[k] = False

                d = (item['ID'], submitted, item['version'], json.dumps(item))

                data.append(d)
                inserted_count += 1
            if len(data) > 0:
                print("Insert %d" % (len(data)))
                self.db.execute_many(insert_query, data)

        if inserted_count > 0:
            self.register_import(survey_key, start_time, end_time)

        #if not profile.rename_columns is None:
        #    resp = replace_columns(profile.rename_columns, resp)        

    def get_start_time(self, now:datetime):
       """
        Get export start time
        Always restart from the start of the last days already fetch to be sure the day is complete
       """
       _, max_time = self.time_range(self.profile.survey_key)
       if max_time is None:
           return midnight(self.profile.start_time)
       return midnight(max_time)

    def export_all(self, force_start:Optional[datetime]):
        """"
            Incrementally export data 
        """
        period_size = 7 # Number of days to load (> 1)
        max_time = self.profile.max_time  
        now = datetime.now()
        if force_start is not None:
            start_time = force_start
        else:
            start_time = self.get_start_time(now)
        # Max download time, if not provided only load one years (prevent infinite loop)
        exported = 0
        print("Loading %s data from %s to %s by %d days" % (self.profile.survey_key, start_time, max_time, period_size ))
        while start_time < max_time:
            if start_time > now:
                # Cannot load data in the future
                break
            end_time = start_time + timedelta(days=period_size - 1)
            end_time = end_time.replace(hour=23, minute=59)
            print("> %s - %s" % (start_time, end_time))
            r = self.export(start_time, end_time)
            if r is not None:
                exported += 1
            start_time = start_time + timedelta(days=period_size)
        print("%d periods exported" % (exported))
        self.export_info()
            
    def export_info(self, replace=True):
        if self.profile.survey_info is None:
            return
        
        self.db.setup_surveyinfo()
        
        survey_info = self.profile.survey_info
        survey_key = self.profile.survey_key
        short_keys = True
        survey_infos = self.client.get_survey_info_preview(self.study_key, survey_key, survey_info['lang'], short_keys)
        
        if "versions" not in survey_infos:
            print("Unable to get survey info, 'versions' is missing in response")
            return
        
        if replace:
            action = "REPLACE"
        else:
            action = "IGNORE"

        for info in survey_infos['versions']:
            versionID = info['versionId']
            query = "INSERT OR {action} INTO {table_name} (survey,version,data) VALUES (?,?,?)".format(table_name=table_name, action=action)
            self.db.execute(query, (survey_key, versionID, json.dumps(info)))
