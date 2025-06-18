import os
from datetime import datetime
from cliff.command import Command
from . import register
from ifncli.utils import read_yaml, readable_yaml, read_json, write_content, Output
from ifncli.managers.export import ExportProfile
try:
    from ifncli.managers.export.db import DbExporter, ExportDatabase 
    from ifncli.managers.export.db.describe import describe_database, DatabaseDescriber
    from ifncli.managers.export.db.importer import Importer, ImporterProfile, SurveySchema
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
        parser.add_argument("--study", help="Study key", required=True)
        parser.add_argument("--profile", help="Path to yaml export profile")
        parser.add_argument("--db-path", help="Database file path")
        parser.add_argument("--page-size", help="page size", type=int, default=1000)
        parser.add_argument("--start-from", help="restart export from", default=None)
        return parser

    def take_action(self, args):
        client = self.app.get_management_api()

        study_key = args.study
        page_size = args.page_size

        profile = ExportProfile(args.profile)
        exporter = DbExporter(profile, client, study_key, args.db_path, page_size)
        exporter.export_all(None)

class ResponseBulkExporterDb(Command):
    """
        Incremental Export for a set of surveys (each with an export profile)
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
            version = spec.parser_version_selector_str(args.version)
        else:
            version = None

        schema = survey_schema.from_export_db(db, version=version)

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
        parser.add_argument("--survey", help="Survey name", required=True)
        parser.add_argument("--source-db", help="Database file path", required=True)
        parser.add_argument("--target-db", help="Database to import data into", required=False)
        parser.add_argument('--from-time', help="Import data from this time (submitted)", required=False)
        parser.add_argument("--to-time", help="Import data until this time (submited)", required=False)
        parser.add_argument("--version",help="Version selector (default is all)", required=False)
        parser.add_argument("--target-table", help="Table name to import data into in the target database (default is pollster_response_$(survey))", required=False)
        parser.add_argument("--source-table", help="Table name to import data into in the target database (default is responses_$(survey))", required=False)
        parser.add_argument("--profile", help="Yaml file defining the import profile (all parameters can be in it)", required=False)
        parser.add_argument("--only-show", help="Only show the profile configuration use for import and exit (do not import anything)", action="store_true")
        return parser

    def take_action(self, args):

        source_db = ExportDatabase(args.source_db)

        # Export parameters are stored in the export db in metadata table
        export_meta = source_db.get_meta()

        profile_overides = {
            'source_table': args.source_table,
            'from_time':args.from_time,
            'to_time': args.to_time,
            'target_table': args.target_table,
            'target_db': args.target_db,
            'survey': args.survey,
        }

        profile = ImporterProfile(source_db)
        profile.load(args.profile, profile_overides)
        profile.build()

        if args.only_show:
            d = profile.to_readable()
            print(readable_yaml(d))
            return

        importer = Importer(profile, debug=False)
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
        if 'submitted' in column:
            return datetime.fromtimestamp(value)
        return value

class ResponseDbDescribe(Command):

    name = "response:db:describe"

    def get_parser(self, prog_name):
        parser = super(ResponseDbDescribe, self).get_parser(prog_name)
        parser.add_argument("--db", help="Database file", required=True)
        return parser

    def take_action(self, args):
        data = describe_database(args.db, describer=ResponseDbDescribder(), debug=True)
        data.show()

class ResponseTestRenamer(Command):
    name = "response:db:renamer"

    def get_parser(self, prog_name):
        parser = super(ResponseTestRenamer, self).get_parser(prog_name)
        parser.add_argument("--file", help="json file where columns names are stored", required=False)
        parser.add_argument("--verbose", help="json file where columns names are stored", action="store_true", required=False)
        return parser

    def take_action(self, args):
        columns = read_json(args.file)
        processor = processor.DefaultRenamingProcessor('|')

        if args.verbose:
            debug = lambda msg: print(" ", msg)
        else:
            debug = None
        
        renamed = processor.apply_to_list(columns, debug=debug)
        for index, col in enumerate(columns):
            print("'{}' => '{}'".format(col, renamed[index]))

class ResponseDbUnavailable(Command):
    """
        Reason for response:db commands not available (missing module)
    """

    name = "response:db:unavailable"

    def take_action(self, args):
        print("response:db actions are not available because of missing python packages")
        print(missing_module)

if export_module_available:
    register(ResponseExportDb)
    register(ResponseBulkExporterDb)
    register(ResponseExportSchema)
    register(ResponseDbImport)
    register(ResponseTestRenamer)
    register(ResponseDbDescribe)
else:
    register(ResponseDbUnavailable)
