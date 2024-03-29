## Platform file
from pathlib import Path
from re import S
from typing import Dict, Optional,Union
from .utils import read_yaml
from os.path import dirname

class PlatformException(Exception):
    pass

# Determine which is the current implementation since it depends on platforms
_Path_ = type(Path())
class ResourcesLayoutPath(_Path_):
    """
        Resources path with helpers to find files on default location 
        if the directory follows the default layout organization
    """

    def __init__(self, *args, studies_path="study", auto_messages_path="auto_messages", **kwargs):
        self.studies_path = studies_path
        self.auto_messages_path = auto_messages_path

    def get_survey_file(self, study_key, name):
        return self.get_study_path(study_key) / 'surveys' / (name + ".json")

    def get_study_rules_file(self, study_key):
        return self.get_study_path(study_key) / 'studyRules.json'

    def get_study_props_file(self, study_key):
        return self.get_study_path(study_key) / 'props.yaml'

    def get_study_path(self, study_key)->_Path_:
        return self / self.studies_path / study_key

    def get_auto_messages_path(self, name)->_Path_:
        return self / self.auto_messages_path / name

class PlatformResources:
    """
        Platform resources
    
        Hold the current resource path and common variables

        Platform variables can be provided in the platform.yaml config if (at the root of the resource path) and in the config
        targeting a specific env

    """

    def __init__(self, path: Union[str, Path], overrides:Optional[Dict]):
        path =  Path(path)
        
        if not path.is_absolute():
            root_path = Path(dirname(__file__) + '/..').resolve()
            path = root_path / path

        self.path = ResourcesLayoutPath(path.resolve())
        if not self.path.is_dir():
            raise PlatformException("Resource path '%s' is not a directory" % (self.path))
        self.vars = {}
        self.vars_from = {} # Catch the source of the variables
        self.template_layout = None
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
            raise PlatformException("Loaded platform.yaml in '%s' is not dictionary" % p)
        if 'vars' in d:
            self._update_vars(d['vars'], 'platform_file')
        if 'template_layout' in d:
            p = self.path.joinpath(d['template_layout'])
            if not p.exists():
                raise PlatformException("Email template layout '%s' not found" % p)
            self.template_layout = p
        if 'studies_path' in d:
            p = self.path.joinpath(d['studies_path'])
            if not p.exists():
                raise PlatformException("Studies path '%s' not found" % p)
            self.path.studies_path = p
        if 'auto_messages_path' in d:
            p = self.path.joinpath(d['auto_messages_path'])
            if not p.exists():
                raise PlatformException("Auto messages path '%s' not found" % p)
            self.path.auto_messages_path = p

    def get_vars(self)->Dict:
        return self.vars

    def get_vars_from(self):
        return self.vars_from

    def get_path(self)->ResourcesLayoutPath:
        return self.path
        
    def get(self, name, default: None):
        return self.vars.get(name, default)
    
    def has(self, name):
        return name in self.vars

