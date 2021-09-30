from collections import OrderedDict
import json
from ifncli.commands import survey
from ifncli.formatter.models.survey import SurveyItem, SurveySingleItem
from ifncli.formatter.survey import standard
from ifncli.formatter.survey.standard.models import (MATRIX_CHOICE_TYPE, MULTIPLE_CHOICE_TYPE)
from ifncli.formatter.survey.standard.parser import json_parser_survey_standard
from ifncli.utils import read_json, read_yaml

from .. import models
from .standard import StandardQuestion, StandardSurvey

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

class ValidatorProfile:
    """
    ValidationProfile define parameters describing how to do the validation against the standard.
    It embeds parameters to map survey to the standard and options to mute some expected anomalies
    """
    def __init__(self):
        self.prefix = None
        self.standard = None
        self.standard_from = None

    @staticmethod
    def create(data):
        """
        Create the profile from a dictionnary (from a yaml or json file)

        Example:
        standard:
          file: 'path/to/standard.json'
        survey:
          prefix: 'key prefix to remove '


        """
        p = ValidatorProfile()
        p.prefix = data['prefix']
        if not 'standard' in data:
            raise ConfigError("standard entry expected")
        std = data['standard']
        p.standard_from = std
        return p

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
            print(standard_json)

        self.standard = json_parser_survey_standard(standard_json)
            

COMPATIBLE_TYPES = {
    standard.SINGLE_CHOICE_TYPE : models.RG_TYPE_SINGLE,
    standard.MULTIPLE_CHOICE_TYPE : models.RG_TYPE_MULTIPLE,
    standard.DATE_TYPE: models.RG_TYPE_DATE,
    standard.MATRIX_CHOICE_TYPE: models.RG_TYPE_MATRIX,
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
    
    def validate(self, definition:models.SurveyItem):
        """Validate survey definition to the standard

        Parameters
        ------
            definition: models.SurveyItem
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
            if self.profile.prefix is not None:
                if item_key.startswith(self.profile.prefix):
                    item_key = item_key[len(self.profile.prefix):]
            if not item_key in expected:
                problems.append({'type': 'not_defined', 'name': item_key})
                continue
            std = expected[item_key]
            self.compare_question(item, rg, std, problems)
            del expected[item_key]
            
        if len(expected) > 0:
            for e in expected:
                problems.append({'type': 'missing', 'name': e})

        return problems

    def compare_question(self, item:SurveySingleItem, rg, std: StandardQuestion, problems: list):
        expected_type = COMPATIBLE_TYPES.get(std.type, None)
        if expected_type is not None:
            if rg.type != expected_type:
                problems.append({'type':'wrong_type', 'name':item.key, 'expected': expected_type})
        if std.mandatory:
            if item.validations is None:
                problems.append({'type':'missing_validation', 'name':item.key})

    