from datetime import datetime
from ifncli.formatter.survey.validator import SurveyStandardValidator, ValidatorProfile

from cliff.command import Command
from . import register

from ifncli.formatter.survey import survey_parser
from ifncli.utils import read_json, readable_yaml

class SurveyValidateStandard(Command):
    """
        Compare survey with standard definition
    """

    name = 'survey:standard'

    def get_parser(self, prog_name):
        parser = super(SurveyValidateStandard, self).get_parser(prog_name)
        parser.add_argument(
            "--survey", help="path to the survey json", required=True,
        )
        parser.add_argument(
            "--profile",help="path to the validation profile", required=True,
        )
        return parser

    def take_action(self, args):
        survey = read_json(args.survey)

        if "studyKey" in survey:
            # A study entry
            survey = survey['survey']
        survey = survey_parser(survey)

        profile = SurveyStandardValidator.profile_from_yaml(args.profile)

        validator = SurveyStandardValidator(profile)
        r = validator.validate(survey.getCurrent())

        print(readable_yaml(r))

register(SurveyValidateStandard)