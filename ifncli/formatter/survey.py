from .translatable import to_translatable,parse_translatable
from .models import Timestamp
from .models.survey import SurveyGroupItem, SurveySingleItem, SurveyItemGroupComponent, SurveyItemResponseComponent, SurveyItemComponent
from .expression import expression_parser
from .readable import as_readable

def component_parser(obj):
    role = obj['role']
    key =  obj.get('key')

    comp = None
    if 'items' in obj:
        # ItemGroupComponent
        ii = []
        for it in obj['items']:
            ii.append(component_parser(it))
        
        if 'order' in obj:
           order = expression_parser(obj['order'])
        else:
            order = None
        comp = SurveyItemGroupComponent(key=key, role=role, items=ii, order=order)

    if 'dtype' in obj:
        # ResponseComponent
        if comp is not None:
            raise Exception("Component cannot be group and response type")
        if 'properties' in obj:
            # Todo parsing
            props = obj['properties']
        else:
            props = None
        comp = SurveyItemResponseComponent(key=key, role=role, dtype=obj['dtype'], props=props)

    if comp is None:
        # ItemComponent base (Display ?)
        comp = SurveyItemComponent(key=key, role=role)

    if 'content' in obj:
        comp.content = parse_translatable(obj['content'])
    
    if 'description' in obj:
        comp.description = parse_translatable(obj['description'])

    if 'displayCondition' in obj:
        comp.displayCondition = expression_parser(obj['displayCondition'])

    if 'disabled' in obj:
        comp.disabled = expression_parser(obj['disabled'])

    if 'style' in obj:
        ss = {}
        for s in obj['style']:
            ss[s['key']] = s['value']
        comp.style = ss

    return comp

def survey_item_parser(obj):
    
    _id = obj.get('id')
    version = obj.get('version')
    key = obj['key']
    if 'items' in obj:

        ii = []
        for i in obj['items']:
            ip = survey_item_parser(i)
            ii.append(ip)
        if 'selectionMethod' in obj:
            selection = expression_parser(obj['selectionMethod'])
        else:
            selection = None
        item = SurveyGroupItem(key,  id=_id, items=ii, selection=selection, version=version )

    else:
        comp = component_parser(obj['components'])
        _type = obj.get('type')
        if 'validations' in obj:
            vv = []
            for v in  obj['validations']:
                v['rule'] = expression_parser(v['rule']) 
                vv.append(v)
            validations = vv
        else:
            validations = None
        item = SurveySingleItem(key, id=_id, type=_type, components=comp, validations=validations)

    return item

def survey_definition_parser(surveyDef):
    ii = []
    for item in surveyDef['items']:
        item = survey_item_parser(item)
        ii.append(item)
    surveyDef['items'] = ii    
    return surveyDef

def survey_parser(survey):
    pp =  survey['props']
    pp = to_translatable(pp, ['name','description', 'typicalDuration'])
    survey['props'] = pp
    pp = survey['current']
    pp['published'] = Timestamp(pp['published'])
    pp['surveyDefinition'] = survey_definition_parser(pp['surveyDefinition'])
    survey['current'] = pp
    return survey
    
def readable_survey(survey, context):
    ss = survey_parser(survey)
    return as_readable(ss, context)
