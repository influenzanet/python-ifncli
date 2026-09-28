
from ifncli.utils.io import read_yaml
from typing import Optional, Union
import os

from .profile import BuilderProfile
from .trace import DictWithOrigin

import copy

ProfileType = dict[str, str]

def check_path_exits(file):
    file_path = os.path.dirname(file)
    return os.path.exists(file_path)

class BuilderPlanError(Exception):
    pass

class BuilderPlan:
    """
        BuilderPlan embeds configuration to build analysis database for several surveys
        Configuration holds source (raw data) and target (duckdb) database file path and list of surveys to build table for
        Each survey is associated with a set of parameters called build profile.
        The profile can be provided using 3 ways:
            - with the survey declaration 
            - using a predefined profile (provided in the 'profiles' section)
            - from an external file, using a prefix '@' before the file path
    """
    def __init__(self, data_path: Optional[str]=None):
        """
            data_path: optional path to resolve path for source & target db if they contains {data_path}
        """
        self.source_db: str = ''
        self.target_db: str = ''
        self.data_path = data_path
        self.profiles: dict[str, ProfileType] = {}
        self.surveys: dict[str, BuilderProfile] = {}
        self.file: Optional[str] = None
    
    def error(self, message):
        if self.file is not None:
            message = "{} in {}".format(message, self.file)
        return BuilderPlanError(message)

    def relative_file(self, file):
        """
            Resolve file path, if not absolute, file path is relative to the plan file (if defined)
        """
        if os.path.isabs(file):
                return file
        if self.file is not None:
            file_dir = os.path.dirname(self.file)
        else:
            file_dir = '.'
        return os.path.join(file_dir, file)

    def data_file(self, file):
        if '{data_path}' in file:
            if self.data_path is None:
                raise BuilderPlanError("{data_path} cannot be resolved if data_path is None")
            file = file.replace('{data_path}', self.data_path)
        return file

    def load_file(self, file):
        """
            Load plan from a file
        """
        self.file = file
        plan = read_yaml(file) 
        if 'source_db' in plan:
            self.source_db = self.data_file(plan['source_db'])
        if 'target_db' in plan:
            self.target_db = self.data_file(plan['target_db'])
        self.parse_profiles(plan)
        self.parse_surveys(plan)

    def parse_profiles(self, plan):
        """
            Profiles are predefined named list of profiles that can be reused in 'surveys' section
            It can be used if several surveys share the same profile
        """        
        if 'profiles' in plan:
            pp = plan['profiles']
            if not isinstance(pp, dict):
                raise self.error("'profiles' entry must be a dictionnary")
            for name, values in pp.items():
                if not isinstance(values, dict):
                    raise self.error(f"entry profiles.{name} must be a dictionnary")
                self.profiles[name] = values
    
    def parse_surveys(self, plan):
        """
            Parse surveys entry, surveys to build are provided as a dictionary.
            Key is the survey name to build data for.
            Value can be a string referring a name in 'profiles' or a file if it starts with '@'
            It's also possible to provide a dictionary with the profile values directly for this survey 
        """
        if  'surveys' not in plan:
            raise self.error("'surveys' entry is expected")
        ss = plan['surveys']
        
        if not isinstance(ss, dict):
            raise self.error("'surveys' entry must be a dictionnary")

        # Profile defaults will be used as default values (common)
        # For profiles
        profile_defaults = {
            'source_db': self.source_db,
            'target_db': self.target_db,
        }
        
        # List of values that cannot be provided in an external profile file
        # A plan aims to be consistent, so you cannot use an external file using another database for example
        non_overridable = ['survey', 'target_db', 'source_db']

        for survey_name, survey_def in ss.items():
            
            survey_origin = f"surveys.{survey_name}" # Where data comes from in plan file
            profile_data = DictWithOrigin(profile_defaults, values_origin="plan file")
            profile_data.set_from('survey', survey_name, survey_origin)

            if survey_def is not None :
                if isinstance(survey_def, dict):
                    # If dict, profile parameters are provided directly by the entry
                    profile_data.merge_from(survey_def, origin=survey_origin)
                elif isinstance(survey_def, str):
                    if survey_def.startswith('@'):
                        # Profile params defined in an external file
                        profile_file = file_path(survey_def[1:])
                        pp = BuilderProfile.load_form_file(profile_file)
                        for key in non_overridable:
                            if key in pp:
                                print(f"Warning : {key} is defined in {profile_file} but cannot be overriden. Value in plan will be used")
                                pp[key] = None
                        profile_data.merge_from(pp, allow_none=False)
                    else:
                        if survey_def not in self.profiles:
                            raise self.error(f"surveys.{survey_name} {survey_def} profile is not in profiles list")

                        pp = copy.deepcopy(self.profiles[survey_def])
                        
                        profile_data.merge_from(pp, origin=f("profiles.{survey_def}"), allow_none=False)
                else:
                    raise self.error(f"surveys.{survey_name} must be a dictionnary or a string")
            try:
                profile = BuilderProfile(profile_data)
            except Exception as e:
                raise self.error(f"Error in profile for survey {survey_name}") from e            
            self.surveys[survey_name] = profile

    def to_dict(self):

        surveys = {}
        for name, profile in self.surveys.items():
            surveys[name] = profile.to_readable()
        
        return {
            'source_db': self.source_db,
            'target_db': self.target_db,
            'surveys': surveys
        }