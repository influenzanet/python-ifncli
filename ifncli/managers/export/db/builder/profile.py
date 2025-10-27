
from ..database import ExportDatabase
from ifncli.utils.io import read_yaml
from datetime import datetime
from typing import Optional
from .schema import SurveySchema
from .processor import BasePreprocessor, SchemaCastingProcessor, DefaultRenamingProcessor, ProcessorParserSpec, PROC_TYPE_CASTING, PROC_TYPE_RENAME
from .version_selector import VersionSelectorRule, VersionSelectorParser, parse_version, SurveyVersion
from .trace import DictWithOrigin

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
    """
        ProcessorSpec embeds a Processor with an eventual version criteria
    """

    def __init__(self, processor: BasePreprocessor, version: Optional[VersionSelectorRule]):
        self.processor = processor
        self.version = version

    def supports(self, version:SurveyVersion):
        if self.version is None:
            return True
        return self.version.is_version(version)
    
    def __str__(self):
        if self.version is None:
            return str(self.processor)
        return "{} when version {}".format(str(self.processor), str(self.version))

    def to_readable(self):
        if self.version is None:
            return self.processor.to_readable()
        return {
            'version': str(self.version),
            'processor': self.processor.to_readable()
        }
class ProcessorEntry:
    """
        Intermediate class used to order processor by position type
    """

    def __init__(self, proc: ProcessorSpec, position: str):
        self.proc = proc
        self.position = position

POSITION_BEFORE_CASTING = 'before_casting'
POSITION_AFTER_CASTING = 'after_casting'
POSITION_END = 'end'

PROC_DEFAULT_CASTING = 'default_casting'
PROC_DEFAULT_RENAMING = 'default_renaming'

class Debugger:
    """
        Debugger contains flags to known which part to debug (print)
    """
    
    PROPERTIES = [
        'json', # Print json parsed
        'query', # Import query
        'query_source', # Source query
        'version', # Version loop block
        'processors' # Processors run in version block
    ]

    def __init__(self) -> None:
        self.flags = dict[str, bool]([ (name, False) for name in Debugger.PROPERTIES])

    def parse(self, spec):
        tokens = []
        if isinstance(spec, str):
            tokens = spec.split(',')
        if isinstance(spec, list):
            for s in spec:
                if not isinstance(s, str):
                    raise ValueError("Debugger list item must be a string, cannot handle nested list")
                tokens.extend(s.split(','))
        activate = set()
        for token in tokens:
            name = token.strip()
            if name == 'all':
                activate.update(Debugger.PROPERTIES)
            else:
                if not name in Debugger.PROPERTIES:
                    raise ValueError("Unknown debugger flag {}".format(name))
                activate.add(name)
        for name in activate:
            self.flags[name] = True

    def has(self, name:str):
        if not name in self.flags:
            print("Warning: Unknown debugger flag {}".format(name))
        return self.flags.get(name, False)

class Conf(DictWithOrigin):
    """
        Helper class to get configuration values from
        It handles origin of values (using DictWithOrigin) to provides better error message (indicater where the value comes from)
    """
    def get_val_from(self, name:str):
        value = self.get(name)
        origin = self.origin(name)
        return value, origin
    
    def value_error(self, name, expecting, value):
        origin = self.origin(name)
        value = str(value)
        return ValueError(f"Unable to parse profile param '{name}' from {origin} expecting {expecting} got '{value}'")
    
    def get_val_str(self, name:str):
        v = self.get(name)
        if v is not None and not isinstance(v, str):
            raise self.value_error(name, 'string', v)
        return v
    
    def get_val_bool(self, name, default:bool):
        v = self.get(name)
        if v is None:
            return default
        try:
            return bool(v)
        except:
            raise self.value_error(name, 'boolean', v)
    
    def get_val_int(self, name, default:int):
        v = self.get(name)
        if v is None:
            return default
        try:
            return int(v)
        except:
            raise self.value_error(name, 'integer', v)
        
    def get_val_time(self, name):
        v = self.get(name)
        if v is not None:
            try:
                return parse_iso_time(v)
            except:
                raise self.value_error(name, 'iso time', v)
        return v

class BuilderProfile:
    """
        Builder profile describes the parameters to build an analysis database (with flat tables) from the download database (raw data)
    """

    @staticmethod
    def load_from_file(file, overrides:dict[str, str]={}, overrides_origin='overrides'):
        profile = read_yaml(file)
        p = DictWithOrigin(profile, values_origin=file)
        if len(overrides) > 0:
            p.merge_from(overrides, origin=overrides_origin, allow_none=False)
        return p

    def __init__(self, profile: Optional[DictWithOrigin]=None, source_db: Optional[ExportDatabase]=None):
        """
            Load profile parameters if file is provided, possibly overriden with extra values (from command line arguments)
        """
        self.versions: Optional[VersionSelectorRule] = None
        self.processors: list[ProcessorSpec] = []
        self.conf = {} # The loaded profile configuration 
        self.survey_schema: Optional[SurveySchema] = None
        self.debugger = Debugger()
        
        if profile is None:
            profile = {}

        conf = Conf(profile)

        self.from_time = conf.get_val_time('from_time')
        self.to_time = conf.get_val_time('to_time')
        
        vv = conf.get("versions")
        if vv is not None:
            self.versions = parse_version_selector(vv)

        survey = conf.get_val_str("survey")
        if survey is None:
            raise ValueError("survey is required")
        
        self.survey = survey

        self.batch_size = conf.get_val_int("batch_size", default=5000)
        self.starting_offset = conf.get_val_int("starting_offset", default=0)
        self.dry_run = conf.get_val_bool("dry_run", default=False)
        debugger_spec = conf.get("debugger")

        self.debugger.parse(debugger_spec)

        if source_db is None:
            source_db_path = conf.get_val_str("source_db")
            if source_db_path is None:
                raise ValueError("`source_db` (path to source db) must be provided")
            self.source_db = ExportDatabase(source_db_path)
        else:
            self.source_db = source_db

        target_db = conf.get_val_str("target_db")
        if target_db is None:
            raise ValueError("`target_db` must be provided")

        self.target_db = target_db
        self.conf = profile

        source_table = conf.get_val_str("source_table")
        target_table = conf.get_val_str("target_table")
        
        if target_table is None:
            self.target_table = "pollster_results_{}".format(self.survey)
        else:
            self.target_table = target_table

        if source_table is None:
            self.source_table = self.source_db.response_table(self.survey)
        else:
            self.source_table = source_table

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
        self.survey_schema = SurveySchema(self.survey) # type: ignore
        if infer_schema:
            schema = self.survey_schema.from_export_db(self.source_db, self.versions)
            if len(schema.problems) > 0:
                print("Problem found when building the schema ")

        self.survey_schema.override(defaultSchemaOverrides)
        
        if schema_overrides is not None:
            self.survey_schema.override(schema_overrides)

    def build_processors(self):
        if self.survey_schema is None:
            raise ValueError("Survey schema is not available, did you called build_schema() ?")

        meta = self.source_db.get_meta()
        proc_def = self.conf.get('processors')

        # Processor add default : append default processors after custom ones
        # If False, you must define all processors sequence by yourself
        add_defaults = self.conf.get('processors_defaults', True)

        defaults = {
            PROC_DEFAULT_CASTING:SchemaCastingProcessor(self.survey_schema),
            PROC_DEFAULT_RENAMING: DefaultRenamingProcessor(meta.key_separator),
        }

        if proc_def is None:
            proc_def = []

        if add_defaults:
            proc_def.extend([
                PROC_DEFAULT_CASTING,
                PROC_DEFAULT_RENAMING
            ])

        self.processors = self.parse_processors(proc_def, defaults, meta.key_separator)
    
    def parse_processors(self, proc_defs, defaults, key_separator: str):
        if not isinstance(proc_defs, list):
            raise ValueError("Processor definition must be a list")   
        
        entries: list[ProcessorEntry] = []
        
        # Position of the processor in the transformation process
        # Some processors must be run before the default ones
        positions = [POSITION_BEFORE_CASTING, PROC_DEFAULT_CASTING, POSITION_AFTER_CASTING, PROC_DEFAULT_RENAMING, POSITION_END]

        parser = ProcessorParserSpec(key_separator)
        for proc_def in proc_defs:
            proc = None
            position = POSITION_END
            if isinstance(proc_def, str):
                proc = defaults.get(proc_def)
                if proc is None:
                    raise ValueError("Unknown default processor named '{}'".format(proc_def))
                position = proc_def
            elif isinstance(proc_def, dict):
                proc = parser.parse(proc_def)
                versionSelector = None
                if "version" in proc_def:
                    versionSelector = parse_version_selector(proc_def['version'])
                if "position" in proc_def:
                    position = proc_def['position']
                else:
                    position = POSITION_AFTER_CASTING
                proc = ProcessorSpec(proc, versionSelector)
            if proc is not None:
                if position not in positions:
                    raise ValueError("Position '{}' is not registered".format(position))
                entries.append(ProcessorEntry(proc, position))

        # Now reorder processors order using position
        processors = []
        for position in positions:
            for entry in entries:
                if entry.position == position:
                    processors.append(entry.proc)
        return processors
    
    def select_processors(self, version:str):
        """
            Return list of processors for a given version
        """
        pp = []
        v = parse_version(version)
        for proc_spec in self.processors:
            if isinstance(proc_spec, ProcessorSpec):
                if proc_spec.supports(v):
                    pp.append(proc_spec.processor)
            else:
                pp.append(proc_spec)
        return pp
                
    def to_readable(self):
        schema = None
        if self.survey_schema is not None:
            schema = self.survey_schema.to_readable()
        d = {
            'source_table': self.source_table,
            'target_table': self.target_table,
            'target_db': self.target_db,
            'from_time': self.from_time,
            'to_time': self.to_time,
            'versions': str(self.versions),
            'processors': [p.to_readable() for p in self.processors],
            'survey': self.survey,
            'schema': schema,
            'debugger': self.debugger.flags,
            'batch_size': self.batch_size,
            'starting_offset': self.starting_offset,
        }
        return d

