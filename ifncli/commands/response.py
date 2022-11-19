
import os
import re
from datetime import datetime, timedelta
from cliff.command import Command
from . import register
import json
from ..utils import read_yaml
from typing import Dict,List,Optional

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
                raise Exception("Invalid value '%s' in %s" % (v, name))
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

        query_start_time = datetime.strptime(query_start_date, "%Y-%m-%d-%H-%M-%S").timestamp() if query_start_date is not None else None
        query_end_time = datetime.strptime(query_end_date, "%Y-%m-%d-%H-%M-%S").timestamp() if query_end_date is not None else None
        
        survey_key = profile.survey_key

        client = self.app.get_management_api()
            
        resp = client.get_response_csv(
            study_key, survey_key,
            profile.key_separator,
            profile.response_format,
            profile.short_keys,
            profile.meta_infos,
            query_start_time, query_end_time
        )

        if resp is None:
            print("No files were generated.")
            exit()

        if not profile.rename_columns is None:
            resp = replace_columns(profile.rename_columns, resp)        

        output_folder = args.output
        
        os.makedirs(output_folder)

        query_range_text = ""
        if query_start_date is not None:
            query_range_text += "_" + query_start_date
        if query_end_date is not None:
            query_range_text += "_" + query_end_date

        response_file_name =  "{}_responses{}.{}".format(survey_key, query_range_text, profile.response_extension)
        
        export_data(os.path.join(output_folder, response_file_name), resp)
        
        if profile.survey_info is None:
            return

        survey_info = profile.survey_info

        survey_info_text = ""
        if survey_info['format'] == "csv":
            survey_info_text = client.get_survey_info_preview_csv(study_key, survey_key, survey_info['lang'], profile.short_keys)
        else:
            survey_infos = client.get_survey_info_preview(study_key, survey_key, survey_info['lang'], profile.short_keys)
            if survey_infos is not None:
                survey_info_text = json.dumps(survey_infos, indent=2)

        info_file_name =  "{}_survey_info.{}".format(survey_key, survey_info['format'])
        export_data(os.path.join(output_folder, info_file_name), survey_info_text) 
        print("File generated at: {}".format(info_file_name))

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

register(ResponseSchemaDownloader)
register(ResponseDownloader)
