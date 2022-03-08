## Platform file
from pathlib import Path
from typing import Dict, Optional,Union
from .utils import read_yaml

class PlatformException(Exception):
    pass


class PlatformResources:
    """
        Platform resources
    
        Hold the current resource path and common variables

    """

    def __init__(self, path: Union[str, Path], overrides:Optional[Dict]):
        self.path = Path(path)
        if not self.path.is_dir():
            raise PlatformException("Resource path '%s' is not a directory" % (self.path))
        self.vars = {}
        self.vars_from = {} # Catch the source of the variables
        self.load_platform_config()
        if overrides is not None:
            self._update_vars(overrides, 'config')

    def _update_vars(self, data:Dict, source_name):
        for name, value in data.items():
            self.vars[name] = value
            self.vars_from[name] = source_name

    def load_platform_config(self):
        p = self.path.joinpath('platform.yaml')
        if not p.exists():
            return 
        d = read_yaml(p)
        if not isinstance(d, dict):
            raise PlatformException("Loaded platform.yaml is not dictionnary")
        if 'vars' in d:
            self._update_vars(d['vars'], 'platform_file')

    def get_vars(self)->Dict:
        return self.vars

    def get_vars_from(self):
        return self.vars_from

    def get_path(self):
        return self.path
        
    def get(self, name, default: None):
        return self.vars.get(name, default)
    
    def has(self, name):
        return name in self.vars