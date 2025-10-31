
from datetime import datetime
from typing import Optional
from ifncli.utils import ISO_TIME_FORMAT, readable_yaml, write_content
from os import path, mkdir
import re
 
class ExportSetupGenerator:
    """
        ExportSetupGenerator creates interactively profile to export data
    """
    
    def __init__(self, resources_path:str):
        self.resources_path = resources_path
        self.default_surveys: list[str] =  ['intake','weekly','vaccination']
        self.exported_surveys: Optional[list[str]] = None
        self.generated_files = []

    def ask(self, label: str, validator=None, default=None, description=None, instruction=None):
        if description is not None:
            print(description)
        if instruction is not None:
                label = "{} ({})".format(label, instruction)
        if default is not None:
                label = "{} [{}]".format(label, default)
        label = label + ': '
        while True:
            value = input(label)
            if value == "" and default is not None:
                return default
            if validator is not None:
                value = validator(value)
                if value is not None:
                    return value
            else:
                if value != "":
                    return value

    def ask_choices(self, label, choices, default=None, description=None, lowercase=True):
        if lowercase:
            trans = lambda x: x.lower()
        else:
            trans = lambda x: x
        if isinstance(choices, list):
            def validator(value):
                value = trans(value)
                if value in choices:
                    return value
                return None
            instruction = '/'.join(choices)
        if isinstance(choices, dict):
            def validator(value):
                value = trans(value)
                return choices.get(value)
            instruction = '/'.join(choices.keys())
        return self.ask(label, validator=validator, default=default, description=description, instruction=instruction)

    def ask_yn(self, label, description=None):
        choices = {'y': True, 'yes':True, 'n':False, 'no':False }
        return self.ask_choices(label, choices=choices, description=description)

    def ask_date(self, label:str, description:Optional[str]=None):
        def validator(value):
            if value == "":
                return None
            try:
                v = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return v.strftime(ISO_TIME_FORMAT)
            except Exception as e:
                print(e)
                return None
        return self.ask(label, validator=validator, instruction="date using 'YYYY-MM-DD HH:mm:SS' format", description=description)

    def ask_for_surveys(self)->list[str]:
        use_custom_surveys = self.ask_yn(label="Customize surveys", description="Do you want to customize surveys list to export (if no will export intake,weekly,vaccination)")
    
        if use_custom_surveys:
            surveys = []
            for survey in self.default_surveys:
                y = self.ask_yn("Add survey {} ?".format(survey))
                if y:
                    surveys.append(survey)
            extra_surveys = self.ask("Enter extra survey names (space separated), empty for none")
            extra_surveys = self.parse_survey_list(extra_surveys)
            if len(extra_surveys) > 0:
                surveys.extend(extra_surveys)
        else:
            surveys = self.default_surveys
        return surveys

    def setup_export_profile(self, save_path:Optional[str]=None):
        print("This script will setup configuration to synchonize platform raw data")
        
        study_name = self.ask("Enter the study name")
        start_date = self.ask_date("Enter the starting date and time of the export (first response to export)")

        use_ending_date = self.ask_yn("Do you want to use a maximum date (if 'no' will use 'now' as ending date)")
        if use_ending_date:
            ending_date = self.ask_date("Enter the maximum date to export")
        else:
            ending_date = 'now'
        
        surveys = self.ask_for_surveys()

        self.exported_surveys = surveys
        
        language = self.ask("Language code used for the survey language (e.g. 'en', 'fr',...)")

        export_profile = {
            'study_key': study_name,
            'surveys': surveys,
            'start_time': start_date,
            'max_time': ending_date,
            'survey_info': {
                'lang': language
            }
        }

        profile_data = readable_yaml(export_profile)
        
        print("Generated profile :")
        print("---")
        print(profile_data)
        print("---")

        save = self.ask_yn("Save this profile")
        if save:
            if save_path is None:
                default_path = self.resources_path + '/export/export-db.yml'
                save_path = input("Where to put the export configuration [{}]".format(default_path))
                if save_path == "":
                    save_path = default_path
            self.save_file(save_path, profile_data)

    def setup_build_plan(self, data_path = None, save_path:Optional[str]=None):
        if data_path is None:
            data_path = '{data_path}'
        print("For source & target database path, it's possible to use absolute path or prefix the file path by {data_path}. It will be replaced by a provided path on run")
        source_db = self.ask("Source db path", default='{data_path}/export.db')
        target_db = self.ask("Source db path", default='{data_path}/export.duck')

        surveys = None

        if self.exported_surveys is not None:
            reuse_exported = self.ask_yn("Use the same surveys as previously ({})".format(','.join(self.exported_surveys)))
            if reuse_exported:
                surveys = self.exported_surveys
        if surveys is None:
            surveys = self.ask_for_surveys()
        
        surveys_def = {}
        for survey_name in surveys:
            surveys_def[survey_name] = None
        
        data = {
            'source_db': source_db,
            'target_db': target_db,
            'surveys': surveys_def
        }

        content = readable_yaml(data)

        print("Generated build profile :")
        print("---")
        print(content)
        print("---")
        save = self.ask_yn("Save this profile")
        if save:
            if save_path is None:
                default_path = self.resources_path + '/export/build.yml'
                save_path = input("Where to put the export configuration [{}]".format(default_path))
                if save_path == "":
                    save_path = default_path
            self.save_file(save_path, profile_data)
        
    
    def parse_survey_list(self, value):
        value = re.split(r"n |,", value)
        value = [ x.strip() for x in value ]
        value = [ x for x in value if x != "" ]
        return value
            

    def save_file(self, file, content):
        dir = path.dirname(file)
        if not path.exists(dir):
            create = self.ask_yn("Directory {} does not exist, create ?")
            if create:
                mkdir(dir)
        write_content(file, content)


        
    
        