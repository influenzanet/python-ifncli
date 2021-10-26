from datetime import datetime
import json
import sys
from ifncli.surveys import create_context
from ifncli.surveys.influenzanet.expression import library_path, schema_path
from ifncli.surveys.readable import as_readable
from ifncli.surveys.influenzanet import survey_parser
from ifncli.surveys.tools.validator import SurveyStandardValidator
from ifncli.surveys.tools.checker import SurveyChecker

from cliff.command import Command

from . import register

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

        parser.add_argument(
            "--all",help="Returns all problems, including known", required=False, action="store_true"
        )

        parser.add_argument("--output", help="path of file to output results", required=False)
        parser.add_argument("--format", help="Output format available, default is 'human' (human readable yaml-like)", required=False, action="store", default='human', choices=['human','json','yaml'])
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
        
        if not args.all:
            r = validator.filter_known(r)

        ctx = create_context()

        if args.output:
            need_close = True
            out = open(args.output, 'w')
        else:
            need_close = False
            out = sys.stdout

        out_format = args.format

        ss = as_readable(r, ctx)
        if out_format in ["human", "yaml"]:
            out.write(readable_yaml(ss))
        else:
            out.write(json.dumps(ss))

        if need_close:
            out.close()


class SurveyCheckCommand(Command):
    """
        Check survey consistency
    """

    name = 'survey:check'

    def get_parser(self, prog_name):
        parser = super(SurveyCheckCommand, self).get_parser(prog_name)
        parser.add_argument(
            "--survey", help="path to the survey json", required=True,
        )
        
        parser.add_argument("--output", help="path of file to output results", required=False)
        parser.add_argument("--format", help="Output format available, default is 'human' (human readable yaml-like)", required=False, action="store", default='human', choices=['human','json','yaml'])
        return parser

    def take_action(self, args):
        survey = read_json(args.survey)

        if "studyKey" in survey:
            # A study entry
            survey = survey['survey']
        survey = survey_parser(survey)

        checker = SurveyChecker()
        
        r = checker.check(survey)
        
        ctx = create_context()

        if args.output:
            need_close = True
            out = open(args.output, 'w')
        else:
            need_close = False
            out = sys.stdout

        out_format = args.format

        ss = as_readable(r, ctx)
        if out_format in ["human", "yaml"]:
            out.write(readable_yaml(ss))
        else:
            out.write(json.dumps(ss))

        if need_close:
            out.close()

class ValidateExpressionLibrary(Command):
    """
        Validate survey description file agaisnt json schema 
    """

    name = 'survey:validate-exp'

    def take_action(self, args):
        
        json = read_json(library_path())
        schema = read_json(schema_path())
        
        import jsonschema
        
        jsonschema.validate(json, schema)
        print("Json schema is valid")


register(ValidateExpressionLibrary)
register(SurveyValidateStandard)
register(SurveyCheckCommand)