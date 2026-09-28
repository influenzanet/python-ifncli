from cliff.command import Command
from . import register
from influenzanet.surveys.repository import SurveyRepositoryAPI, ApiError
from ..utils import readable_yaml
from typing import Tuple, Any, Dict, List
import datetime
import json

def get_repository_api(app)->Tuple[SurveyRepositoryAPI, Dict[str, Any]]:
    configs = app.appConfigManager.get_configs('survey_repository', must_exist=False)
    if configs is None:
        raise RuntimeError("Survey Repository is not in configuration ('survey_repository'), command not available")
    return (SurveyRepositoryAPI(configs), configs)

class SurveyDefinitionProvider:
    """
        Loader for Survey Definitions
    """

    def __init__(self, client, study_key, survey):
        self.study_key = study_key
        self.survey = survey
        self.client = client
        self.versions = ['']

    def version(self, version=''):
        return self.client.get_survey_definition(self.study_key, self.survey, version_id=version)
    
    def load_published_versions(self, published_after=None):
        """
            Load all available versions in the platform for a given survey
        """
        versions = self.client.get_survey_history(self.study_key, self.survey)
        if 'surveyVersions' not in versions:
            return []
        vv = []
        
        if published_after is not None:
            after_time = int(published_after.timestamp())
        else:
            after_time = None
        
        for v in versions['surveyVersions']:
            published = int(v['published'])
            if after_time is not None and published < after_time:
                continue
            vv.append( (v['versionId'], published) )
        vv.sort(key=lambda x : x[1], reverse=True)
        self.versions = [ x[0] for x in vv ]
        return self.versions


def get_surveys_for_study(configs, study, must_exists:bool=True):
    """"
        configs : sections survey_repository of the config
    """
    if 'studies' in configs:
        if not isinstance(configs['studies'], dict):
            raise ValueError("`studies` in configuration must be a dictionnary")
        surveys = configs['studies'].get(study, None)
        if surveys is None:
            if must_exists:
                raise ValueError("No entry for {} in survey_repository.studies".format(study))
            return None
        if not isinstance(surveys, list):
            raise ValueError("Entry {} in survey_repository.studies of the configuration must be a list".format(study))
        return surveys
    
def parse_surveys_list(surveys:List[str])->Dict[str, str]:
    """
        parse list with survey name, and optionaly recoding with form new_name=survey_key
    """
    out = {}
    if surveys is None:
        return out
    for s in surveys:
        if '=' in s:
            survey_def = s.split('=')
            survey_key = survey_def[1]
            survey_name = survey_def[0]
        else:
            survey_key = s
            survey_name = s
        survey_key = survey_key.strip()
        survey_name= survey_name.strip()
        out[survey_name] = survey_key
    return out
              

class SurveyRepositoryImport(Command):
    """
        Import published surveys of the platform into the repository
    """

    name = "survey:repo:import"

    def get_parser(self, prog_name):
        parser = super(SurveyRepositoryImport, self).get_parser(prog_name)
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--all-versions", help="Import all versions of survey(s)", action="store_true")
        parser.add_argument("--published-after", help="Only survey published after this time")
        parser.add_argument("--dry-run", help="Only prepare but do not send the survey", action="store_true")
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--survey", help="Survey key (several if comma separated)")
        g.add_argument("--defaults", help="Use the defaults surveys for study in survey_repository.studies", action="store_true")
        return parser

    def load_uploaded_versions(self, repo:SurveyRepositoryAPI, survey:str, model_type:str):
        versions = repo.list_surveys(platforms=[repo.platform_code], names=[survey], types=[model_type], short=True)
        vv = []
        for v in versions['data']:
            vv.append(v['version'])
        return vv
    
    def survey_list(self, surveys, study, configs, use_defaults):
        if use_defaults:
            print("Using default surveys in config for study '%s'" % (study))
            surveys = get_surveys_for_study(configs=configs, study=study)
            if surveys is None:
                raise ValueError("No surveys found in config for study '%s'" % (study))
        else:
            if not isinstance(surveys, str):
                raise ValueError("Surveys is not a string")
            surveys = surveys.split(',')
        return parse_surveys_list(surveys)

    def take_action(self, args):
        repo, configs = get_repository_api(self.app)
        client = self.app.get_management_api()

        dry_run = args.dry_run

        surveys = self.survey_list(args.survey, args.study, configs, args.defaults)

        if args.published_after is not None:
            published_after =  datetime.fromisoformat(args.published_after)
        else:
            published_after = None

        if not args.all_versions:
            print("Only load the current published survey for each survey key")

        limiter = None
        
        for survey_name, survey_key in surveys.items():
            print("Survey {}".format(survey_key))
            provider = SurveyDefinitionProvider(client, args.study, survey=survey_key)

            if args.all_versions:
                known_versions = self.load_uploaded_versions(repo, survey_key, model_type='D')
                versions = provider.load_published_versions(after=published_after)
                print("Loaded {} versions, repository has {} versions".format(len(versions), len(known_versions)))
            else:
                known_versions = None
                versions = [''] # Empty version only load the current version

            for version_id in versions:
                if version_id == "":
                    version_str = "current"
                else:
                    version_str = version_id
                print(" - '{}'".format(version_str), end=None)
                if known_versions is not None:
                    if version_id in known_versions:
                        print("already in repo, skipped.")
                        continue

                survey = provider.version(version_id)

                data = json.dumps(survey)
                try:
                    if dry_run:
                        print("dry-run mode, nothing uploaded")
                    else:
                        if limiter is not None:
                            limiter.wait()
                        r = repo.import_survey(data, name=survey_name)
                        if r.created:
                            msg = "Created"
                        else:
                            msg = "Already imported"
                        print("#{} {} {}".format(r.id, r.version, msg))
                        if hasattr(r, 'limiter'):
                            limiter = r.limiter
                except ApiError as e: 
                    handled = False
                    if e.is_too_many_request():
                        if e.wait_retry_after():
                            handled = True
                    if not handled:
                        print(e)
                        print(e.response.headers)

class SurveyRepositoryList(Command):

    name = "survey:repo:list"

    def get_parser(self, prog_name):
        parser = super(SurveyRepositoryList, self).get_parser(prog_name)
        return parser

    def take_action(self, args):
        repo, config = get_repository_api(self.app)
        r = repo.list_surveys()
        print(readable_yaml(r))

register(SurveyRepositoryList)
register(SurveyRepositoryImport)
