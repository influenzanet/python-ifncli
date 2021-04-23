import yaml
import json
import os

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