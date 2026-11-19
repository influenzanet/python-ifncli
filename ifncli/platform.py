## Platform file
import sys
from os.path import dirname
from pathlib import Path

from .utils import read_yaml


class PlatformException(Exception):
    pass

# Determine which is the current implementation since it depends on platforms
_Path_ = type(Path())
class ResourcesLayoutPath(_Path_):
    """
        Resources path with helpers to find files on default location 
        if the directory follows the default layout organization
    """

    def __init__(self, *args, studies_path="study", auto_messages_path="auto_messages", whatsapp_templates_path="whatsapp_templates", **kwargs):
        # Since Python 3.12 pathlib initializes Path in __init__ (before, only in __new__)
        if sys.version_info >= (3, 12):
            super().__init__(*args)
        self.studies_path = studies_path
        self.auto_messages_path = auto_messages_path
        self.whatsapp_templates_path = whatsapp_templates_path

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

    def get_whatsapp_templates_path(self)->_Path_:
        return self / self.whatsapp_templates_path

    def get_whatsapp_template_file(self, language, name)->_Path_:
        return self.get_whatsapp_templates_path() / language / (name + ".json")

class PlatformResources:
    """
        Platform resources
    
        Hold the current resource path and common variables

        Platform variables can be provided in the platform.yaml config if (at the root of the resource path) and in the config
        targeting a specific env

    """

    def __init__(self, path: str | Path, overrides:dict | None):
        path =  Path(path)
        
        if not path.is_absolute():
            root_path = Path(dirname(__file__) + '/..').resolve()
            path = root_path / path

        self.path = ResourcesLayoutPath(path.resolve())
        if not self.path.is_dir():
            raise PlatformException("Resource path '{}' is not a directory".format(self.path))
        self.vars = {}
        self.vars_from = {} # Catch the source of the variables
        self.template_layout = None
        self.load_platform_config()
        if overrides is not None:
            self._update_vars(overrides, 'config')

    def _update_vars(self, data:dict, source_name):
        for name, value in data.items():
            self.vars[name] = value
            self.vars_from[name] = source_name

    def load_platform_config(self):
        p = self.path.joinpath('platform.yaml')
        if not p.exists():
            return 
        d = read_yaml(p)
        if not isinstance(d, dict):
            raise PlatformException(f"Loaded platform.yaml in '{p}' is not dictionary")
        if 'vars' in d:
            self._update_vars(d['vars'], 'platform_file')
        if 'template_layout' in d:
            p = self.path.joinpath(d['template_layout'])
            if not p.exists():
                raise PlatformException(f"Email template layout '{p}' not found")
            self.template_layout = p
        if 'studies_path' in d:
            p = self.path.joinpath(d['studies_path'])
            if not p.exists():
                raise PlatformException("Studies path '{}' not found".format(p))
            self.path.studies_path = p
        if 'auto_messages_path' in d:
            p = self.path.joinpath(d['auto_messages_path'])
            if not p.exists():
                raise PlatformException("Auto messages path '{}' not found".format(p))
            self.path.auto_messages_path = p
        if 'whatsapp_templates_path' in d:
            p = self.path.joinpath(d['whatsapp_templates_path'])
            if not p.exists():
                raise PlatformException("WhatsApp templates path '{}' not found".format(p))
            self.path.whatsapp_templates_path = p

    def get_vars(self)->dict:
        return self.vars

    def get_vars_from(self):
        return self.vars_from

    def get_path(self)->ResourcesLayoutPath:
        return self.path
        
    def get(self, name, default: None):
        return self.vars.get(name, default)
    
    def has(self, name):
        return name in self.vars

