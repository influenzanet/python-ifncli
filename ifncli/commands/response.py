
import os
import re
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Dict,List,Optional
from cliff.command import Command
from . import register
from ..utils import read_yaml, write_content, read_json

def get_survey_parser_based_on_time(parsers, key: str, ts):
    parser = None

    filtered_parsers = [p for p in parsers if p['key'] == key]
    filtered_parsers_count = len(filtered_parsers)
    if filtered_parsers_count < 1:
        return None
    elif filtered_parsers_count == 1:
        return filtered_parsers[0]
    else:
        for p in filtered_parsers:
            start = int(p['published'])
            end = p['unpublished']
            # print(key, start, end, ts)
            if start > ts:
                continue
            if end is not None:
                end = int(p['unpublished'])
                if end < ts:
                    continue
            parser = p

    if parser is None:
        return filtered_parsers[0]
    return parser

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


ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def from_iso_time(time:str):
    return datetime.strptime(time, ISO_TIME_FORMAT)

def to_iso_time(d):
    return d.strftime(ISO_TIME_FORMAT)

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

        self.start_time = None
        self.max_time = None
        if 'start_time' in profile:
            self.start_time = datetime.strptime(profile['start_time'], ISO_TIME_FORMAT)
        
        if 'max_time' in profile:
            self.max_time = datetime.strptime(profile['max_time'], ISO_TIME_FORMAT)
        

class ExportCatalog:

    def __init__(self, path:str, start_time:datetime, max_time:datetime):
        self.file = path + '/catalog.json'
        self.current_end = start_time
        self.min_time = start_time
        self.max_time = max_time
        if os.path.exists(self.file):
            self.load()
        else:
            self.catalog = []
    
    def load(self):
        data = read_json(self.file)
        self.catalog = []
        previous_end = None
        for i, row in data.iteritems():
            start_time = from_iso_time(row['start'])
            end_time = from_iso_time(row['end'])
            self.check_range(start_time, self.min_time, self.max_time, "%d start_time" % (i,) )
            self.check_range(end_time, self.min_time, self.max_time, "%d end_time" % (i,)  )
            
            if previous_end is not None:
                self.check_range(start_time, previous_end, None, "%d start_time" % (i,))
            
            self.current_end = end_time
            previous_end = end_time
            self.append(start_time, end_time, row['file'])

    def check_range(self, time:datetime, min_t:datetime, max_t:Optional[datetime], name:str):
        if max_t is not None and time > max_t:
            raise Exception("%s (%s) after max (%s)" % (name, time, max_t))
        if time < min_t:
            raise Exception("%s (%s) befor max (%s)" % (name, time, min_t))
            

    def append(self, start_time, end_time, file):
        self.catalog.append({'start': start_time, 'end': end_time, 'file': file})
        self.current_end = end_time

    def save(self):
        def encoder(d):
            if isinstance(d, datetime):
                return d.strftime(ISO_TIME_FORMAT)
        write_content(self.file, json.dumps(self.catalog, default=encoder))

    def get_last_time(self):
        return self.current_end
            
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
        catalog = ExportCatalog(output, self.profile.start_time, self.profile.max_time)
        output_folder = output + '/' + self.profile.survey_key
        os.makedirs(output_folder, exist_ok=True)
        start_time = catalog.get_last_time()
        already_has_data = False
        # Max download time, if not provided only load one years (prevent infinite loop)
        max_time = self.profile.max_time if self.profile.max_time is not None else start_time + timedelta(days=365)
        loaded = 0
        while start_time < max_time:
            end_time = start_time + timedelta(days=6)
            end_time = end_time.replace(hour=23, minute=59)
            print("> %s - %s" % (start_time, end_time))
            r = self.export(start_time, end_time, output_folder)
            if r is None: 
                if already_has_data:
                    break
            else:
                already_has_data = True
                loaded += 1
                catalog.append(start_time, end_time, r)
                catalog.save()
            start_time = start_time + timedelta(days=7)
        print("%d file(s) loaded" % (loaded))
            


class ResponseDownloader(Command):
    """
        Download responses from a set of survey (not implemented yet)
    """

    name = "response:download"

    def get_parser(self, prog_name):
        parser = super(ResponseDownloader, self).get_parser(prog_name)
        parser.add_argument("--query-start", default=None)
        parser.add_argument("--query-end", default=None)
        parser.add_argument("--profile", help="Export profile yaml file", default=None)
        parser.add_argument("--study-key", type=str, required=True, help="Study key")
        parser.add_argument("--output", type=str, help="Output folder", default=None)
        return parser
        
    def take_action(self, args):
        study_key = args.study_key
        query_start_date = args.query_start
        query_end_date = args.query_end
        profile = ExportProfile(args.profile)

        output_folder = "export_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        
        query_start_time = datetime.strptime(query_start_date, "%Y-%m-%d-%H-%M-%S") if query_start_date is not None else None
        query_end_time = datetime.strptime(query_end_date, "%Y-%m-%d-%H-%M-%S") if query_end_date is not None else None
        
        client = self.app.get_management_api()
            
        exporter = Exporter(profile, client, study_key)

        r = exporter.export(query_start_time, query_end_time, output_folder )

        if r is None:
            print("No files were generated.")
            exit()
        
        if profile.survey_info is None:
            return

        survey_info = profile.survey_info

        survey_info_text = ""
        if survey_info['format'] == "csv":
            survey_info_text = client.get_survey_info_preview_csv(study_key, profile.survey_key, survey_info['lang'], profile.short_keys)
        else:
            survey_infos = client.get_survey_info_preview(study_key, profile.survey_key, survey_info['lang'], profile.short_keys)
            if survey_infos is not None:
                survey_info_text = json.dumps(survey_infos, indent=2)

        info_file_name =  "{}_survey_info.{}".format(survey_key, survey_info['format'])
        export_data(os.path.join(output_folder, info_file_name), survey_info_text) 

class ResponseSchemaDownloader(Command):
    """
        Download responses schema from survey definition
    """

    name = "response:schema"

    def get_parser(self, prog_name):
        parser = super(ResponseSchemaDownloader, self).get_parser(prog_name)
        parser.add_argument("--survey", help="Survey key", default=None)
        parser.add_argument("--study-key", type=str, required=True, help="Study key")
        parser.add_argument("--short", help="Short keys")
        parser.add_argument("--lang", type=str, required=True, help="Study key")
        parser.add_argument("--format", type=str, required=True, help="Study key")
        parser.add_argument("--output", type=str, help="Output folder", default=None)
        return parser
     
    def take_action(self, args):
        study_key = args.study_key
        survey_key = args.survey_key
        language = args.lang
        short_keys = args.short
        output_format = args.format 
        output = args.output
        survey_info_text = ""
        
        if output_format == "csv":
            survey_info_text = client.get_survey_info_preview_csv(study_key, survey_key, language, short_keys)
        else:
            survey_infos = client.get_survey_info_preview(study_key, survey_key, language, short_keys)
            if survey_infos is not None:
                survey_info_text = json.dumps(survey_infos, indent=2)

        info_file_name =  "{}_{}_survey_info.{}".format(survey_key, output_format)
        export_data(os.path.join(output_folder, info_file_name), survey_info_text) 
        print("File generated at: {}".format(info_file_name))

class ResponseExporter(Command):
    """
        Export incremental
    """

    name = "response:export"

    def get_parser(self, prog_name):
        parser = super(ResponseExporter, self).get_parser(prog_name)
        parser.add_argument("--profile", help="Export profile yaml file")
        parser.add_argument("--study", type=str, required=True, help="Study key")
        parser.add_argument("--output", type=str, help="Output folder")
        return parser
        
    def take_action(self, args):
        study_key = args.study
        profile = ExportProfile(args.profile)

        output_folder = args.output
        
        client = self.app.get_management_api()
            
        exporter = Exporter(profile, client, study_key)

        r = exporter.export_all(output_folder )

class ResponseStats(Command):
    """
        Export incremental
    """

    name = "response:stats"

    def get_parser(self, prog_name):
        parser = super(ResponseStats, self).get_parser(prog_name)
        parser.add_argument("--study", type=str, required=True, help="Study key")
        return parser
        
    def take_action(self, args):
        study_key = args.study
        client = self.app.get_management_api()

        print(client.get_response_statistics(study_key))

class ResponseStatsDaily(Command):
    """
        Export incremental daily statistics
    """

    name = "response:daily"

    def get_parser(self, prog_name):
        parser = super(ResponseStatsDaily, self).get_parser(prog_name)
        parser.add_argument("--file", type=str, required=True, help="data file")
        return parser
        
    def take_action(self, args):
        file = args.file

        data = read_json(file)

        study_key = data['study']
        max_time = from_iso_time(data['max_time'])

        now = datetime.now()

        if max_time > now:
            max_time = now

        if 'start_time' in data:
            start_time = from_iso_time(data['start_time'])
        else:
            start_time = now

        if 'dates' in data:
            dates = data['dates']
        else:
            dates = OrderedDict()
            data['dates'] = dates

        client = self.app.get_management_api()

        start_time = start_time.replace(hour=0, minute=0, second=0)
        while start_time < max_time:
            date = start_time.strftime("%Y-%m-%d")
            end_time = start_time.replace(hour=23, minute=59, second=59)
            print("> %s - %s" % (start_time, end_time), flush=False)
            try:
                r = client.get_response_statistics(study_key, start=start_time.timestamp(), end=end_time.timestamp())
                stats = r['surveyResponseCounts']
                dates[date] = stats
                print(stats)
            except Exception as e:
                print(e)
            last_done = start_time
            start_time = start_time + timedelta(days=1)

        data['start_time'] = last_done

        def encoder(r):
            if isinstance(r, datetime):
                return to_iso_time(r)
            return r

        with open(file, "w") as f:
            d = json.dumps(data, default=encoder)
            f.write(d)
            f.close()


register(ResponseExporter)
register(ResponseSchemaDownloader)
register(ResponseDownloader)
register(ResponseStats)
register(ResponseStatsDaily)