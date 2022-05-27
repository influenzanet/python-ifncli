import sys
import os
from pathlib import Path
from cliff.app import App
from cliff.commandmanager import CommandManager

from ifncli.utils import read_yaml
from ifncli.commands import get_commands
from ifncli.api import ManagementAPIClient
from ifncli.platform import PlatformResources

class ConfigException(Exception):
    pass

class MyApp(App):
    
    def build_option_parser(self, description, version):
        parser = super(MyApp, self).build_option_parser(
            description,
            version,
        )
        parser.add_argument(
            "-c",
            "--config",
            help="Config path (if not present will look IFN_CONFIG env variable",
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
        """
            Preparation of the environment 
        
        """
        cfg_path = self.options.config
        
        cfg_path = os.getenv('IFN_CONFIG', cfg_path)
        
        if os.getenv('IFN_CONFIG') is None and os.getenv('INF_CONFIG') is not None:
            print("INF_CONFIG is defined, are you sure you didnt mistyped IFN_CONFIG ?")

        if not Path(cfg_path).is_file():
            raise ConfigException("Unable to find config file at %s" % (cfg_path,))
        try:
            self._configs = read_yaml(cfg_path)
            self._configs['__config_file'] = cfg_path
        except:
            print("Unable to load configuration file")
            raise
    
    def get_management_api(self):
        if 'management' in self._apis:
            return self._apis['management']
        user_credentials = self._configs["user_credentials"]
        management_api_url = self._configs["management_api_url"]
        participant_api_url = self._configs["participant_api_url"]

        client = ManagementAPIClient(management_api_url, user_credentials, participant_api_url, verbose=False)
        self._apis['management'] = client
        return client

    def get_configs(self, what=None, must_exist=True):
        """
            Get App configs
            @param what entry to get, return all if None (default)
            @param must_exist if True, raise an error if 'what' entry doesnt exists, if False returns None if entry doesnt exist
        """
        if what is not None:
            if not must_exist and what not in self._configs:
                return None
            return self._configs[what]
        
        return self._configs
    
    def get_platform(self, resources_path=None)->PlatformResources:
        """
            Get The platform object
        """
        if resources_path is None:
            resources_path = self._configs.get('resources_path', None)
        overrides = self._configs.get('vars', None)

        if resources_path is None:
            raise ConfigException("Resource path must be provided either in config file or as command option")
        return PlatformResources(resources_path, overrides=overrides)
            
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