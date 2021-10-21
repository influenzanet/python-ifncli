from collections import OrderedDict
import json
from typing import Dict, List, Optional
from ifncli.commands import survey
from ifncli.surveys.influenzanet.dictionnary import ItemDictionnary
from ifncli.surveys.influenzanet.survey import SurveyItem, SurveySingleItem
from ifncli.surveys import standard
from ifncli.surveys.standard.models import (MATRIX_CHOICE_TYPE, MULTIPLE_CHOICE_TYPE)
from ifncli.surveys.standard.parser import json_parser_survey_standard
from ifncli.utils import read_json, read_yaml

from .. import influenzanet
from ..standard import StandardQuestion, StandardSurvey

from urllib import request
from urllib.error import URLError

class ConfigError(Exception):
    pass

def read_from_url(url):
    try:
        with request.urlopen(url) as response:
            standard_json = response.read()
            return standard_json
    except URLError as e:
        if hasattr(e, 'reason'):
            raise ConfigError("read_from_url(%s): %s" % (url, e.reason,))
        else:
            raise ConfigError("read_from_url(%s): %s" % (url, e.code))

class ValidatorProblem:

    MISSING = 'question_missing'
    NOT_DEFINED = 'question_unknown'
    WRONG_TYPE = 'wrong_type'
    MISSING_VALIDATION = 'missing_validation'
    OPT_NOT_DEFINED = 'option_unknown'
    OPT_MISSING = 'option_missing'

    def __init__(self, type:str, name:str, expected:Optional[str]=None, given:Optional[str]=None) -> None:
        self.type = type
        self.name = name
        self.given = given
        self.expected = expected
        self.known = False

    def to_readable(self, ctx):
        d = {'type': self.type, 'name': self.name, 'known': self.known}
        if self.expected is not None:
            d['expected'] = self.expected
        if self.given is not None:
            d['given'] = self.given
        return d

ValidatorProblem.TYPES = [
    ValidatorProblem.MISSING,
    ValidatorProblem.NOT_DEFINED,
    ValidatorProblem.WRONG_TYPE,
    ValidatorProblem.MISSING_VALIDATION,
    ValidatorProblem.OPT_MISSING,
    ValidatorProblem.OPT_NOT_DEFINED,
]

class ValidatorProfile:
    """
    ValidationProfile define parameters describing how to do the validation against the standard.
    It embeds parameters to map survey to the standard and options to mute some expected anomalies
    """
    def __init__(self):
        self.prefix = None
        self.standard = None
        self.standard_from = None
        self.expected = None

    @staticmethod
    def create(data):
        """
        Create the profile from a dictionnary (from a yaml or json file)

        Example:
        standard:
          # Full Path 
          file: 'path/to/standard.json' # Full name of the standard
          # Or directly from git repo
          name: 'standard_name' # name of the standard
          repo: 'influenzanet/surveys-standards' # repo name (optionnal, only if dont want default)
          revision: 'master' # revision in the repo, optionnal only if not master last commit
          # OR directly URL where to get the json standard

        prefix: 'key prefix to remove '
        expected: # Expected differences with the standard
          question_missing: [ "list of missing questions or pattern like Q10c*..."]
          question_unknown: [ "list of not expected questions or pattern like Q10c*..."]

        """
        p = ValidatorProfile()
        
        prefixes = data['prefix']
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        p.prefixes = prefixes

        if not 'standard' in data:
            raise ConfigError("standard entry expected")
        std = data['standard']
        p.standard_from = std
        if 'expected' in data:
            p.expected = p.load_expected(data['expected'])
        return p

    def load_expected(self, expected:dict)-> Dict:
        for n, v in expected.items():
            if not n in ValidatorProblem.TYPES:
                raise ConfigError("Unknown problem %s in expected" % (n, ))
        return expected            

    def load_standard(self):
        std = self.standard_from
        standard_json = None
        url = None
        if 'file' in std:
            try:
                standard_json = read_json(std['file'])
            except Exception as e:
                raise ConfigError("Unable to load standard from '%s' %s" % (std['file'], e) )
        if 'name' in std:
            name = std['name']
            if 'repo' in std:
                repo = std['repo']
            else:
                repo = 'influenzanet/surveys-standards'
            if 'revision' in std:
                revision = std['revision']
            else:
                revision = 'master'
            url = 'https://github.com/%s/blob/%s/surveys/%s/survey.json?raw=true' % (repo, revision, name)
        if 'url' in std:
            url = std['url']
        if url is not None:
            standard_json = json.loads(read_from_url(url))
            #print(standard_json)

        self.standard = json_parser_survey_standard(standard_json)

COMPATIBLE_TYPES = {
    standard.SINGLE_CHOICE_TYPE : [influenzanet.RGROLES.SINGLE, influenzanet.RGROLES.DROPDOWN],
    standard.MULTIPLE_CHOICE_TYPE : influenzanet.RGROLES.MULTIPLE,
    standard.DATE_TYPE: influenzanet.RGROLES.DATE,
    standard.MATRIX_CHOICE_TYPE: influenzanet.RGROLES.MATRIX,
}

class SurveyStandardValidator:
    """"Validate a survey definition compliance to a standard survey description

    """

    def __init__(self, profile: ValidatorProfile):
        """
            profile: ValidatorProfile
            Structure embedding information about how to process the validation
            Which standard and where to find it, and validation options
        
        """
        self.profile = profile
        self.standard = profile.standard

        
    @staticmethod
    def profile_from_yaml(file: str):
        """
            Read Profile from yaml file
            Validation profile is expected to be under a 'profile' entry
        """
        p = read_yaml(file)
        profile = ValidatorProfile.create(p['profile'])
        profile.load_standard()
        return profile
    
    def validate(self, definition:influenzanet.SurveyItem):
        """Validate survey definition to the standard

        Parameters
        ------
            definition: influenzanet.SurveyItem
                Survey definition to validate (usually the "current" component)

            options: ValidatorProfile
                Validation profile describes how to do the validation
        """

        problems = []
        
        expected = OrderedDict()
        for quid, q in self.standard.questions.items():
            if q.active:
                expected[quid] = q
        items = definition.flatten()
        for item in items:
            if item.is_group():
                continue
            rg = item.get_dictionnary()
            if rg is None:
                # Not a question
                continue

            item_key = item.key
            
            item_key = self.remove_prefix(item_key)
            if not item_key in expected:
                problems.append(ValidatorProblem(ValidatorProblem.NOT_DEFINED, item_key))
                continue
            std = expected[item_key]
            self.compare_question(item, rg, std, problems)
            del expected[item_key]
            
        if len(expected) > 0:
            # Question not found, mark them as missing
            for e in expected:
                problems.append(ValidatorProblem(ValidatorProblem.MISSING, e))

        # Flag problems with expected rules
        self.validate_problems(problems)

        return problems

    def remove_prefix(self,  item_key):
        """
            Remove prefix for item key from registred ones
        """
        if self.profile.prefixes is None:
            return item_key
        for prefix in self.profile.prefixes:
            if item_key.startswith(prefix):
                return item_key[len(prefix):]
        return item_key

    def validate_problems(self, problems:List[ValidatorProblem]):
        """
            Flag problems as known considering expected rules
            rules can be a question, a pattern (* for starting with), or a option with the form [question].[option key]
        """
        expected = self.profile.expected
        if expected is None:
            return
        for problem in problems:
            for pb_type in ValidatorProblem.TYPES:
                if(problem.type == pb_type):
                    if self.problem_in_list(expected, pb_type , problem.name):
                        problem.known = True

    def problem_in_list(self, expected: Dict, problem_type, name):
        knowns = expected.get(problem_type, None)
        if knowns is None:
            return False
        for known in knowns:
            if known.find('*') >= 0:
                pattern = known.replace('*', '')
                return name.startswith(pattern)
            else:
                if name == known:
                    return True
        return False

    def compare_question(self, item:SurveySingleItem, rg: Optional[ItemDictionnary], std: StandardQuestion, problems: List[ValidatorProblem]):
        expected_types = COMPATIBLE_TYPES.get(std.type, None)
        if expected_types is not None:
            if isinstance(expected_types, list):
                found = rg.type in expected_types
            else:
                found = rg.type == expected_types
            if not found:
                problems.append(ValidatorProblem(ValidatorProblem.WRONG_TYPE, std.data_name, expected_types, rg.type))
        if std.mandatory:
            if item.validations is None:
                problems.append(ValidatorProblem(ValidatorProblem.MISSING_VALIDATION, item.key))
        
        if len(std.responses) == 0:
            return
        expected_keys = OrderedDict()
        for r in std.responses.values():
            expected_keys[r.value] = r
        if rg.options is not None:
            for r in rg.options:
                if r.item_key in expected_keys:
                    del expected_keys[r.item_key]
                else:
                    problems.append(ValidatorProblem(ValidatorProblem.OPT_NOT_DEFINED, std.data_name + '.' + r.item_key))
        
        for name,k in expected_keys.items():
            problems.append(ValidatorProblem(ValidatorProblem.OPT_MISSING, std.data_name + '.' + name))
                
    def filter_known(self, problems: List[ValidatorProblem])->List[ValidatorProblem]:
        pp = []
        for p in problems:
            if p.known:
                continue
            pp.append(p)
        return pp
