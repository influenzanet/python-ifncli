
from cliff.command import Command
from . import register
import requests
from typing import Dict,List
import json
from ..utils import Output
from datetime import datetime

class UserStatsCommand(Command):
    """
        Download user stats for user-stats-service
    """
    name = 'stats:users'

    def get_parser(self, prog_name):
        parser = super(UserStatsCommand, self).get_parser(prog_name)
       # parser.add_argument("--uri", type=str, help="URI of the service", default="/stats/users")
        parser.add_argument("--file", type=str, required=False, help="File to put the data")
       # parser.add_argument("--instance", help="Name of the instance")
        return parser

    def handle_data(self, counters:List):
        data = {}
        for counter in counters:
            name = counter['name']
            if not 'value' in counter or 'error' in counter:
                continue
            v = counter['value']
            data[name] = v['value']
        return data

    def take_action(self, args):
        
        cfg = self.app.get_configs()

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
        
        out = Output(args.file)

        data = self.handle_data(response.json())
        data["_time_"] = datetime.now().isoformat()
        out.write(json.dumps(data))
        
register(UserStatsCommand)