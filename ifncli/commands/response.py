import os
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from cliff.command import Command
from . import register
from ..utils import read_yaml,  read_json, from_iso_time, to_iso_time
from ..managers.export import Exporter, ExportProfile, export_data

class ResponseDownloader(Command):
    """
        Download responses from a survey
    """

    name = "response:download"

    def get_parser(self, prog_name):
        parser = super(ResponseDownloader, self).get_parser(prog_name)
        parser.add_argument("--query-start", default=None)
        parser.add_argument("--query-end", default=None)
        parser.add_argument("--profile", required=True, help="Export profile yaml file", default=None)
        parser.add_argument("--study-key", type=str, required=True, help="Study key")
        parser.add_argument("--output", type=str, default="", help="Output folder")
        return parser
        
    def take_action(self, args):
        study_key = args.study_key
        query_start_date = args.query_start
        query_end_date = args.query_end
        profile = ExportProfile(args.profile)

        output_folder = "export_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S") if args.output == "" else args.output
        
        query_start_time = datetime.strptime(query_start_date, "%Y-%m-%d-%H-%M-%S") if query_start_date is not None else None
        query_end_time = datetime.strptime(query_end_date, "%Y-%m-%d-%H-%M-%S") if query_end_date is not None else None
        
        client = self.app.get_management_api()
            
        exporter = Exporter(profile, client, study_key)
        r = exporter.export(query_start_time, query_end_time, output_folder)
        exporter.export_info(output_folder, prefix_name=True)

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
        parser.add_argument("--output", type=str, default="", help="Output folder")
        return parser
     
    def take_action(self, args):
        study_key = args.study_key
        survey_key = args.survey_key
        language = args.lang
        short_keys = args.short
        output_format = args.format 
        output_folder = args.output
        survey_info_text = ""

        client = self.app.get_management_api()
        
        
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
        Export survey data using an weekly incremental
    """

    name = "response:export-bulk"

    def get_parser(self, prog_name):
        parser = super(ResponseExporter, self).get_parser(prog_name)
        parser.add_argument("--profile", type=str, required=True, help="Profile yaml with export parameters for this survey")
        parser.add_argument("--study", type=str, required=True, help="Study key")
        parser.add_argument("--output", type=str, default="", help="Output folder where to place the export (will create a subfolder)")
        return parser
        
    def take_action(self, args):
        study_key = args.study
        profile = ExportProfile(args.profile)

        output_folder = args.output
        
        client = self.app.get_management_api()
            
        exporter = Exporter(profile, client, study_key)

        r = exporter.export_all(output_folder)

class ResponseBulkExporter(Command):
    """
        Incremental Export for a set of surveys (each with an export profile)
    """

    name = "response:export-plan"

    def get_parser(self, prog_name):
        parser = super(ResponseBulkExporter, self).get_parser(prog_name)
        parser.add_argument("--plan", type=str, required=True, help="yaml files with export plan")
        parser.add_argument("--output", type=str, default="", help="Output folder")
        return parser
        
    def take_action(self, args):
        output_folder = args.output
        
        plan = read_yaml(args.plan)

        study_key = plan['study']

        plan_folder = os.path.dirname(os.path.abspath(args.plan))
        
        client = self.app.get_management_api()
        
        for profile_name in plan['profiles']:
            fp = plan_folder + '/' + profile_name
            print("* Processing %s" % (fp))
            profile = ExportProfile(fp)
            exporter = Exporter(profile, client, study_key)
            r = exporter.export_all(output_folder)

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
register(ResponseBulkExporter)
register(ResponseStats)
register(ResponseStatsDaily)