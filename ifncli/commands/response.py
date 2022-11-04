
import os
from datetime import datetime, timedelta

from cliff.command import Command
from . import register

from ..utils import read_yaml

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
        Download responses from a set of survey (not implemented yet)
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
        raise NotImplementedError("Not implementent yet")

register(ResponseDownloader)