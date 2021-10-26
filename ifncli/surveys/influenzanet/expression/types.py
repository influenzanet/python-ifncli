from ...context import Context

from typing import List,Union,Optional

ARG_SCALAR = 'scalar'
ARG_SURVEYKEY = 'survey_key'
ARG_ITEM_KEY = 'item_key'
ARG_RG_KEY = 'rg_key' # eg 'rg'
ARG_RG_ITEM_KEY = 'rg_item_key' # eg scg
ARG_RG_COMP_KEY = 'rg_comp_key' # eg '1'
ARG_RG_ITEM_PREFIX = 'full_response_key' # eg full response key from item  e.g. rg.scg.1
ARG_STUDY_STATUS = 'study_status'

class Arg:
    """
        Argument descripton
    """
    def __init__(self, name:str, pos: int, variadic:bool):
        self.name = name
        self.pos = pos
        self.variadic = variadic

class CompositeArgument:
    def __init__(self, args:List[Arg]):
        self.args = args

class Reference:
    """
        Argument reference to another element in the survey definition.
        The reference type is defined by the role of the reference
    """
    def __init__(self, role: str):
        self.role = role

class KeyReference(Reference):
    """
        Reference to a key type in the survey
        Role defines the kind of key
    """
    def __init__(self, role: str, param:Arg):
        super(KeyReference, self).__init__(role)
        self.param = param

class ResponseKeyReference(Reference):
    """
        Reference to a Response key of an item in the survey
        item_key: argument where the item key is defined
    """
    def __init__(self, role: str, item_key:Arg, response: Union[Arg, CompositeArgument] ):
        super(ResponseKeyReference, self).__init__(role)
        self.item_key = item_key
        self.response = response

class EnumerationReference(Reference):
    def __init__(self, role: str, values: List[str]):
        super(EnumerationReference, self).__init__(role)
        self.values = values

ArgList = List[Arg]

class ExpressionType:
    """
        Describe a type of expression
    """
    def __init__(self, params: Optional[ArgList]=None, references: Optional[List[Reference]]=None ):
        self.params = params
        self.references = references

    def has_params(self):
        return len(self.params) > 0
    
    def get_param(self, index):
        if index > len(self.params)-1:
            return None
        return self.params[index]



def find_expression_type(name:str)->ExpressionType:
    if name in KNOWN_EXPRESSIONS:
        return KNOWN_EXPRESSIONS[name]
    return None




