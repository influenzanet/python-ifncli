from .models import *

def json_parser_survey_standard(survey):
    """
        parse survey standard definition from json dictionnary
    """
    ss = StandardSurvey(survey['name'])
    if 'comment' in survey:
        ss.comment = json_parser_comment(survey['comment'])
    index = 1
    for qDef in survey['questions']:
        q = json_parser_question(qDef)
        q.order = index
        ss.add_question(q)
        index = index + 1
    return ss

def json_parser_comment(json):
    if isinstance(json, str):
        return [json]
    return json

def json_parser_description(json):
    if isinstance(json, str):
        return [json]
    return json

def import_attr(obj, data, keys):
    for key in keys:
        if key in data:
            setattr(obj, key, data[key])

def json_parser_question(json):
    """
        question definition from json dictionnary
    """
    data_name = json['data_name']

    q = StandardQuestion(data_name, json['type'], json['title'])
    
    if 'description' in json:
        q.description = json_parser_description(json['description'])
    
    if 'mandatory' in json:
        q.mandatory = json['mandatory']
  
    if 'comment' in json:
        q.comment = json_parser_comment(json['comment'])

    import_attr(q, json, ['active','data_type', 'format','rules', 'added_at', 'removed_at', 'platforms', 'target'])

    if 'possible_responses' in json:
        index = 1
        for key, rDef in json['possible_responses'].items():
            try:
                r = json_parser_response(key, rDef, index)
            except Exception as e:
                raise StandardParserException("Error in %s/%s : %s " % (data_name, key, e))
            q.add_response(r)
            index = index + 1

    if 'rows' in json:
        q.rows = json_parser_matrix_dim(json['rows'])

    if 'columns' in json:
        q.columns = json_parser_matrix_dim(json['columns'])

    return q

def json_parser_response(key, json, index):
    
    if not 'text' in json:
        raise StandardParserException("Missing 'text' field")
    
    r = StandardResponse(key, json['text'], index)
    
    import_attr(r, json, ['added_at', 'removed_at', 'platforms'])

    if 'value' in json:
        r.value = json['value']
    
    if 'description' in json:
        r.description = json_parser_description(json['description'])
    
    if 'comment' in json:
        r.comment = json_parser_comment(json['comment'])

    return r

def json_parser_matrix_dim(json):
    rr = StandardMatrixDimensionList()
    index = 1
    for key, d in json.items():
        #print(key, d)
        m = StandardMatrixDimension(d['text'], key, d['value'], index)
        rr[key] = m
        index = index + 1
    return rr