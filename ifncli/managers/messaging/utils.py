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

def read_and_convert_html(path, vars=None, layout=None):
    content = open(path, 'r', encoding='UTF-8').read()

    built = False
    if vars is not None:
        built = True
        for name, value in vars.items():
            var = '{=' + name + '=}'
            content = content.replace(var, value)

    if layout is not None:
        content = layout.replace('{=main_content=}', content)
        built = True

    if built:
        write_content(path + '.built', content)

    return base64.b64encode(content.encode()).decode()

def read_and_encode_template(path, vars=None, layout=None):
    return read_and_convert_html(path, vars=vars, layout=layout)