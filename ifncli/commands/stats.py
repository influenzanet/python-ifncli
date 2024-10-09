
from cliff.command import Command
from . import register
import requests
from typing import Dict,List
import json
from ..utils import Output,write_content
from datetime import datetime

class UserStatsCommand(Command):
    """
        Download user stats for user-stats-service
    """
    name = 'stats:users'

    def get_parser(self, prog_name):
        parser = super(UserStatsCommand, self).get_parser(prog_name)
        parser.add_argument("--file", type=str, required=False, help="File to put the data")
        parser.add_argument("--layout", action="store_true", help="Use stats directory layout to put files")
        
        return parser

    def handle_data(self, counters:List):
        data = {}
        for counter in counters:
            name = counter['name']
            if not 'value' in counter or 'error' in counter:
                continue
            v = counter['value']
            data[name] = v
        return data

    def take_action(self, args):
        
        cfg = self.app.appConfigManager.get_configs()

        instance = cfg['user_credentials']['instanceId']
        
        if not 'users_stats' in cfg:
            raise Exception("'users_stats' should be provided in config")
        
        conf = cfg['users_stats']
        url = conf['url']
        auth = conf['basic_auth']
        
        url += '/fetch/'+ instance

        response = requests.get(url, auth=('stats', auth))
        if response.status_code != 200:
            raise response.raise_for_status()
        
        now = datetime.now()

        if args.layout:
            if not 'stats_path' in conf:
                raise Exception("--layout option requires 'stats_path' in 'users_stats' config entry")
            stats_path = conf['stats_path']
            filename = now.strftime("%Y%m%d%H%M")
            file = "%s/%s.json" % (stats_path, filename)
        else:
            file = args.file

        out = Output(file)

        data = self.handle_data(response.json())
        data["_time_"] = now.isoformat()
        out.write(json.dumps(data))
        if args.layout:
            # Write last file
            write_content("%s/last" % stats_path, filename)
        
register(UserStatsCommand)