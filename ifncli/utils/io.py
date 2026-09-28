import sys
import json
import os
import yaml

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
    with open(path, 'r', encoding='UTF-8') as f:
        data = json.load(f)
        f.close()
    return data

def write_json(path, content):
    with open(path, 'w') as f:
        json.dump(content, f)
        f.close()

def to_json(object):
    return json.dumps(object)


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