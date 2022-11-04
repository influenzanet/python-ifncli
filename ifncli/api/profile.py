
from pathlib import Path
from ..utils import read_yaml
from ..platform import PlatformResources
from . import ManagementAPIClient
from typing import Dict

class ApiProfile:
    """
        ApiProfile manages configuration of an account to connect to a given platform

        The "profile" is stored in a yaml file

    """

    def __init__(self, repository, name: str):
        file = name + '.yaml'
        path = Path(repository) / file
        if not path.exists:
            Exception("Unable to load " + path)
        self.config = read_yaml(path)

    def get_client(self)->ManagementAPIClient: 
        """
            get API client for the profile
        """
        user_credentials = self.config["user_credentials"]
        management_api_url = self.config["management_api_url"]
        participant_api_url = self.config["participant_api_url"]
        client = ManagementAPIClient(management_api_url, user_credentials, participant_api_url, verbose=False)
        return client
       
    def get_config(self)->Dict:
        """
            Get all the config
        """
        return self.config

    def get_vars(self):
        return self.config['vars']

    def get_resources_path(self)->str:
        return self.config['resources_path']

    def get_platform(self)->PlatformResources:
        """
            Get The PlatformResources for this profile
            It provides an object style API to get location for files to update the platform
        """
        resources_path = self.get_resources_path()
        overrides = self.get_vars()

        if resources_path is None:
            raise Exception("Resource path must be provided either in config file or as command option")
        return PlatformResources(resources_path, overrides=overrides)
