import sys
import json
import os
from typing import Dict, List, Set, Union
import yaml
import re
from datetime import datetime

def read_content(path, must_exist=False, default=None):
    found = os.path.exists(path)
    if not found:
        if must_exist:
            raise IOError("File %s doesnt exist" % path)
        return default
    with open(path, 'r', encoding='UTF-8') as f:
        content = f.read()
        f.close()
    return content

def write_content(path, content):
    with open(path, 'w') as f:
        f.write(content)
        f.close()
    

def read_yaml(path):
    obj = yaml.load(open(path, 'r', encoding='UTF-8'),  Loader=yaml.FullLoader)
    return obj

def read_json(path):
    data = json.load(open(path, 'r', encoding='UTF-8'))
    return data

def to_json(object):
    return json.dumps(object)

def readable_yaml(object):
    """
        Create Yaml from object using options to improve readability
    """
    return yaml.dump(object, default_flow_style=False, sort_keys=False, width=1000)

def translatable_to_list(data, language=None):
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

class Output:
    """
        Simple output class
        If no path provided the print contents
    """
    def __init__(self, path=None):
        self.path = path
    
    def write(self, data):
        need_close = False
        if not self.path is None :
            output = open(self.path, 'w')
            need_close = True
        else:
            output = sys.stdout

        output.write(data)
        
        if need_close:
            output.close()

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
   
# FIXME: this duplicated code should be avoided, implementation taken from see
# user-management-service/pkg/utils/utils.go commit #c27b903
def check_password_strength(password):

    if len(password) < 8:
        return False

    lowercase = re.search(r"[a-z]", password) is not None
    uppercase = re.search(r"[A-Z]", password) is not None
    number = re.search(r"[\d]", password) is not None
    symbol = re.search(r"[\W]", password) is not None

    password_check = sum([lowercase, uppercase, number, symbol]) > 2

    return password_check            

ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def from_iso_time(time:str):
    return datetime.strptime(time, ISO_TIME_FORMAT)

def to_iso_time(d):
    return d.strftime(ISO_TIME_FORMAT)
