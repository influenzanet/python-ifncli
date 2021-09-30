from .parser import survey_parser, Survey

def render_to_dict(survey: Survey):
    """
        Render a Survey model into a dictionary based view (see models.dictionnary.ItemDictionnary)
    """
    item = survey['current']['surveyDefinition']
    return item.get_dictionnary()

def survey_to_dictionnary(survey):
    """
        Transform a survey 
    """
    ss = survey_parser(survey)
    return render_to_dict(ss)