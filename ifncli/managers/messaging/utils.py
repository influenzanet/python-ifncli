import os
import re
import base64
from typing import Optional, Dict
from ...utils import write_content

def find_template_file(m_type, folder_with_templates):
    found = False
    for ext in ['','.html','.htm','.txt']:
        file = os.path.join(folder_with_templates, m_type + ext)
        if os.path.exists(file):
            found = True
            break
    if not found:
        raise ValueError("no template file found to message type: " + m_type)
    return file


def encode_template(content:str)->str:
    """
        Encode template in base64
    """
    return base64.b64encode(content.encode()).decode()

def decode_template(encoded:str):
    """
        Decode template (base64)
    """
    return base64.b64decode(encoded).decode()

def wrap_layout(content, layout=None, vars=None):
    """
        Wrap a content with a layout.
        Content is placed into a placeholder in the layout '{=main_content=}'
        Some other variables can be replaced in the layout using the same syntax {=var=} (e.g. title variable the expected placeholder is {=title=} in the layout)
        vars provides the values for each extra variable as a dictionary (key=variable name)
    """
    content, errors = bind_content(content, vars)
    if layout is not None:
        content = layout.replace('{=main_content=}', content)
    return content, errors

""""
Variable syntax regexp {=name=} {= name =}
"""
VAR_REGEXP = re.compile("(\{=\s*([-\w]+)\s*=\})", re.IGNORECASE)

def resolve_vars(vars:Optional[Dict]):
    """"
        Resolve values and parse reference inside values with circular dependency detection
        So variables can contains reference to other variables
    """
    if vars is None:
        return (None, None)
    values = {} # Resolved values
    temporary = [] # Visiting items
    marked = [] # Already visited 
    problems = [] # Collected problems
    def resolve(name):
        if name in temporary:
            raise Exception("Circular dependency :" + "/".join(temporary))
        if name not in marked:
            temporary.append(name)
            if name in vars:
                value = vars[name]
                for p in VAR_REGEXP.findall(value):
                    n = p[1]
                    resolve(n)
                value, pp = bind_vars(value, values)
                if len(pp) > 0:
                    for p in pp:
                        problems.append( "%s in '%s'" % (p, name) )
                values[name] = value
            else:
                problems.append("reference '%s' not found at %s " % (name, "/".join(temporary)))
            marked.append(name)
            temporary.remove(name)
    for n in vars.keys():
        resolve(n)
    return values, problems

def bind_vars(data:str, vars:Optional[Dict]):
    """"
        Bind variables with values in vars in a content string data
        variables are using the syntax {= name =}
    """
    problems = []
    if vars is None:
        return data
    for p in VAR_REGEXP.findall(data):
        m = p[0]
        name = p[1]
        if name in vars:
            data = data.replace(m, vars[name])
        else:
            problems.append("'%s' not found" % name)
    return data, problems

def bind_content(data, vars):
    """
        Bind a string content with variables in vars, the content can contains reference to variables in vars using
        the {=name=} syntax
        vars can also contain variables reference (with the same syntax) and are resolved before parsing the content 

        Returns:
            data : content with variables binded with their resolved values
            problems: List[str] list of problems detected in content ()
    """
    if vars is None:
        return data
    problems = []
    values, pp = resolve_vars(vars)
    if len(pp) > 0:
        problems.extend(pp)
    data, pp = bind_vars(data, values)
    if len(pp) > 0:
        problems.extend(pp)
    return data, problems

def read_and_convert_html(path, vars=None, layout=None):
    content = open(path, 'r', encoding='UTF-8').read()
    content, problems = wrap_layout(content, layout=layout, vars=vars)
    built = vars is not None or layout is not None
    if built:
        write_content(path + '.built.html', content)
        if len(problems) > 0:
            write_content(path + '.built.problems', "\n".join(problems))
    if len(problems) > 0:
        for p in problems:
            print("%s : %s" % (path, p))
    return encode_template(content)

def read_and_encode_template(path, vars=None, layout=None):
    return read_and_convert_html(path, vars=vars, layout=layout)