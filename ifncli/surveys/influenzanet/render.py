from .parser import survey_parser, Survey
from .dictionnary import ItemDictionnary
from ..readable import  as_readable
from typing import List, Optional
from ..context import Context

def readable_survey(survey, context:Context):
    """
        Transform a json based survey model into a 'readable' model (simpler and easier to read model) with a context
        
        context is a parameters set determining how to simplify the model (e.g. language..)
    """
    ss = survey_parser(survey)
    return as_readable(ss, context)

def render_to_dict(survey: Survey)-> Optional[ItemDictionnary]:
    """
        Render a Survey model into a dictionary based view (see influenzanet.dictionnary.ItemDictionnary)
    """
    item = survey['current']['surveyDefinition']
    return item.get_dictionnary()

def readable_study(study, context:Context):
    ss = study_parser(study)
    return as_readable(ss, context)

def survey_to_dictionnary(survey):
    """
        Transform a survey 
    """
    ss = survey_parser(survey)
    return render_to_dict(ss)