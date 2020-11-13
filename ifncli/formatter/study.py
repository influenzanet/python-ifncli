from .expression import expression_parser, render_expression
from .translatable import parse_translatable, render_translatable
from .readable import as_readable

def study_parser(study):
    """"
     Parse study to have some elements easier to represents (like expression)
    """
    if 'rules' in study:
        # Replace
        rr = []
        for rule in study['rules']:
            r = expression_parser(rule)
            rr.append(r)
        study['rules'] = rr
    if 'props' in study:
        pp = study['props']
        if 'name' in pp:
            pp['name'] = parse_translatable(pp['name'])
        if 'description' in pp:
            pp['description'] = parse_translatable(pp['description'])
        if 'tags' in pp:
            tt = []
            for tag in pp['tags']:
                if 'label' in tag:
                    tag['label'] =parse_translatable(tag['label'])
                tt.append(tag)
            pp['tags'] = tt
        study['props'] = pp
    return study


def readable_study(study, context):
    ss = study_parser(study)
    return as_readable(ss, context)
    
