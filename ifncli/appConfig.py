"""
App Configuration Manager
"""

import sys

from .config import ConfigManager, ConfigException
from .platform import PlatformResources
from influenzanet.api import ManagementAPIClient

class AppConfigManager(ConfigManager):
    def __init__(self, cfg_path=None):
        super().__init__()

        self._configs = {}
        self._apis = {}
        self.api_shown = False

        self._cfg_path = cfg_path
        self._configs = self.load(self._cfg_path)

    def switch(self, name: str):
        super().switch(name)
        # reload the configuration
        self._configs = self.load(self._cfg_path)
        # clear the cached api client
        self._apis = {}

    def get_management_api(self):
        """
        Helper to get the Management API client. Commands should never instantiate directly the client,
        but ask for it from this method
        """
        if 'management' in self._apis:
            client = self._apis['management']
            client.renew_token()
            return client
        user_credentials = self._configs["user_credentials"]
        management_api_url = self._configs["management_api_url"]
        participant_api_url = self._configs["participant_api_url"]

        client = ManagementAPIClient(management_api_url, user_credentials, participant_api_url, verbose=False)
        self._apis['management'] = client

        if not self.api_shown:
            current_context = self.get_current()
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

    def get_platform(self, resources_path=None) -> PlatformResources:
        """
        Get The platform object
        """
        if resources_path is None:
            resources_path = self._configs.get('resources_path', None)
        overrides = self._configs.get('vars', None)

        if resources_path is None:
            raise ConfigException("Resource path must be provided either in config file or as command option")
        return PlatformResources(resources_path, overrides=overrides)
