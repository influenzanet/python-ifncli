
import os
from ifncli.api.response_parser import ResponseParser
from datetime import datetime, timedelta
import pandas as pd

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml

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

        client = ManagementAPIClient(management_api_url, user_credentials)

        # download survey definitions:
        survey_definitions = {}
        survey_parsers = []

        for key in survey_keys:
            survey_definitions[key] = client.get_survey_definition(
                study_key, key)

            if 'history' in survey_definitions[key].keys():
                print(key + ' versions: ', len(survey_definitions[key]['history']) + 1)
                for old_version in survey_definitions[key]['history']:
                    try:
                        published = old_version['published']
                    except KeyError:
                        published = 0

                    survey_parsers.append({
                        'key': key,
                        'published': published,
                        'unpublished': old_version['unpublished'],
                        'parser': ResponseParser(old_version['surveyDefinition']),
                        'responses': []
                    })
            try:
                published = survey_definitions[key]['current']['published']
            except KeyError:
                published = 0

            survey_parsers.append({
                'key': key,
                'published': published,
                'unpublished': None,
                'parser': ResponseParser(survey_definitions[key]['current']['surveyDefinition']),
                'responses': []
            })

        # get survey responses
        all_responses = []
        filter_start = time_filter['from']
        while filter_start < min(time_filter['until'], datetime.now() + timedelta(days=1)):
            filter_end = min(filter_start + timedelta(days=14), time_filter['until'])
            print('-------------------------')
            print('Fetching data between: ', filter_start, filter_end)
            resps = client.get_survey_responses(
                study_key,
                start=filter_start.timestamp(),
                end=filter_end.timestamp()
            )
            filter_start = filter_end
            if 'responses' in resps.keys():
                all_responses.extend(resps['responses'])
                print('downloaded count: ', len(resps['responses']))
            else:
                print('no data found in interval')

        print('Response count: ', len(all_responses))

        for r in all_responses:
            current_parser = get_survey_parser_based_on_time(survey_parsers, r['key'], int(r['submittedAt']))
            # print(r['key'], r['submittedAt'], current_parser)
            try:
                parsed_response = current_parser['parser'].parse_response(r)
                current_parser['responses'].append(parsed_response)
            except KeyError as e:
                print(r['key'], e)
            except TypeError as e:
                print(r['key'], e)
                continue

        export_folder = os.path.join(os.path.dirname(__file__), 'export_' + datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(export_folder,
                    exist_ok=True)
        for p in survey_parsers:
            results = pd.DataFrame(p['responses'])

            start = datetime.fromtimestamp(int(p['published']))
            end = p['unpublished']
            if end is not None:
                end = datetime.fromtimestamp(int(end))
            else:
                end = datetime.max

            if time_filter['from'] > start:
                start = time_filter['from']

            if time_filter['until'] < end:
                end = time_filter['until']

            filename = study_key + '_' + p['key'] + '_' + \
                    start.strftime('%Y-%m-%d') + '-' + \
                    end.strftime('%Y-%m-%d') + \
                    '.csv'

            filename = os.path.join(export_folder, filename)

            if len(results) > 0:
                results.sort_values(by='submittedAt', inplace=True)
                results.to_csv(filename)
                print('Write to: ', filename)
            else:
                print('Skipped empty: ', filename)

register(ResponseDownloader)