
from ..database import ExportDatabase
from ifncli.utils.io import read_yaml
from datetime import datetime
from typing import Optional
from .schema import SurveySchema
from .processor import BasePreprocessor, SchemaCastingProcessor, DefaultRenamingProcessor, parse_processor_def
from .version_selector import VersionSelectorRule, VersionSelectorParser, parse_version

def parse_iso_time(d):
    time = datetime.fromisoformat(d)
    return int(time.timestamp())

def parse_version_selector(d):
    parser = VersionSelectorParser()
    return parser.parse(d)

defaultSchemaOverrides = {
    'opened': 'date',
    'submitted': 'date'
}


class ProcessorSpec:

    def __init__(self, processor: BasePreprocessor, version: VersionSelectorRule):
        self.processor = processor
        self.version = version

    def supports(self, version:str):
        if self.version is None:
            return True
        v = parse_version(version)
        return self.version.is_version(v)
    
    def __str__(self):
        if self.version is None:
            return str(self.processor)
        return "{} when version {}".format(self.processor, self.version)

class ImporterProfile:
    """
        Import profile describe the import parameters to import from the download database (raw data) to an analysis database (with flag table)
    """

    def __init__(self, source_db:ExportDatabase):
        self.source_db = source_db
        self.source_table = None
        self.target_table = None
        self.from_time = None
        self.to_time = None
        self.batch_size = 1000
        self.versions: Optional[VersionSelectorRule] = None
        self.processors: list[ProcessorSpec] = []
        self.survey:Optional[str] = None
        self.conf = {} # The loaded profile configuration 
        self.survey_schema: Optional[SurveySchema] = None
       
    def load(self, profile_file=None, overrides:dict[str, str]={}):
        """
            Load profile parameters if file is provided, possibly overriden with extra values (from command line arguments)
        """
        if profile_file is not None:
            profile = read_yaml(profile_file)
        else:
            profile = {}

        def get_val(name:str, parser=None, required=False, default=None):
            value = overrides.get(name)
            origin = 'override'
            if value is None:
                value = profile.get(name)
                origin = 'profile' 
            if value is not None and parser is not None:
                try:
                    value = parser(value)
                except Exception as e:
                    if origin == 'profile':
                        o = 'profile file `{}`'.format(profile_file)
                    else:
                        o = 'overrides values (command line argument ?)'
                    raise ValueError("Unable to parse value {} in {} : {}".format(name, o, e))
            if value is None and required:
                raise ValueError("A value is required for `{}` and none provided in profile nor overrides")
            if value is None and default is not None:
                value = default
            return value

        self.from_time = get_val('from_time', parse_iso_time)
        self.to_time = get_val('to_time', parse_iso_time)
        self.source_table = get_val("source_table")
        self.target_table = get_val("target_table")
        self.target_db = get_val("target_db")
        self.versions = get_val("versions", parse_version_selector)
        self.survey = get_val("survey", required=True)
        self.batch_size = get_val("batch_size", default=5000)
        self.conf = profile

        if self.target_table is None:
            self.target_table = "pollster_results_{}".format(self.survey)

        if self.source_table is None:
            self.source_table = self.source_db.response_table(self.survey)

    def build(self):
        self.build_schema()
        self.build_processors()

    def build_schema(self, allow_problem=False):
        schema_overrides = self.conf.get('schema')
        infer_schema = self.conf.get('infer_schema', True)
        if infer_schema is not None:
            try:
                infer_schema = bool(infer_schema)
            except:
                raise ValueError("`infer_schema` in profile must be a boolean value")
        self.survey_schema = SurveySchema(self.survey)
        if infer_schema:
            schema = self.survey_schema.from_export_db(self.source_db, self.versions)
            if len(schema.problems) > 0:
                print("Problem found when building the schema ")

        self.survey_schema.override(defaultSchemaOverrides)
        
        if schema_overrides is not None:
            self.survey_schema.override(self.schema_overrides)

    def build_processors(self):
        meta = self.source_db.get_meta()
        proc_def = self.conf.get('processors')

        defaults = {
            'default_casting':SchemaCastingProcessor(self.survey_schema),
            'default_renaming': DefaultRenamingProcessor(meta.key_separator),
        }

        if proc_def is None:
            proc_def = [
                'default_casting',
                'default_renaming'
            ]
        self.processors = self.parse_processors(proc_def, defaults)
    
    def parse_processors(self, proc_defs, defaults):
        if not isinstance(proc_defs, list):
            raise ValueError("Processor definition must be a list")   
        processors = []
        for proc_def in proc_defs:
            if isinstance(proc_def, str):
                proc = defaults.get(proc_def)
                if proc is None:
                    raise ValueError("Unknown default processor named '{}'".format(proc_def))
            elif isinstance(proc_def, dict):
                proc = proc.parse_processor_def(proc_def)
                versionSelector = None
                if "version" in proc_def:
                    versionSelector = parse_version_selector(proc_def['version'])
                proc = ProcessorSpec(proc, versionSelector)
            processors.append(proc)
        return processors
    
    def select_processors(self, version:str):
        """
            Return list of processors for a given version
        """
        pp = []
        for proc_spec in self.processors:
            if isinstance(proc_spec, ProcessorSpec):
                if proc_spec.supports(version):
                    pp.append(proc_spec.processor)
            else:
                pp.append(proc_spec)
        return pp
                
    def to_readable(self):
        d = {
            'source_table': self.source_table,
            'target_table': self.target_table,
            'target_db': self.target_db,
            'from_time': self.from_time,
            'to_time': self.to_time,
            'versions': str(self.versions),
            'processors': [str(x) for x in self.processors],
            'survey': self.survey,
            'schema': self.survey_schema,
        }
        return d

