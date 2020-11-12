import os
import json
import base64

from cliff.command import Command
from . import register

from ifncli.utils import read_yaml, read_json

def yaml_obj_to_loc_object(obj):
    loc_obj = []
    for k in obj.keys():
        loc_obj.append({
            "code": k,
            "parts": [{
                "str": obj[k]
            }]
        })
    return loc_obj

class CreateStudy(Command):
    """
        Create a new study
    """

    name = 'study:create'

    def get_parser(self, prog_name):
        parser = super(CreateStudy, self).get_parser(prog_name)
        parser.add_argument(
            "--study_def_path", help="folder with study def yaml and rules json", required=True
        )

        return parser


    def take_action(self, parsed_args):
        study_path = parsed_args.study_def_path
        print(study_path)

        study_def = read_yaml(os.path.join(study_path, "props.yaml"))
        rules = json.load(
            open(os.path.join(study_path, "study_rules.json"), 'r', encoding='UTF-8'))

        study_obj = {
            "study": {
                "key": study_def["studyKey"],
                "status": study_def["status"],
                "secretKey": study_def["secretKey"],
                "props": {
                    "systemDefaultStudy": study_def["props"]["systemDefaultStudy"],
                    "startDate": study_def["props"]["startDate"],
                    "name": yaml_obj_to_loc_object(study_def["props"]["name"]),
                    "description": yaml_obj_to_loc_object(study_def["props"]["name"]),
                    "tags": [{"label": yaml_obj_to_loc_object(t)} for t in study_def["props"]["tags"]]
                },
                "rules": rules
            }
        }

        client = self.app.get_management_api()
        client.create_study(study_obj)

class ImportSurvey(Command):
    """
        Import survey definition into a study
    """

    name = 'study:import-survey'

    def get_parser(self, prog_name):
        parser = super(ImportSurvey, self).get_parser(prog_name)
        parser.add_argument(
            "--replace", help="if to replace any existing survey definition, without keeping the history", default=False)
        parser.add_argument(
            "--study_key", help="study key to which study the survey should be saved", required=True)
        parser.add_argument(
            "--survey_json", help="path to the survey json", required=True)

        return parser

    def take_action(self, args):
        
        study_key = args.study_key
        survey_path = args.survey_json
        replaceExisting = args.replace

        client = self.app.get_management_api()

        survey_def = read_json(survey_path)

        survey_key = survey_def['survey']['current']['surveyDefinition']['key']
        survey_def['studyKey'] = study_key
        survey_def['survey']['current']['published'] = int(
            datetime.now().timestamp())

        existing_survey_def = client.get_survey_definition(study_key, survey_key)

        if existing_survey_def is None or replaceExisting:
            client.save_survey_to_study(study_key, survey_def)
        else:
            history = []
            if 'history' in existing_survey_def.keys():
                history = existing_survey_def['history']

            existing_survey_def['current']['unpublished'] = int(
                datetime.now().timestamp())
            history.append(
                existing_survey_def['current']
            )
            survey_def['survey']['history'] = history
            client.save_survey_to_study(study_key, survey_def)

class UpdateSurveyRules(Command):
    """
        Update rules of a survey
    """
    name = 'study:update-rules'

    def get_parser(self, prog_name):
        parser = super(ImportSurvey, self).get_parser(prog_name)
        parser.add_argument(
                "--rules_json_path", help="file path to the survey rules json", required=True)
        parser.add_argument(
            "--study_key", help="study key, the rules should be updated for", required=True)

    def take_action(self, args):
        study_key = args.study_key
        rules_path = args.rules_json_path

        client = self.app.get_management_api()

        rules = read_json(rules_path)
        client.update_study_rules(study_key, rules)


register(ImportSurvey)
register(CreateStudy)
register(UpdateSurveyRules)