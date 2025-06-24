import os
from datetime import datetime
from cliff.command import Command
from . import register
from ifncli.utils import read_yaml, readable_yaml, read_json, write_content, Output, from_iso_time
from ifncli.managers.export import ExportProfile
try:
    from ifncli.managers.export.db import DbExporter, ExportDatabase, ExportSqlite 
    from ifncli.managers.export.db.compress import CompressEvaluator
    from ifncli.managers.export.db.describe import describe_database, DatabaseDescriber
    from ifncli.managers.export.db.importer import Importer, ImporterProfile, SurveySchema, VersionSelectorParser, fake, PrintWriter
    from influenzanet.surveys.preview.schema import ReadableSchema
    export_module_available = True
    missing_module = None
except ModuleNotFoundError as e:
    missing_module = e.msg
    export_module_available = False

class ResponseExportDb(Command):

    name = "response:db:export"

    def get_parser(self, prog_name):
        parser = super(ResponseExportDb, self).get_parser(prog_name)
        parser.add_argument("--profile", help="Path to yaml export profile")
        parser.add_argument("--db-path", help="Database file path", required=True)
        
        # Profile overrides
        parser.add_argument("--study", "--study-key", help="Study key (optional can be in profile)", required=False)
        parser.add_argument("--survey", help="Only apply this command to this survey (for multiple survey profile)")
        
        # Options
        parser.add_argument("--page-size", help="page size", type=int, default=1000)
        
        g = parser.add_mutually_exclusive_group()   
        g.add_argument("--start-from", help="restart export from this time (iso time string)", default=None)
        g.add_argument("--restart", help="Force restart of plan", action="store_true")
        return parser

    def take_action(self, args):
        client = self.app.get_management_api()

        page_size = args.page_size

        profile = ExportProfile(args.profile, {'short_keys': True})

        study_key = args.study
        if study_key is not None:
            if profile.study_key != '':
                print("Overriding profile study_key `{}` to `{}`".format(profile.study_key, study_key))
        else:
            study_key = profile.study_key
        
        if study_key is None or study_key == '':
            raise ValueError("study_key must be provided in profile or in command line with '--study' parameter")

        if args.survey is not None:
            surveys = [args.survey]
        else:
            surveys = profile.survey_list()

        start_time = None
        if args.start_from is not None:
            try:
                start_time = from_iso_time(args.start_from)
            except Exception as e:
                raise ValueError("Unable to parse '--start-from'") from e
        
        restart = args.restart
            
        if not profile.short_keys:
            print("Profile short_keys set to False is ignored")
            profile.short_keys = True # Avoid warning on each download loop

        for survey in surveys:
            profile.configure_for_survey(survey)
            exporter = DbExporter(profile, client, study_key, args.db_path, page_size)
            if restart:
                start_time = profile.start_time
            exporter.export_all(start_time)

class ResponseBulkExporterDb(Command):
    """
        Incremental Export for a set of surveys (each with an export profile)
        
        This is only useful if you have different profiles for each survey. If all surveys shared the same profile export parameters
        you can use `surveys` directly in profile and set a list of surveys to export in one pass.
    """

    name = "response:db:export-plan"

    def get_parser(self, prog_name):
        parser = super(ResponseBulkExporterDb, self).get_parser(prog_name)
        parser.add_argument("--db-path", help="Database file path")
        parser.add_argument("--plan", type=str, required=True, help="yaml files with export plan")
        parser.add_argument("--page-size", help="page size", type=int, default=1000)
        parser.add_argument("--restart", help="Force restart of plan", action="store_true")
        return parser
        
    def take_action(self, args):
        db_path = args.db_path
        
        plan = read_yaml(args.plan)

        study_key = plan['study']

        plan_folder = os.path.dirname(os.path.abspath(args.plan))
        
        client = self.app.get_management_api()
        
        for profile_name in plan['profiles']:
            fp = plan_folder + '/' + profile_name
            print("* Processing %s" % (fp))
            profile = ExportProfile(fp)
            if profile.study_key != '' and profile.study_key != study_key:
                print("Overriding profile study_key `{}` to `{}`".format(profile.study_key, study_key))
            exporter = DbExporter(profile, client, study_key, db_path, args.page_size)
            start_time = None
            if args.restart:
               start_time = profile.start_time 
            exporter.export_all(start_time)

class ResponseExportSchema(Command):
    """
        Build and export survey schema from the survey_info in an export database
    """
    name = "response:db:schema"

    def get_parser(self, prog_name):
        parser = super(ResponseExportSchema, self).get_parser(prog_name)
        parser.add_argument("--survey", help="Survey name", required=True)
        parser.add_argument("--db-path", help="Export Database file path", required=True)
        parser.add_argument("--version", help="Version selector", required=False)
        parser.add_argument("--output", help="Output file (yaml)", required=False)
        parser.add_argument("--input", help="Previous schema to update", required=False)
        parser.add_argument("--details", help="Export schema details", required=False, action="store_true")
        parser.add_argument("--force", help="Force update even if they are errors (manual editing will be required)", action="store_true", required=False)
        return parser

    def take_action(self, args):
        
        db = ExportDatabase(args.db_path)

        survey_schema = SurveySchema(args.survey)

        if args.version:
            parser = VersionSelectorParser()
            version = parser.parse(args.version)
        else:
            version = None

        schema = survey_schema.from_export_db(db, version)

        if len(schema.problems) > 0:
            print("Warning: some problems have been found in schema")
            print(readable_yaml(schema.problems))
    
        # Details mode only output the full builder info
        if args.details:
            readdable = ReadableSchema()
            d = readdable.build(schema)
            if(args.output):
                write_content(args.output, d)
            else:
                print(readable_yaml(d))
            return
    
        if args.input is not None:
            previous = read_yaml(args.input)
            problems = previous.get('problems', [])
            columns = previous.get('columns')
            if columns is None:
                raise Exception("`columns` in not in file are you sure its a schema file ?")
        else:
            previous = {}
            columns = {}
            problems = []
        
        for name, col_def in schema.columns.items():
            new_type = col_def.value_type
            if name in columns:
                prev_type = columns[name]
                if new_type != prev_type:
                    problems.append("Conflict type for item '{}' : '{}' previously '{}'".format(name, new_type, prev_type))
            else:
                columns[name]= new_type
        if len(problems) > 0:
            print("Warning: problems in schema, cannot update types for some column")
            for p in problems:
                print(" - ", p)
        previous['columns'] = columns
        if len(problems) > 0:
            previous['problems'] = problems

        write = False
        if len(problems) == 0 or args.force:
            if args.output is not None:
                write = True
        
        d = readable_yaml(previous)
        if write:
            write_content(args.output, d)
        else:
            print(d)
        
class ResponseDbImport(Command):
    """
        Import data into a analysis database with flat table from an exported database
    """

    name = "response:db:import"

    def get_parser(self, prog_name):
        parser = super(ResponseDbImport, self).get_parser(prog_name)
        parser.add_argument("--survey", help="Survey name", required=False)
        parser.add_argument("--source-db", help="Database file path", required=False)
        parser.add_argument("--target-db", help="Database to import data into", required=False)
        parser.add_argument('--from-time', help="Import data from this time (submitted)", required=False)
        parser.add_argument("--to-time", help="Import data until this time (submited)", required=False)
        parser.add_argument("--version",help="Version selector (default is all)", required=False)
        parser.add_argument("--target-table", help="Table name to import data into in the target database (default is pollster_response_$(survey))", required=False)
        parser.add_argument("--source-table", help="Table name to import data into in the target database (default is responses_$(survey))", required=False)
        parser.add_argument("--profile", help="Yaml file defining the import profile (all parameters can be in it)", required=False)
        parser.add_argument("--offset", help="Starting offset", type=int, default=0)
        parser.add_argument("--batch-size", help="Number of rows to load at once", type=int, default=5000)
        parser.add_argument('--debugger', help="Debugger list of properties to debug")
        parser.add_argument("--only-show", help="Only show the profile configuration use for import and exit (do not import anything)", action="store_true")
        parser.add_argument("--dry-run", help="Only prepare data dont run the update on target db", action="store_true")
        return parser

    def take_action(self, parsed_args):
        args = parsed_args
        profile_overides = {
            'source_db': args.source_db,
            'source_table': args.source_table,
            'target_table': args.target_table,
            'target_db': args.target_db,
            'from_time':args.from_time,
            'to_time': args.to_time,
            'survey': args.survey,
            'starting_offset': args.offset,
            'batch_size': args.batch_size,
            'debugger': args.debugger,
            'dry_run': args.dry_run,
        }

        profile = ImporterProfile(args.profile, profile_overides)
        profile.build()

        if args.only_show:
            d = profile.to_readable()
            print(readable_yaml(d))
            return

        importer = Importer(profile)
        importer.run()
       
class ResponseDbDescribder(DatabaseDescriber):
    """
    Describe tables in a export db (works with sqlite and duckdb)
    """
    def query_columns(self, table_name):
        if table_name.startswith('responses_'):
            return ["max(submitted) as max_submitted", 'min(submitted) as min_submitted']
        if table_name.startswith('pollster_results_'):
            return ['max(timestamp) as max_submitted', 'min(timestamp) as min_submitted']
        return []

    def format_column(self, column:str, value):
        if 'submitted' in column and not isinstance(value, datetime):
            return datetime.fromtimestamp(value)
        return value

class ResponseDbDescribe(Command):

    name = "response:db:describe"

    def get_parser(self, prog_name):
        parser = super(ResponseDbDescribe, self).get_parser(prog_name)
        parser.add_argument("--db", help="Database file", required=True)
        return parser

    def take_action(self, parsed_args):
        data = describe_database(parsed_args.db, describer=ResponseDbDescribder(), debug=True)
        data.show(self.app.stdout)

class ResponseTestRenamer(Command):
    """
        Load a profile with a fake db and Run the Rename processors
    """

    name = "response:db:renamer"

    def get_parser(self, prog_name):
        parser = super(ResponseTestRenamer, self).get_parser(prog_name)
        parser.add_argument("--survey", help="Survey name", required=False)
        parser.add_argument("--source-db", help="Database file path", required=False)
        #parser.add_argument("--columns", help="Comma separated list of columns", required=True)
        parser.add_argument("--profile", help="The profile", required=True)
        parser.add_argument("--debugger", help="Debugger", required=False)
        return parser

    def take_action(self, parsed_args):
        args = parsed_args
        
        profile_overides = {
            'source_db': args.source_db,
            'survey': args.survey,
            'debugger': args.debugger,
        }

        if args.source_db is None:
            fake_db = ExportSqlite(':memory:', allow_create=True)
            fake_db.setup_meta('|')
            fake_db.setup_surveyinfo()
        else:
            fake_db = None

        profile = ImporterProfile(args.profile, profile_overides, source_db=fake_db)
        profile.build()
        profile.dry_run = True

        print(profile.to_readable())

        columns = fake.FakeColumnsData(['Q1|0', 'Q2|2|open'], '23-11-1')
        loader = fake.FakeDataLoader(columns.data)

        importer = Importer(profile)
        importer.run(loader, PrintWriter())

class ResponseDbUnavailable(Command):
    """
        Reason for response:db commands not available (missing module)
    """

    name = "response:db:unavailable"

    def take_action(self, args):
        print("response:db actions are not available because of missing python packages")
        print(missing_module)


class ResponseTestCompress(Command):
    """
        Reason for response:db commands not available (missing module)
    """

    name = "response:db:compress"

    def get_parser(self, prog_name):
        parser = super(ResponseTestCompress, self).get_parser(prog_name)
        parser.add_argument("--survey", help="Survey name", required=False)
        parser.add_argument("--source-db", help="Database file path", required=False)
        return parser

    def take_action(self, parsed_args):
        evaluator = CompressEvaluator(parsed_args.source_db)
        evaluator.evaluate(parsed_args.survey)

if export_module_available:
    register(ResponseExportDb)
    register(ResponseBulkExporterDb)
    register(ResponseExportSchema)
    register(ResponseDbImport)
    register(ResponseTestRenamer)
    register(ResponseDbDescribe)
    register(ResponseTestCompress)
else:
    register(ResponseDbUnavailable)
