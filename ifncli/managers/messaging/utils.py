import os
import os
import base64

from ifncli.utils import write_content

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
    return base64.b64encode(content.encode()).decode()

def decode_template(encoded:str):
    return base64.b64decode(encoded).decode()

def wrap_layout(content, layout=None, vars=None)->str:
    """
        Wrap a content with a layout.
        Content is placed into a placeholder in the layout '{=main_content=}'
        Some other variables can be replaced in the layout using the same syntax {=var=} (e.g. title variable the expected placeholder is {=title=} in the layout)
        vars provides the values for each extra variable as a dictionnary (key=variable name)
    """
    if vars is not None:
        for name, value in vars.items():
            var = '{=' + name + '=}'
            content = content.replace(var, value)

    if layout is not None:
        content = layout.replace('{=main_content=}', content)
    return content


def read_and_convert_html(path, vars=None, layout=None):
    content = open(path, 'r', encoding='UTF-8').read()
    content = wrap_layout(content, layout=layout, vars=vars)
    built = vars is not None or layout is not None
    if built:
        write_content(path + '.built', content)
    return encode_template(content)

def read_and_encode_template(path, vars=None, layout=None):
    return read_and_convert_html(path, vars=vars, layout=layout)