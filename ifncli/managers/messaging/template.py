from ...platform import PlatformResources
from ...utils import read_content
from .utils import read_and_encode_template, wrap_layout, decode_template

from typing import Optional, List

class TemplateResult:
    def __init__(self, content:str, problems=Optional[List[str]]):
        self.content = content
        self.problems = problems

    def has_problems(self):
        return len(self.problems) > 0

class TemplateLoader:
    """
            Load a Template html and wrap it with an optional layout and bind platform variables 
    """

    def __init__(self, path, platform:PlatformResources):
        
        self.layout = None
        # Check if global layout exists
        if path is None and not platform.template_layout is None:
               path = platform.template_layout
        
        if not path is None and path != "":
            self.layout = read_content(path, must_exist=True)
        
        if self.layout is None:
            print("Using layout in '%s'" % (path))
    
        template_vars = platform.get_vars()
        
        if 'web_app_url' in template_vars:
            url:str = template_vars.get('web_app_url')
            if url.endswith('/'): # Remove ending slash 
                url = url[:-1] 
        self.vars = template_vars

        # List of problems in the last template loading
        self.problems = []

    def load(self, template_path, language:str)->str:
        """
            Load a template from file and wrap with layout if available
        """
        data = self.vars.copy()
        data['language'] = language
        return read_and_encode_template(template_path, layout=self.layout, vars=data)

    def bind(self, content:str, language:str, is_encoded:bool)->TemplateResult:
        data = self.vars.copy()
        data['language'] = language
        if is_encoded:
            content = decode_template(content)
        content, problems = wrap_layout(content, layout=self.layout, vars=data)
        return TemplateResult(content, problems)