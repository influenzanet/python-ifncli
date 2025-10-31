import pandas
import re
import json
from typing import Optional

from ..schema import SurveySchema
from .columns import BaseColumnSelector, ColumnSelector

PROC_TYPE_RENAME = 'rename'
PROC_TYPE_CASTING = 'casting'
PROC_TYPE_DEFAULT_RENAMING = 'default_renaming'
PROC_TYPE_DEFAULT_CASTING = 'default_casting'


def dict_to_readable(d: dict, glue:str):
    """ readable simple representation of dictionary in a single line"""
    s = []
    for k, v in d.items():
        s.append("`{}`{}`{}`".format(k, glue, v))
    return ', '.join(s)

def to_str(l:list):
    for x in l:
        yield str(x)

class BasePreprocessor:
    """
        A Processor apply a transformation to a dataframe
    """
    def apply(self, rows: pandas.DataFrame, debug: bool = False):
        return rows
    
    def processor_type(self)->str:
        return 'none'

    def to_readable(self):
        return 'Unknown'

class BaseRenameRule:

    def apply(self, column:str)->str:
        raise NotImplementedError()

    def to_readable(self):
        """ readable simple representation (simple yaml to be human readed)"""
        return self.__str__()

class RemovePrefixRule(BaseRenameRule):
    """
        Remove prefix of question (group keys), keeping only the last item key
    """
    def __init__(self, separator):
        self.separator = separator
    
    def apply(self, column:str)->str:
        q = column.split(self.separator, 1)
        if len(q) == 2:
            question = q[0]
            response = q[1]
        else:
            question = q[0]
            response = None
        question = question.split('.')
        question = question[ -1:]
        question = question[0]
        if response is None:
            return question
        return question + self.separator + response
        
    def __str__(self):
        return 'remove_prefix'
    
    def to_readable(self):
        """ readable simple representation (simple yaml to be human readed)"""
        return self.__str__()

class RenameRegexpRule(BaseRenameRule):
    """
        Rename column using regex and replacement
    """

    def __init__(self, separator:str, pattern:str, replace:str):
        """

        """
        self.separator = separator
        sep = re.escape(self.separator)
        p = pattern.replace('<$>', sep)
        try:
            self.pattern = re.compile(p, re.IGNORECASE)
        except ValueError as e:
            raise Exception("Error compiling regex `{}`".format(p))
        r = replace.replace('<$>', self.separator)
        self.replace = r

    def apply(self, column):
        return re.sub(self.pattern, self.replace, column)
        #return column
    
    def __str__(self):
        return '`{}`:`{}`'.format(self.pattern, self.replace)

    def to_readable(self):
        """ readable simple representation (simple yaml to be human readed)"""
        f = ''
        if self.pattern.flags & re.IGNORECASE:
            f += 'i'
        if self.pattern.flags & re.MULTILINE:
            f += 'm'
        if self.pattern.flags & re.DOTALL:
            f += 's'
        return "regexp:/{}/{} => '{}'".format(self.pattern.pattern, f, self.replace)

class RenameFixedColumnRule(BaseRenameRule):
    """
        Rename columns using a simple dictionnary
    """
    def __init__(self, to_rename:dict):
        self.to_rename = to_rename

    def apply(self, column):
        return self.to_rename.get(column, column)
        
    def __str__(self):
        return 'fixed `{}`'.format(self.to_rename)

    def to_readable(self):
        """ readable simple representation (simple yaml to be human readed)"""
        return {'fixed': self.to_rename}


DefaultExcludedColumns = ['submitted', 'language', 'participantID','engineVersion', 'opened', 'ID']

DefaultRenameColumns = {
    'participantID': 'global_id',
    'submitted':'timestamp',
    'ID':'id',
}

class DuplicateColumnError(Exception):
    pass

class BaseRenamingProcessor(BasePreprocessor):
    """
        Base processor to rename columns based on list of renaming rules (regex, fixed, ...)
    """
    def __init__(self, excluded:list[str]=[]):
        self.rules : list[BaseRenameRule] = []
        self.excluded = excluded

    def apply_to_list(self, columns: list[str], debug=None):
        """
            Apply renaming to a list of columns
        """
        renamed = {}
        targets = {}
        for column in columns:
            if column in self.excluded:
                continue
            value = column
            for rule in self.rules:
                r = rule.apply(value)
                if debug is not None:
                    debug("   - {}: '{}' => '{}'".format(rule, value, r))
                value = r
            if value in targets:
                targets[value].append(column)
            else:
                targets[value] = [column]
            renamed[column] = value
        error = False
        for target, from_names in targets.items():
            if len(from_names) > 1:
                print("Duplicate column {} renamed from {}".format(target, from_names))
                error = True
        if error:
            raise DuplicateColumnError("Duplicate column name after renaming")
        return renamed

    def apply(self, rows:  pandas.DataFrame, debug: bool = False):
        columns = rows.columns.to_list()
        renamed = self.apply_to_list(columns)
        rows.rename(columns=renamed, inplace=True)
        return rows

    def processor_type(self)->str:
        return PROC_TYPE_RENAME

    def to_readable(self):
        return {
            'name': 'rename',
            'rules': [ rule.to_readable() for rule in self.rules],
            'excluded': "`{}`".format('`, `'.join(self.excluded)),
        }

    def __str__(self):
        return "<Rename: rules:{}, excluded:{}>".format(",".join(to_str(self.rules)), self.excluded)

class DefaultRenamingProcessor(BaseRenamingProcessor):

    def __init__(self, separator, excluded=DefaultExcludedColumns, defaultColumns=DefaultRenameColumns):

        super(DefaultRenamingProcessor, self).__init__(excluded)

        # PLaceholder <$> stands for the question/response separator (|)
        rules = [
            (r'<$>mat\.row(\d+)\.col(\d+)', r"<$>multi_row\1_col\2"), # Legacy column naming to be compatible with data of previous platform
            (r"<$>likert_(\d+)", r"<$>lk_\1"),
            ("<$>", "_")
        ]
        self.rules.append( RemovePrefixRule(separator) )
        for r in rules:
            self.rules.append(RenameRegexpRule(separator, r[0], r[1]))
        self.defaultColumns = defaultColumns

    def apply(self, rows:  pandas.DataFrame, debug: bool = False):
        rows = super(DefaultRenamingProcessor, self).apply(rows)
        rows.rename(columns=self.defaultColumns, inplace=True, errors='ignore')
        return rows

    def processor_type(self)->str:
        return PROC_TYPE_DEFAULT_RENAMING

    def __str__(self):
        return "<DefaultRename:{}>".format(",".join(to_str(self.rules)))

    def to_readable(self):
        r = super(DefaultRenamingProcessor, self).to_readable()
        r['name'] = PROC_TYPE_DEFAULT_RENAMING
        r['defaults']= dict_to_readable(self.defaultColumns,'=>')
        return r


class ToBooleanRule:
    """
        Transform colum to boolean
    """

    def __init__(self, columns: list[str]):
        self.columns = columns

    def apply(self, rows: pandas.DataFrame):
        booleans = {'0': False, '1':True, 'true': True, 'false': False}
        to_bool = lambda x: str(x).lower() if not (pandas.isna(x) or x == '') else None
        for column in self.columns:
            if  column not in rows:
                continue
            if rows[column].dtype != 'boolean':
                with pandas.option_context("future.no_silent_downcasting", True):
                    rows[column] = rows[column].map(to_bool).replace(booleans).astype('boolean')
                #rows[column] = rows[column].astype('boolean')
        return rows

    def __str__(self):
        return "<boolean:{}>".format(", ".join(self.columns))
    
class ToDatetimeRule:
    """
        Transform colum to date time from
    """

    def __init__(self, columns: list[str]):
        self.columns = columns

    def apply(self, rows: pandas.DataFrame):
        for column in self.columns:
            if column not in rows:
                continue
            rows[column] = pandas.to_datetime(rows[column].astype('int64', errors='ignore'), unit='s', errors='coerce')
        return rows

    def __str__(self):
        return "<date:{}>".format(", ".join(self.columns))
 

def extract_items_keys(data):
        d = []
        if 'items' in data:
            for item in data['items']:
                d.append(item['key'])
        return d

class UnJsonRule:
    def __init__(self, columns: list[str]):
        self.columns = columns

    def apply(self, rows: pandas.DataFrame):

        def update_row(value):
            if pandas.isna(value):
                return value
            if value == "":
                return value
            if isinstance(value, dict):
                v = value
            else: 
                try:
                    v = json.loads(value)
                except Exception as e:
                    print("Unable to parse json data :{}".format(e))
            v = extract_items_keys(v)
            if len(v) > 0:
                v = ','.join(v)
            return v
        
        for column in self.columns:
            if column not in rows.columns:
                continue
            rows[column] = rows[column].apply(update_row)
        return rows

    def __str__(self):
        return "<unjson:{}>".format(', '.join(self.columns))

class SchemaCastingProcessor(BasePreprocessor):

    def __init__(self, schema: SurveySchema):
        super().__init__()  
        self.schema = schema
        self.boolean_rule: Optional[ToBooleanRule] = None
        self.unjson_rule: Optional[UnJsonRule] = None
        self.date_rule: Optional[ToDatetimeRule] = None
        self.build()

    def build(self):
        cols = {}
        for name, col_type in self.schema.column_types.items():
            if col_type not in cols:
                cols[col_type] = []
            cols[col_type].append(name)
        
        def create_rule(name, clz):
            columns = cols.get(name)
            if columns is not None and len(columns) > 0:
                return clz(columns)
            return None
        
        self.boolean_rule = create_rule('bool', ToBooleanRule)
        self.unjson_rule = create_rule('json', UnJsonRule)
        self.date_rule = create_rule('date', ToDatetimeRule)

    def apply(self, rows: pandas.DataFrame, debug: bool = False):
        if self.boolean_rule is not None:
            self.boolean_rule.apply(rows)
        if self.unjson_rule is not None:
            self.unjson_rule.apply(rows)
        if self.date_rule is not None:
            self.date_rule.apply(rows)
        return rows

    def processor_type(self)->str:
        return 'default_casting'

    def __str__(self):
        return "SchemaCasting<{},{},{}>".format(self.boolean_rule, self.unjson_rule, self.date_rule)
    
    def to_readable(self):
        return {
            'name': PROC_TYPE_DEFAULT_CASTING,
            'rules': [
                str(self.boolean_rule),
                str(self.date_rule),
                str(self.unjson_rule),
            ]
        }

class RuleBasedProcessor(BasePreprocessor):
    def __init__(self, rule_class, columns: ColumnSelector):
        self.columns = columns
        self.rule_class = rule_class

    def apply(self, rows: pandas.DataFrame, debug: bool = False):
        columns = rows.columns.to_list()
        columns = self.columns.select(columns)
        rule = self.rule_class(columns)
        return rule.apply(rows)
    
    def processor_type(self)->str:
        return PROC_TYPE_CASTING
    
    def to_readable(self):
        return {
            'name': self.rule_class,
            'columns': self.columns,
        }

class RenamingProcessor(BaseRenamingProcessor):
    
    def __init__(self, rules: list[BaseRenameRule], excluded: list[str]):
        super(RenamingProcessor, self).__init__(excluded)
        self.rules = rules
    
    def processor_type(self)->str:
        return PROC_TYPE_RENAME

    def to_readable(self):
        return {
            'name': PROC_TYPE_RENAME,
            'rules': [ rule.to_readable() for rule in self.rules],
        }
