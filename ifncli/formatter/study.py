from .expression import expression_parser, render_expression
from .translatable import parse_translatable, render_translatable, to_translatable
from .readable import as_readable
from .models import Timestamp

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
        pp = to_translatable(pp, ['name','description'])
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
    
def readable_survey(survey, context):
    ss = survey_parser(survey)
    return as_readable(survey, context)