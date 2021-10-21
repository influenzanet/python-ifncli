from .translatable import to_translatable,parse_translatable
from .time import Timestamp
from .survey import SurveyGroupItem, SurveySingleItem, SurveyItemGroupComponent, SurveyItemResponseComponent, SurveyItemComponent
from .expression import expression_arg_parser, expression_parser

class Survey(dict):

    def get_name(self):
        return self['props']['name']
        
    def getCurrent(self):
        return self['current']['surveyDefinition']
     

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
        comp = SurveyItemResponseComponent(key=key, role=role, dtype=obj['dtype'])

    if comp is None:
        # ItemComponent base (Display ?)
        comp = SurveyItemComponent(key=key, role=role)

    if 'content' in obj:
        comp.content = parse_translatable(obj['content'])
    
    if 'properties' in obj:
            # Todo parsing
            pp = {}
            for k, p in obj['properties'].items():
                pp[k] = expression_arg_parser(p)
            comp.properties = pp

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

def survey_parser(survey):
    """
    Parse a json based survey (loaded from a json definition file) model into a python object model
    
    Returns: Survey

    """
    pp =  survey['props']
    pp = to_translatable(pp, ['name','description', 'typicalDuration'])
    survey['props'] = pp
    pp = survey['current']
    if 'published' in pp:
        # published is not present when survey is only a draft from editor
        pp['published'] = Timestamp(pp['published'])
    pp['surveyDefinition'] = survey_item_parser(pp['surveyDefinition'])
    survey['current'] = pp
    return Survey(survey)
