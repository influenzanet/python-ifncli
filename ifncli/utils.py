import yaml
import json

def read_yaml(path):
    obj = yaml.load(open(path, 'r', encoding='UTF-8'),  Loader=yaml.FullLoader)
    return obj

def read_json(path):
    data = json.load(open(path, 'r', encoding='UTF-8'))
    return data

def to_json(object):
    return json.dumps(object)

def readable_yaml(object):
    return yaml.dump(object, default_flow_style=False, sort_keys=False)

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