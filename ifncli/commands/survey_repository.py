from cliff.command import Command
from . import register
from influenzanet.surveys.repository import SurveyRepositoryAPI, ApiError
from ..utils import readable_yaml
import datetime
import json

def get_repository_api(app)->SurveyRepositoryAPI:
    configs = app.appConfigManager.get_configs('survey_repository', must_exist=False)
    if configs is None:
        raise RuntimeError("Survey Repository is not in configuration ('survey_repository'), command not available")
    return SurveyRepositoryAPI(configs)


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


class SurveyRepositoryImport(Command):
    """
        Import published surveys of the platform into the repository
    """

    name = "survey:repo:import"

    def get_parser(self, prog_name):
        parser = super(SurveyRepositoryImport, self).get_parser(prog_name)
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--survey", help="Survey key (several if comma separated)", required=True)
        parser.add_argument("--all-versions", help="Import all versions of survey(s)", action="store_true")
        parser.add_argument("--published-after", help="Only survey published after this time")
        return parser

    def load_uploaded_versions(self, repo:SurveyRepositoryAPI, survey:str, model_type:str):
        versions = repo.list_surveys(platforms=[repo.platform_code], names=[survey], types=[model_type], short=True)
        vv = []
        for v in versions['data']:
            vv.append(v['version'])
        return vv

    def take_action(self, args):
        repo = get_repository_api(self.app)
        client = self.app.get_management_api()

        surveys = str(args.survey).split(',')

        if args.published_after is not None:
            published_after =  datetime.fromisoformat(args.published_after)
        else:
            published_after = None

        if not args.all_versions:
            print("Only load the current published survey for each survey key")

        for survey_key in surveys:
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
                    r = repo.import_survey(data)
                    if r.created:
                        msg = "Created"
                    else:
                        msg = "Already imported"
                    print("#{} {} {}".format(r.id, r.version, msg))
                except ApiError as e: 
                    print(e)

class SurveyRepositoryList(Command):

    name = "survey:repo:list"

    def get_parser(self, prog_name):
        parser = super(SurveyRepositoryList, self).get_parser(prog_name)
        return parser

    def take_action(self, args):
        repo = get_repository_api(self.app)
        r = repo.list_surveys()
        print(readable_yaml(r))

register(SurveyRepositoryList)
register(SurveyRepositoryImport)
