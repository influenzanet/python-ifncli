import sys
import os
from pathlib import Path
from cliff.app import App
from cliff.commandmanager import CommandManager

from ifncli.utils import read_yaml
from ifncli.commands import get_commands
from ifncli.api.management_api import ManagementAPIClient

class MyApp(App):
    
    def build_option_parser(self, description, version):
        parser = super(MyApp, self).build_option_parser(
            description,
            version,
        )
        parser.add_argument(
            "-c",
            "--config",
            help="Config path",
            default=os.path.join('resources', 'config.yaml')
        )

        self._configs = {}
        self._apis = {}

       # self.plugin_manager.build_option_parser(parser)

        return parser

    def initialize_app(self, argv):
        commands = get_commands()
        for command in commands:
            if hasattr(command, 'name'):
                name = command.name
            else:
                name = command.__name__
            self.command_manager.add_command(name.lower(), command)

    def prepare_to_run_command(self, cmd):
        cfg_path = self.options.config
        
        cfg_path = os.getenv('IFN_CONFIG', cfg_path)
        
        if not Path(cfg_path).is_file():
            raise Exception("Unable to find config file at %s" % (cfg_path,))
        try:
            self._configs = read_yaml(cfg_path)
        except:
            print("Unable to load configuration file")
            raise
    
    def get_management_api(self):
        if 'management' in self._apis:
            return self._apis['management']
        user_credentials = self._configs["user_credentials"]
        management_api_url = self._configs["management_api_url"]
        participant_api_url = self._configs["participant_api_url"]

        client = ManagementAPIClient(management_api_url, user_credentials, participant_api_url )
        self._apis['management'] = client
        return client

def main(argv=sys.argv[1:]):
    app = MyApp(
            description="InfluenzaNet CLI",
            version="0.0.1",
            command_manager=CommandManager('ifncli'),
            deferred_help=True,
        )
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main())