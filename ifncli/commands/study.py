import os
import json
import base64
import string
import sys
from datetime import datetime

from cliff.command import Command
from cliff.lister import Lister
from . import register

from ifncli.utils import read_yaml, read_json, json_to_list, readable_yaml, translatable_to_list, to_json

from ifncli.formatter import readable_expression, readable_study, readable_translatable, readable_survey, create_context, survey_to_dictionnary, survey_parser, survey_to_html

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

class ManageStudyMembers(Command):
    """
        Manage study members
    """
    name = 'study:manage-members'

    def get_parser(self, prog_name):
        parser = super(ManageStudyMembers, self).get_parser(prog_name)
        parser.add_argument(
            "--action", help="ADD or REMOVE", default='ADD')
        parser.add_argument(
            "--study_key", help="key of the study, the user should be added to or removed from", required=True)
        parser.add_argument(
            "--user_id", help="user id of the RESEARCHER user to be added", required=True)
        parser.add_argument(
            "--user_name", help="user name of the RESEARCHER user", required=True)
        return parser

    def take_action(self, args):
        action = args.action
        study_key = args.study_key
        user_id = args.user_id
        user_name = args.user_name

        client = self.app.get_management_api()

        if action == 'ADD':
            client.add_study_member(study_key, user_id, user_name)
        elif action == 'REMOVE':
            client.remove_study_member(study_key, user_id)
        else:
            raise('unknown action: ' + action)

class ListSurveys(Command):
    """
        List surveys
    """
    name = 'study:list-surveys'

    def get_parser(self, prog_name):
        parser = super(ListSurveys, self).get_parser(prog_name)
        parser.add_argument(
            "--study_key", help="key of the study", required=True)
        parser.add_argument(
            "--json", help="get the json", required=False, action="store_true")
        parser.add_argument(
            "--lang", help="Show only translation for lang", required=False, action="store", default=None)
        return parser

    def take_action(self, args):
        study_key = args.study_key
       
        client = self.app.get_management_api()

        surveys = client.get_surveys_in_study(study_key)

        if args.json:
            print(to_json(surveys))

        data = []

        ctx = create_context(language=args.lang)

        for s in surveys:
            d = {
                'key': s['surveyKey'],
                'name': readable_translatable(s['name'], ctx),
                'description': readable_translatable(s['description'], ctx)
            }
            data.append(d)

        print(readable_yaml(data))

class ListStudies(Lister):
    """
        List studies
    """
    name = 'study:list'

    def take_action(self, args):
        client = self.app.get_management_api()
        r = client.get_studies()
        return json_to_list(r, ['id','key','status'])


class ShowStudy(Command):
    """
        Show study
    """
    name = 'study:show'

    def get_parser(self, prog_name):
        parser = super(ShowStudy, self).get_parser(prog_name)
        parser.add_argument(
            "--study_key", help="key of the study", required=True)
        parser.add_argument(
            "--json", help="get the json", required=False, action="store_true")
        parser.add_argument("--lang", help="Show only translation for lang", required=False, action="store", default=None)
        return parser
    
    def take_action(self, args):
        client = self.app.get_management_api()
        study = client.get_study(args.study_key)
        if args.json:
            print(to_json(study))
            return
        
        ctx = create_context(language=args.lang)

        ss = readable_study(study, ctx)
        
        print(readable_yaml(ss))

class ShowSurvey(Command):
    """
        Show survey 

        Show a survey definition. By default render using a human readable presentation based on Yaml.
        --json option will output the raw json definition as returned by the API

    """
    name = 'study:show-survey'

    def get_parser(self, prog_name):
        parser = super(ShowSurvey, self).get_parser(prog_name)

        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--from-file", help="load survey from json file. Cannot be used with study_key", required=False, action="store")
        g.add_argument("--study_key", help="key of the study (survey from api). Cannot be used with from-file", required=False)
        
        parser.add_argument("--survey", help="key of the survey, ", required=False)
        parser.add_argument("--output", help="path of file to output results", required=False)
        parser.add_argument("--json", help="get the json (raw data from api)", required=False, action="store_true")
        parser.add_argument("--lang", help="Show only translation for lang", required=False, action="store", default=None)
        parser.add_argument("--format", help="Output format available 'human', 'dict-yaml','dict-json' default is 'human'", required=False, action="store", default=None)
        return parser
    
    def take_action(self, args):
        
        if args.from_file is not None:
            survey = read_json(args.from_file)
            if 'survey' in survey and isinstance(survey['survey'], dict):
                survey = survey['survey']
        else:
            if args.survey is None:
                raise Exception("survey argumen is missing. I need this to get the survey from the study")
            client = self.app.get_management_api()
            survey = client.get_survey_definition(args.study_key, args.survey)
            if survey is None:
                raise Exception("No survey available for %s:%s" % (args.study_key, args.survey))

        if args.output:
            need_close = True
            out = open(args.output, 'w')
        else:
            need_close = False
            out = sys.stdout

        if args.json:
            out.write(to_json(survey))
            return
        
        out_format = args.format 
        if out_format is None:
            out_format = "human"

        ctx = create_context(language=args.lang)
            
        if out_format == "human":
            ss = readable_survey(survey, ctx)
            out.write(readable_yaml(ss))
        
        if out_format in ["dict-json", "dict-yaml"]:
            ss = survey_to_dictionnary(survey)
            if out_format ==  "dict-yaml":
                out.write(readable_yaml(ss))
            else:
                out.write(json.dumps(ss))

        if out_format == "html":
            ss = survey_to_html(survey, ctx)
            out.write(ss)

        if need_close:
            out.close()



register(ImportSurvey)
register(CreateStudy)
register(UpdateSurveyRules)
register(ManageStudyMembers)
register(ListSurveys)
register(ListStudies)
register(ShowStudy)
register(ShowSurvey)