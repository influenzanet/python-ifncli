from .parser import survey_parser


def render_to_dict(survey):
    item = survey['current']['surveyDefinition']
    return item.get_dictionnary()

def survey_to_dictionnary(survey):
    ss = survey_parser(survey)
    return render_to_dict(ss)