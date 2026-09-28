import fnmatch
import re
from typing import Union

def apply_glob(pattern, values:list):
    """
        Select list from a glob pattern
    """
    f = lambda x:fnmatch.fnmatch(x, pattern)
    return list(filter(f, values))

def apply_re(pattern, values: list):
    """
        Select from a list using a re pattern
    """
    f = lambda x:re.match(pattern) is not None
    return list(filter(f, values))

class ColumnSelector:
    """
        Select a list of columns from a list of column selectors
        A selector can be:
            - a string (column name)
            - a list of string
            - a dictionary with either:
                'glob' key with pattern(s) (single string or list of pattern)
                're' key with pattern(s) (single string or list of pattern)
    """
    def __init__(self, conf):
        self.selectors = list(self.config(conf))
         
    def config(self, conf):
        if not isinstance(conf, list):
            raise ValueError("Column selector entry must be a list (each entry could be str or dict['glob' or 're'])")
        for selector_conf in conf:
            if isinstance(selector_conf, str) or isinstance(selector_conf, list):
                yield FixedColumnSelector(selector_conf)
            if isinstance(selector_conf, dict):
                for mode in ['glob','re']:
                    if mode in selector_conf:
                        yield PatternColumnSelector(selector_conf[mode], mode)
    
    def select(self, data_columns:list[str]):
        columns = []
        for selector in self.selectors:
            cols = list(selector.select(data_columns))
            columns.extend(cols)
        columns = list(set(columns)) 
        return columns   

    def __str__(self) -> str:
        return ','.join(map(str, self.selectors))

class BaseColumnSelector:

    def select(self, data_columns:list[str]):
        raise NotImplementedError()

class FixedColumnSelector(BaseColumnSelector):

    def __init__(self, columns: Union[list[str],str]):
        self.columns = []
        if isinstance(columns, str):
            self.columns.append(columns)
        if isinstance(columns, list):
            self.columns.extend(columns)
    
    def select(self, data_columns:list[str]):
        for col in data_columns:
            if col in self.columns:
                yield col
    
    def __str__(self):
        return "fixed(%s)" % ( ','.join(self.columns))


class PatternColumnSelector:
    
    def __init__(self, patterns, mode:str):
        if isinstance(patterns, str):
            patterns = [patterns]
        self.patterns = patterns
        self.mode = mode
        if mode == 'glob':
            self.func = apply_glob
        if mode == 're':
            self.func = apply_re
    
    def select(self, data_columns:list[str]):
        out = []
        for p in self.patterns:
            cols = self.func(p, data_columns)
            out.extend(cols)
        return out

    def __str__(self) -> str:
        return "%s(%s)" % ( self.mode, ','.join(self.patterns))