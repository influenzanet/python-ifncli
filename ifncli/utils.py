import yaml
import json

def read_yaml(path):
    obj = yaml.load(open(path, 'r', encoding='UTF-8'),  Loader=yaml.FullLoader)
    return obj

def read_json(path):
    data = json.load(open(path, 'r', encoding='UTF-8'))
    return data
