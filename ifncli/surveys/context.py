from typing import List, Optional

class Context:
    """
    Rendering context
    """
    def __init__(self, language:Optional[List[str]]=None):
        self.language = language
    
    def get_language(self):
        return self.language

def create_context(language=None):
    if language is not None:
        if isinstance(language, str):
            language = language.split(',')
        if not isinstance(language, list):
            raise Exception("language must be a list (or a string comma separated items)")
        language = [x.strip() for x in language]
    return Context(language=language)
