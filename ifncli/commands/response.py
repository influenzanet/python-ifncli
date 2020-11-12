
import os
from ifncli.api.response_parser import ResponseParser
from datetime import datetime
import pandas as pd

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml

class ResponseDownloader(Command):
    """
        Download reponses from a set of survey
    """

    name = "response:download"

    def get_parser(self, prog_name):
        parser = super(ResponseDownloader, self).get_parser(prog_name)
        parser.add_argument(
            "--filter_options_yaml", 
            help="script specific configuration file path", 
            default=os.path.join('resources', 'response_download_filter.yaml')
        )
        return parser
        
    def take_action(self, args):
        client = self.app.get_management_api()

        filter_config = read_yaml(args.filter_options_yaml)

        study_key = filter_config['study_key']
        survey_keys = filter_config['survey_keys']

        time_filter = {
                "from": datetime.strptime(filter_config['from'], "%Y-%m-%d"),
                "until": datetime.strptime(filter_config['until'], "%Y-%m-%d"),
            }

        # download survey definitions:
        survey_definitions = {}
        survey_parsers = {}
        responses = {}
        for key in survey_keys:
            survey_definitions[key] = client.get_survey_definition(
                study_key, key)
            survey_parsers[key] = ResponseParser(survey_definitions[key])
            responses[key] = []

        # get survey responses
        resps = client.get_survey_responses(
            study_key,
            start=time_filter["from"].timestamp(),
            end=time_filter["until"].timestamp()
        )

        for r in resps['responses']:
            try:
                parsed_response = survey_parsers[r['key']].parse_response(r)
                responses[r['key']].append(parsed_response)
            except KeyError as e:
                print(r['key'], e)

        for survey_key in survey_keys:
            results = pd.DataFrame(responses[survey_key])

            filename = study_key + '_' + survey_key + '_' + \
                time_filter['from'].strftime('%Y-%m-%d') + '-' + \
                time_filter['until'].strftime('%Y-%m-%d') + '.csv'
            if len(results) > 0:
                results.sort_values(by='submittedAt', inplace=True)
            results.to_csv(filename)

register(ResponseDownloader)