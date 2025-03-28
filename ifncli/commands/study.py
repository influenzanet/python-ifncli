import os
import json
import sys
import time
from datetime import datetime
import re
from cliff.command import Command
from cliff.lister import Lister
from . import register
from pathlib import Path
from cliff.formatters.table import TableFormatter  


from ..utils import read_yaml, read_json, json_to_list, readable_yaml, to_json, read_content, write_json, Output

from influenzanet.surveys import readable_study, readable_translatable, readable_survey, create_context, survey_to_dictionnary, survey_to_html, read_survey_json
from influenzanet.surveys.influenzanet.loader import survey_transform_to_12

def yaml_obj_to_loc_object(obj):
    """ 
        Transform Yaml key value dict to a localized text structure
    """
    loc_obj = []
    for k in obj.keys():
        loc_obj.append({
            "code": k,
            "parts": [{
                "str": obj[k]
            }]
        })
    return loc_obj    

def extract_survey_args(study_key, from_name):
    """
        Resolve study_key and survey_key with the 2 arguments study_key and from_name
        Can be provided :
          - separately (from_name only contains survey_key)
          - Only in 
    """
    survey_key = None
    if from_name is not None:
        if '/' in from_name:
            if study_key is not None:
                raise Exception("Study key must be provided either in name or in separated parameter not both")
        n = from_name.split('/')
        if len(n) != 2:
            raise Exception("name can only contains 2 elements (study_key/survey_key) ")
        if len(n) == 2:
            study_key = n[0]
            survey_key = n[1]
        else:
            survey_key = n[0]
    return [study_key, survey_key]

class CreateStudy(Command):
    """
        Create a new study
    """

    name = 'study:create'

    def get_parser(self, prog_name):
        parser = super(CreateStudy, self).get_parser(prog_name)
        parser.add_argument("--secret-from", help="Get secret key from this file, default=$study_path/secret", required=False)
        parser.add_argument("--dry-run", help="Show the study json but do not submit", required=False, action="store_true")

        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--study-def-path", help="folder with study def yaml and rules json")
        g.add_argument("--study-key", "--study", help="Key of the study (will use default layout in resources path)")
    
        return parser

    def take_action(self, args):
        study_path = args.study_def_path
        secret_file = args.secret_from

        if args.study_key:
            path = self.app.appConfigManager.get_platform().get_path()
            study_path = path.get_study_path(args.study_key).resolve()
            study_props_path = path.get_study_props_file(args.study_key)
            study_rules_path = path.get_study_rules_file(args.study_key)
        else:
            study_props_path = os.path.join(study_path, "props.yaml")
            study_rules_path = os.path.join(study_path, "studyRules.json")
        
        study_def = read_yaml(study_props_path)
        rules = read_json(study_rules_path)
        
        if secret_file is None:
            default_secret_file = os.path.join(study_path, "secret")
            if os.path.exists(default_secret_file):
                secret_file = default_secret_file

        secret = read_content(secret_file, must_exist=True)

        if secret == "":
            raise Exception("Study secret cannot be empty")

        if "secretKey" in study_def:
            raise Exception("Secret must not be provided in props.yaml but as external secret file")

        startDate = study_def["props"]["startDate"]

        study_obj = {
            "study": {
                "key": study_def["studyKey"],
                "status": study_def["status"],
                "secretKey": secret,
                "props": {
                    "systemDefaultStudy": study_def["props"]["systemDefaultStudy"],
                    "startDate": startDate,
                    "name": yaml_obj_to_loc_object(study_def["props"]["name"]),
                    "description": yaml_obj_to_loc_object(study_def["props"]["description"]),
                    "tags": [{"label": yaml_obj_to_loc_object(t)} for t in study_def["props"]["tags"]]
                },
                "rules": rules
            }
        }

        if "configs" in study_def.keys():
            allowParticipantFiles = study_def["configs"]["allowParticipantFiles"]
            idMappingMethod = study_def["configs"]["idMappingMethod"]
            study_obj["study"]["configs"] = {
                "participantFileUploadRule": {
                    "name": "gt",
                    "data": [
                        { "dtype": "num", "num": 1},
                        { "dtype": "num", "num": 0 if allowParticipantFiles == True else 2 }
                    ]
                },
                "idMappingMethod": idMappingMethod
            }

        if args.dry_run:
            print(study_obj)
            return

        client = self.app.appConfigManager.get_management_api()
        client.create_study(study_obj)

class ImportSurvey(Command):
    """
        Import survey definition into a study
    """

    name = 'study:import-survey'

    def get_parser(self, prog_name):
        parser = super(ImportSurvey, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="study key to which study the survey should be saved", required=False)
        parser.add_argument("--input-format", help="input survey format: v1.1, [v1.2]", default="v1.2", required=False)
        
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument("--survey-json", "--json", help="path to the survey json", required=False)
        group.add_argument("--from-name", help="Name of the survey (can be study-key/survey-key) if the files are organized following the common layout", required=False)

        return parser

    def take_action(self, args):

        study_key, survey_key = extract_survey_args(args.study_key, args.from_name)

        client = self.app.appConfigManager.get_management_api()

        if survey_key is not None:        
            path = self.app.appConfigManager.get_platform().get_path()
            survey_path = path.get_survey_file(study_key, survey_key)
        else:
            survey_path = args.survey_json
            survey_path = Path(survey_path)    

        if not survey_path.exists():
            print("Unable to find file '%s'" % (survey_path))
            return

        print("Using survey in '%s'" % survey_path)

        survey_def = read_json(survey_path)

        if args.input_format == "v1.1":
            survey_def = survey_transform_to_12(survey_def, preserve_item_version=True)

        resp = client.save_survey_to_study(study_key, survey_def)
        print("Survey uploaded id=%s  version=%s" % ( resp['id'], resp['versionId']))

def old_survey_upload(client, survey_def, study_key):
    survey_key = survey_def['survey']['current']['surveyDefinition']['key']
    survey_def['studyKey'] = study_key
    survey_def['survey']['current']['published'] = int(datetime.now().timestamp())

    existing_survey_def = client.get_survey_definition(study_key, survey_key)

    if existing_survey_def is None:
        print("Creating new survey '%s' in study '%s'" % (survey_key, study_key))
        client.save_survey_to_study(study_key, survey_def)
    else:
        history = []
        if 'history' in existing_survey_def.keys():
            history = existing_survey_def['history']

        existing_survey_def['current']['unpublished'] = int(datetime.now().timestamp())
        history.append(
            existing_survey_def['current']
        )
        survey_def['survey']['history'] = history
        print("Replacing current version in survey '%s' in study '%s'" % (survey_key, study_key))
        client.save_survey_to_study(study_key, survey_def)

class UpdateSurveyRules(Command):
    """
        Update rules of a study
    """
    name = 'study:update-rules'

    def get_parser(self, prog_name):
        parser = super(UpdateSurveyRules, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="study key, the rules should be updated for", required=True)
        
        g = parser.add_mutually_exclusive_group()
        g.add_argument("--rules_json_path", help="file path to the survey rules json", required=False)
        g.add_argument("--default", help="Use default file at resources path for the study", required=False, action="store_true")

        return parser

    def take_action(self, args):
        study_key = args.study_key
        
        if args.default:
            platform_path = self.app.appConfigManager.get_platform().get_path()
            rules_path = platform_path.get_study_rules_file(study_key)
        else:
            rules_path = args.rules_json_path

        client = self.app.appConfigManager.get_management_api()

        rules = read_json(rules_path)
        client.update_study_rules(study_key, rules)

class ManageStudyMembers(Command):
    """
        Manage study members
    """
    name = 'study:manage-members'

    def get_parser(self, prog_name):
        parser = super(ManageStudyMembers, self).get_parser(prog_name)
        parser.add_argument("--action", help="ADD or REMOVE", default='ADD')
        parser.add_argument("--study_key",  "--study", help="key of the study, the user should be added to or removed from", required=True)
        parser.add_argument("--user_id","--user-id", help="user id of the RESEARCHER user to be added", required=True)
        parser.add_argument("--user_name", "--user-name", help="user name of the RESEARCHER user", required=True)
        return parser

    def take_action(self, args):
        action = args.action
        study_key = args.study_key
        user_id = args.user_id
        user_name = args.user_name

        client = self.app.appConfigManager.get_management_api()

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
        parser.add_argument("--study_key", "--study", help="key of the study", required=True)
        parser.add_argument("--json", help="get the json", required=False, action="store_true")
        parser.add_argument("--lang", help="Show only translation for lang", required=False, action="store", default=None)
        return parser

    def take_action(self, args):
        study_key = args.study_key
       
        client = self.app.appConfigManager.get_management_api()

        surveys = client.get_surveys_in_study(study_key, extract_infos=True)

        if args.json:
            print(to_json(surveys))

        data = []

        ctx = create_context(language=args.lang)

        for s in surveys:
            d = {
                'key': s['surveyKey'],
                'name': readable_translatable(s['name'], ctx),
                'description': readable_translatable(s['description'], ctx),
            }
            if 'metadata' in s:
                d['metadata'] = s['metadata']

            data.append(d)

        print(readable_yaml(data))

class ListSurveysVersions(Lister):
    """
        List surveys version
    """
    name = 'study:survey-versions'

    def get_parser(self, prog_name):
        parser = super(ListSurveysVersions, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="key of the study", required=True)
        parser.add_argument("--survey", "--study", help="key of the survey", required=True)
        parser.add_argument("--raw", help="get the raw data", required=False, action="store_true")
        parser.add_argument("--json", help="get the json", required=False, action="store_true")
        parser.add_argument("--yaml", help="show readable yaml", required=False, action="store_true")
        self.formatter = TableFormatter()
       
        return parser

    def take_action(self, args):
        study_key = args.study_key
       
        client = self.app.get_management_api()

        surveys = client.get_survey_history(study_key, args.survey)

        if 'surveyVersions' not in surveys:
            raise ValueError("Unable to get versions in response")
            
        surveys = surveys['surveyVersions']

        if args.json:
            print(to_json(surveys))
            return
        
        if args.yaml:
            print(readable_yaml(surveys))
            return
        
        data = []
        for survey in surveys:
            try:
                published = int(survey['published'])
            except ValueError:
                published = 0
            if published > 0:
                d = datetime.fromtimestamp(published)
                pub_date = d.isoformat()
            else:
                pub_date = "Unknown"
            d = (survey['id'], pub_date, survey['versionId'], survey['surveyDefinition']['key'])
            data.append(d)
        return (
                ('id','published', 'version', 'key'), 
                data
            )
        
class ListStudies(Command):
    """
        List studies
    """
    name = 'study:list'

    def take_action(self, args):
        client = self.app.appConfigManager.get_management_api()
        r = client.get_studies()
        return json_to_list(r, ['id','key','status'])


class ShowStudy(Command):
    """
        Show study
    """
    name = 'study:show'

    def get_parser(self, prog_name):
        parser = super(ShowStudy, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="key of the study", required=True)
        parser.add_argument("--json", help="get the json", required=False, action="store_true")
        parser.add_argument("--lang", help="Show only translation for lang", required=False, action="store", default=None)
        return parser
    
    def take_action(self, args):
        client = self.app.appConfigManager.get_management_api()
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
        g.add_argument("--study_key", "--study", help="key of the study (survey from api). Cannot be used with from-file", required=False)
        
        parser.add_argument("--survey", help="key of the survey, ", required=False)
        parser.add_argument("--output", help="path of file to output results", required=False)
        parser.add_argument("--json", help="get the json (raw data from api)", required=False, action="store_true")
        parser.add_argument("--lang", help="Show only translation for lang", required=False, action="store", default=None)
        parser.add_argument("--format", help="Output format available 'human', 'dict-yaml','dict-json', html default is 'human'", required=False, action="store", default=None)
        return parser
    
    def take_action(self, args):
        
        if args.from_file is not None:
            survey = read_survey_json(args.from_file)
            if 'survey' in survey and isinstance(survey['survey'], dict):
                survey = survey['survey']
        else:
            if args.survey is None:
                raise Exception("survey argument is missing. I need this to get the survey from the study")
            client = self.app.appConfigManager.get_management_api()
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

class CustomStudyRules(Command):
    """
        Execute a custom study rules 

        Show a survey definition. By default render using a human readable presentation based on Yaml.
        --json option will output the raw json definition as returned by the API

    """
    name = 'study:custom-rules'

    def get_parser(self, prog_name):
        parser = super(CustomStudyRules, self).get_parser(prog_name)
        parser.add_argument("--rules", help="Rules files", required=True, action="store")
        parser.add_argument("--study", "--study_key", help="key of the study (survey from api)", required=True)
        parser.add_argument("--output", help="path of file to output results", required=False)
        parser.add_argument("--dry-run", help="Prepare but do not send", required=False, action="store_true")
        parser.add_argument("--done-file", help="File to write participant ids done with success", required=False)
        parser.add_argument("--exclude-done", help="Read done file and dont redo for those in file", required=False, action="store_true")
        
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--all", help="All participants", required=False, action="store_true")
        g.add_argument("--pid", help="Participants id (coma separated for several)", required=False)
        g.add_argument("--pid-file", help="Participants id from this file (exclusive with pid), if json dictionary needs --pid-json-* option", required=False)

        g2 = parser.add_mutually_exclusive_group(required=False)
        
        g2.add_argument("--pid-json-keys", help="Use key of json dictionary", required=False, action="store_true")
        g2.add_argument("--pid-json-values", help="Use values of json dictionary", required=False, action="store_true")
        

        # parser.add_argument("--format", help="Output format available 'human', 'dict-yaml','dict-json', html default is 'human'", required=False, action="store", default=None)
        return parser

    def take_action(self, args):
        study_key = args.study
        rules_path = args.rules
        dry_run = args.dry_run
        client = self.app.appConfigManager.get_management_api()
        
        participants = None
        done_file = None
        
        if args.pid is not None:
            participants = args.pid.split(',')
            participants = [x.strip() for x in participants]
                
        if args.pid_file is not None:
            if args.pid_file.endswith('.json'):
                participants = read_json(args.pid_file)
                if not isinstance(participants, list):
                    if isinstance(participants, dict):
                        if not args.pid_json_keys and not args.pid_json_values:
                            raise Exception("Participant json dictionary must have either --pid-json-keys or --pid-json-values options")
                        if args.pid_json_keys:
                            participants = list(participants.keys())
                        if args.pid_json_values:
                            participants = list(participants.values())
                    else:
                        raise Exception("participant json file must be a dictionary or a list")

            else:            
                with open(args.pid_file, 'r') as f:
                    participants = f.readlines()
                participants = [x.strip() for x in participants]

        if not args.all:
            print(" Participants loaded : %d" % len(participants))
            done_file = args.done_file
            exclude_done = args.exclude_done
            if done_file is not None and exclude_done:
                with open(done_file, 'r') as f:
                        exclude = f.readlines()
                exclude = [x.strip() for x in exclude]
                print(" Participants to be excluded : %d" % len(exclude))
                participants = list(filter(lambda x: x not in exclude, participants))
                print(" Participants kept : %d" % len(participants))

        rules = read_json(rules_path)
        
        if args.all:
            # Only 
            if dry_run:
                print("[fake] dry-run mode, call run_custom_study_rules for all participants")
                resp = []
            else:
                resp = client.run_custom_study_rules(study_key, rules)
            print(resp)
        else:
            if len(participants) == 0:
                print("No participant in list, aborting")
                return
            resp = {}
            max_batch = 100
            sleep_batch = 1
            count_errors = 0
            count_ok = 0
            count_run = 0
            for pid in participants:
                print("Appplying to %s" % pid, end="")
                count_run += 1
                if dry_run:
                    print("[fake] dry-run call for %s" % pid)
                    r = {}
                else:
                    try:
                        r = client.run_custom_study_rules_for_single_participant(study_key, rules, pid)
                        count_ok += 1
                        print("  OK")
                        if done_file is not None:
                            with open(done_file, 'a') as f:
                                f.write(pid + "\n")
                    except Exception as e:
                        count_errors += 1
                        print(" Error")
                        r = {'error': str(e)}
                resp[pid] = r
                if (count_run % max_batch) == 0:
                    print("Sleep")
                    time.sleep(sleep_batch)
                    
        output = Output(args.output)
        output.write(readable_yaml(resp))
        if not args.all:
            print("Count OK: %d  Errors: %d" % (count_ok, count_errors))

class ShowStudyCurrentRules(Command):
    """
        Show study
    """
    name = 'study:rules:current'

    def get_parser(self, prog_name):
        parser = super(ShowStudyCurrentRules, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="key of the study", required=True)
        parser.add_argument("--output", help="Output file", required=False, default=None)
        return parser
    
    def take_action(self, args):
        client = self.app.get_management_api()
        rules = client.current_study_rules(args.study_key)
        output = Output(args.output)
        output.write(json.dumps(rules))

class ShowStudyRulesHistory(Command):
    """
        Show study
    """
    name = 'study:rules:history'

    def get_parser(self, prog_name):
        parser = super(ShowStudyRulesHistory, self).get_parser(prog_name)
        parser.add_argument("--study_key", "--study", help="key of the study", required=True)
        parser.add_argument("--output", help="Output file", required=False, default=None)
        return parser
    
    def take_action(self, args):
        client = self.app.get_management_api()
        rules = client.study_rules_history(args.study_key)
        output = Output(args.output)
        output.write(json.dumps(rules))

class BulkApplyRules(Command):
    """
        Execute a custom study rules for each participant (each participant has different rules)
        Rules are provided as a dictionnary with participant id as key and rules as value
    """
    name = 'study:rules:bulk'

    def get_parser(self, prog_name):
        parser = super(BulkApplyRules, self).get_parser(prog_name)
        parser.add_argument("--rules", help="Rules files", required=True, action="store")
        parser.add_argument("--study", "--study_key", help="key of the study (survey from api)", required=True)
        parser.add_argument("--dry-run", help="Prepare but do not send", required=False, action="store_true")
        parser.add_argument("--max-run", help="Maximum count to run", required=False, default=0, type=int)
        parser.add_argument("--max-batch", help="Maximum count by round", required=False, default=100, type=int)
        
        return parser

    def take_action(self, args):
        study_key = args.study
        dry_run = args.dry_run
        max_run = args.max_run
        max_batch = args.max_batch
        client = self.app.get_management_api()
        rules = read_json(args.rules)
        
        print("Loaded rules for %d participants" % (len(rules)))

        if not isinstance(rules, dict):
            raise Exception("Must be an dictionary, key is particpant is and value is exoression")
        
        done_file = args.rules + '.done'
        if os.path.isfile(done_file):
            done = read_json(done_file)
            print("Resuming from %s with %d already done" % (done_file, len(done)))
        else:
            done = {}

        sleep_batch = 1
        count_errors = 0
        count_ok = 0
        count_run = 0
            
        for participant_id, rule in rules.items():
            if participant_id in done:
                continue
            count_run += 1
            if dry_run:
                print("[fake] dry-run mode, call run_custom_study_rules for all participants")
            else:
                try:
                    print("%s" % (participant_id))
                    if isinstance(rule, dict):
                        rule = [rule]
                    r = client.run_custom_study_rules_for_single_participant(study_key, rule, participant_id)
                    count_ok += 1
                except Exception as e:
                    count_errors += 1
                    print(" Error", e)
                    r = {'error': str(e)}
                done[participant_id] = r
                write_json(done_file, done)
            if (count_run % max_batch) == 0:
                print("Sleeping...")
                time.sleep(sleep_batch)
            if max_run > 0 and count_run >= max_run:
                print("Max run reached, stopping")
                break
        print("Count OK: %d  Errors: %d" % (count_ok, count_errors))


register(BulkApplyRules)
register(ShowStudyRulesHistory)
register(ShowStudyCurrentRules)
register(ImportSurvey)
register(CreateStudy)
register(UpdateSurveyRules)
register(ManageStudyMembers)
register(ListSurveys)
register(ListStudies)
register(ShowStudy)
register(ShowSurvey)
register(CustomStudyRules)
register(ListSurveysVersions)