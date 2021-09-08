
from .expression import readable_expression
from .study import readable_study
from .survey import  readable_survey, survey_to_dictionnary, survey_parser
from .translatable import readable_translatable
from .readable import as_readable
from .html import survey_to_html

class Context:
    def __init__(self, language=None):
        self.language = language
    
    def get_language(self):
        return self.language

def create_context(language=None):
    if isinstance(language, str):
        language = language.split(',')
    if not isinstance(language, list):
        raise Exception("language must be a list (or a string comma separated items)")
    
    language = [x.strip() for x in language]
    return Context(language=language)

