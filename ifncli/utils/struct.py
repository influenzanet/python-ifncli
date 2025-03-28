# Utilities for Data structure manipulations

from typing import Dict, List, Set, Union
import yaml

def readable_yaml(object):
    """
        Create Yaml from object using options to improve readability
    """
    return yaml.dump(object, default_flow_style=False, sort_keys=False, width=1000)

def translatable_to_list(data, language=None):
    """
        Select translatable
    """
    values = []
    for d in data:
        s = []
        if language is not None:
            if d['code'] != language:
                continue
        else:
            s.append("[%s] " % d['code'])
        for p in d['parts']:
            s.append(p['str'])
        values.append(' '.join(s))
    return values        


# Create a list 
# json json data
# fields list of fields to extract
def json_to_list(json, fields):
    if isinstance(fields, dict):
        ff = []
        cols = []
        for col,f in fields.items():
           cols.append(col)
           ff.append(f) 
        fields = ff   
    else:
        cols = fields 
    rows = []
    for row in json:
        r = []
        for field in fields:
            v = row[field]
            r.append(v)
        rows.append(r)
    return (cols, rows)

def check_keys(data: Dict, keys:Union[List, Set], complete:bool=False):
    data_keys = data.keys()
    keys = set(keys)
    diff = list(data_keys - keys)
    if len(diff) > 0:
        raise KeyError("Keys %s is not in acceptable keys" % (','.join(diff)))
    if complete:
        missings = list(keys - data_keys)    
        if len(missings) > 0:
            raise KeyError("Some keys are missing : %s" % (','.join(missings)))
