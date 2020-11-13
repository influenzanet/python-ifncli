
from .expression import readable_expression
from .study import readable_study
from .survey import  readable_survey
from .translatable import readable_translatable
from .readable import as_readable

class Context:
    def __init__(self, language=None):
        self.language = language
    
    def get_language(self):
        return self.language

def create_context(language=None):
    return Context(language=language)

