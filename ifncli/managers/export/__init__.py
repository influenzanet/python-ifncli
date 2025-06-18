
import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict,List,Optional
from ...utils import read_yaml, write_content, read_json, ISO_TIME_FORMAT, from_iso_time, to_iso_time

def replace_columns(response_modifier, resp):
    resp = resp.split('\n')
    cols = resp[0]

    for col in response_modifier:
        cols = re.sub(col, response_modifier[col], cols)

    return '\n'.join([cols] + resp[1:])

def export_data(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
            f.write(data)
    print("File generated at: {}".format(file_name))

class ExportProfile:

    def get_bool(self, data, name, default):
        if name in data:
            v = data[name]
            if not isinstance(v, bool):
                raise Exception("Field %s must be boolean" % (name, ))
        else:
            v = default
        return v


    def get_string(self, data, name, default, values:Optional[List]):
        if name in data:
            v = data[name]
            if not isinstance(v, str):
                raise Exception("Field %s must be string" % (name, ))
            if values is not None and v not in values:
                raise Exception("Invalid value '%s' in %s, expect: %s" % (v, name, ', '.join(values) ))
        else:
            v = default
        return v

    def get_meta_infos(self, meta: Dict): 
        params = {
                "withPositions": 'position',
                "withInitTimes": 'init_times',
                "withDisplayTimes": 'display_tile', 
                "withResponseTimes": 'response_time',
            }
        o = {}
        for name, yaml_key in params.items():
            value ='false'
            if yaml_key in 'meta':
                if meta[yaml_key]:
                    value = 'true'
            o[name] = value
        return o

    def __init__(self, yaml_file):
        
        profile = read_yaml(yaml_file)
        
        self.survey_key = profile['survey_key']

        if 'survey_info' in profile:
            survey_info = profile['survey_info']
            self.survey_info = {
                'lang': survey_info['lang'],
                'format': self.get_string(survey_info, 'format', 'csv', ['csv', 'json'])
            }
        else:
            self.survey_info = None

        self.response_format = self.get_string(profile, 'format', 'wide', values=["long", "wide", "json"])

        self.response_extension = 'json' if self.response_format == 'json' else 'csv'

        self.short_keys = self.get_bool(profile, 'short_keys', False)
   
        self.key_separator = profile['key_separator']
        
        self.meta_infos = self.get_meta_infos(profile.get('meta', {}))

        self.rename_columns = profile.get('rename_columns', None)

        if not 'start_time' in profile:
            raise Exception("start_time must be provided")
            
        self.start_time = datetime.strptime(profile['start_time'], ISO_TIME_FORMAT)
        
        if 'max_time' in profile:
            max = profile['max_time']
            if max == 'now':
                self.max_time = datetime.now()
            else:
                self.max_time = datetime.strptime(max, ISO_TIME_FORMAT)
        else:
            self.max_time = self.start_time + timedelta(days=365) 

    def __str__(self) -> str:
        return str(self.__dict__)

class ExportCatalog:
    """
        Export Catalog manage list of downloaded response file batches and their period (min,max time)
    """

    def __init__(self, path:str, start_time:datetime, max_time:datetime, period: int):
        self.file = path + '/catalog.json'
        self.current_end = start_time
        self.min_time = self.midnight(start_time)
        self.max_time = max_time
        self.period = period
        self.catalog: Dict[datetime, Dict] = {}
        if os.path.exists(self.file):
            self.load()
        
    def midnight(self, d: datetime):
        return d.replace(hour=0, minute=0, second=0)
    
    def load(self):
        data = read_json(self.file)
        previous_end = None
        
        if not 'period' in data:
            raise Exception("Missing period entry in catalog")
        
        catalog_period = data['period']
        if catalog_period != self.period:
            raise Exception("This catalog has been created for another period %d cannot reuse it" % (catalog_period))
        
        files = data['files']
        for i, row in enumerate(files):
            start_time = from_iso_time(row['start'])
            end_time = from_iso_time(row['end'])
            updated = None
            if 'updated' in row:
                updated = row['updated']
            self.check_range(start_time, self.min_time, self.max_time, "%d start_time" % (i,) )
            self.check_range(end_time, self.min_time, self.max_time, "%d end_time" % (i,)  )
            
            if previous_end is not None:
                self.check_range(start_time, previous_end, None, "%d start_time" % (i,))
            
            previous_end = end_time

            self.append(start_time, end_time, row['file'], updated=updated)

    def check_range(self, time:datetime, min_t:datetime, max_t:Optional[datetime], name:str):
        if max_t is not None and time > max_t:
            raise Exception("%s (%s) after max (%s)" % (name, time, max_t))
        if time < min_t:
            raise Exception("%s (%s) before max (%s)" % (name, time, min_t))
            
    def append(self, start_time, end_time, file, updated:datetime=None):
        entry = {'start': start_time, 'end': end_time, 'file': file}
        if updated is not None:
            entry['updated'] = updated
        self.catalog[start_time] = entry
        self.current_end = end_time
        self.current_start = start_time

    def has_files(self):
        return len(self.catalog) > 0

    def save(self):
        def encoder(d):
            if isinstance(d, datetime):
                return to_iso_time(d)
        files = []
        for time in sorted(self.catalog.keys()):
            files.append(self.catalog[time])
        d = {
            'period': self.period,
            'files': files
        }
        write_content(self.file, json.dumps(d, default=encoder, indent=2))

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
            
class Exporter:

    def __init__(self, profile:ExportProfile, client, study_key):
        self.profile = profile
        self.client = client
        self.study_key = study_key

    def export(self, start_time: Optional[datetime], end_time: Optional[datetime], output_folder:str):
        
        profile = self.profile
        
        survey_key = profile.survey_key
    
        resp = self.client.get_response_csv(
            self.study_key, survey_key,
            profile.key_separator,
            profile.response_format,
            profile.short_keys,
            profile.meta_infos,
            start_time.timestamp() if start_time is not None else None, 
            end_time.timestamp() if end_time is not None else None
        )

        if resp is None:
            return None

        if not profile.rename_columns is None:
            resp = replace_columns(profile.rename_columns, resp)        

        os.makedirs(output_folder, exist_ok=True)

        query_range_text = ""
        if start_time is not None:
            query_range_text += "_" + start_time.strftime("%Y-%m-%d-%H-%M-%S")
        if end_time is not None:
            query_range_text += "_" + end_time.strftime("%Y-%m-%d-%H-%M-%S")

        response_file_name =  "{}_responses{}.{}".format(survey_key, query_range_text, profile.response_extension)
        
        export_data(os.path.join(output_folder, response_file_name), resp)
        return response_file_name

    def export_all(self, output:str):
        """"
            Incrementally export data 
        """
        output_folder = os.path.join(output, self.profile.survey_key)
        period_size = 7 # Number of days to load (> 1)
        max_time = self.profile.max_time  
        catalog = ExportCatalog(output_folder, self.profile.start_time, max_time, period_size)
        os.makedirs(output_folder, exist_ok=True)
        now = datetime.now()
        start_time = catalog.get_start_time(now)
        # Max download time, if not provided only load one years (prevent infinite loop)
        loaded = 0
        print("Loading %s data from %s to %s by %d days" % (self.profile.survey_key, start_time, max_time, period_size ))
        while start_time < max_time:
            if start_time > now:
                # Cannot load data in the future
                break
            end_time = start_time + timedelta(days=period_size - 1)
            end_time = end_time.replace(hour=23, minute=59)
            print("> %s - %s" % (start_time, end_time))
            r = self.export(start_time, end_time, output_folder)
            if r is not None:
                loaded += 1
                catalog.append(start_time, end_time, r, updated=now)
                catalog.save()
            start_time = start_time + timedelta(days=period_size)
        print("%d file(s) loaded" % (loaded))
        self.export_info(output_folder)
            
    def export_info(self, output_folder:str, prefix_name:bool=False):
        if self.profile.survey_info is None:
            return

        survey_info = self.profile.survey_info
        survey_key = self.profile.survey_key
        short_keys = self.profile.short_keys
        survey_info_text = ""
        if survey_info['format'] == "csv":
            survey_info_text = self.client.get_survey_info_preview_csv(self.study_key, survey_key, survey_info['lang'], short_keys)
        else:
            survey_infos = self.client.get_survey_info_preview(self.study_key, survey_key, survey_info['lang'], short_keys)
            if survey_infos is not None:
                survey_info_text = json.dumps(survey_infos, indent=2)

        info_file_name =  "survey_info.{}".format(survey_info['format'])
        if prefix_name:
            info_file_name = "{}_{}".format(survey_key, info_file_name)
        export_data(os.path.join(output_folder, info_file_name), survey_info_text) 

