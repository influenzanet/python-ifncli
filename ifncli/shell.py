import sys
import os
from pathlib import Path
from cliff.app import App
from cliff.commandmanager import CommandManager

from .utils import read_yaml
from .commands import get_commands
from influenzanet.api import ManagementAPIClient
from .platform import PlatformResources
from .config import ConfigManager, ConfigException

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

        # Current loaded config
        self._configs = {}
        self._apis = {}

        # Config contexts
        self.api_shown = False

        self.configManager = ConfigManager()

        self.plugin = None

        try:
            from plugins import Plugin
            self.plugin = Plugin()
        except:
            pass
    
       # self.plugin_manager.build_option_parser(parser)

        return parser

    def initialize_app(self, argv):
        commands = get_commands()
        if self.plugin is not None:
            commands.extend(self.plugin.get_commands())
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
        self._configs = self.configManager.load(cfg_path=self.options.config)
    
    def get_management_api(self):
        """
            Helper to get the Management API client. Commands should never instanciate directly the client,
            but ask for it from this method
        
        """
        if 'management' in self._apis:
            return self._apis['management']
        user_credentials = self._configs["user_credentials"]
        management_api_url = self._configs["management_api_url"]
        participant_api_url = self._configs["participant_api_url"]

        client = ManagementAPIClient(management_api_url, user_credentials, participant_api_url, verbose=False)
        self._apis['management'] = client

        if not self.api_shown:
            current_context = self.get_current_context()
            print("Connected to [%s] <%s>@%s on %s" % (current_context, user_credentials['email'], user_credentials['instanceId'], management_api_url), file=sys.stderr)
            self.api_shown = True

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

    def get_current_context(self):
        return self.configManager.get_current()
            
def main(argv=sys.argv[1:]):
    if len(argv) == 0:
        argv = ["help"]
    app = MyApp(
            description="InfluenzaNet CLI",
            version="0.0.1",
            command_manager=CommandManager('ifncli'),
            deferred_help=True,
        )
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main())