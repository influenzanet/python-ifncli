from ...context import Context

from . import KNOWN_EXPRESSIONS
from typing import List,Union,Optional

ARG_SCALAR = 'scalar'
ARG_SURVEYKEY = 'survey_key'
ARG_ITEM_KEY = 'item_key'
ARG_RG_KEY = 'rg_key' # eg 'rg'
ARG_RG_ITEM_KEY = 'rg_item_key' # eg scg
ARG_RG_COMP_KEY = 'rg_comp_key' # eg '1'
ARG_RG_COMP_PREFIX = 'rg_comp_prefix' 
ARG_RG_COMP_FULL_PATH = 'rg_full_path' # eg full response key from item e.g. rg.scg.1
ARG_STUDY_STATUS = 'study_status'
ARG_QUALIFIED_RESPONSE ='qualified_response'
ARG_QUALIFIED_RG = 'qualified_rg'
ARG_FLAG_KEY = 'flag_key'
ARG_TIMESTAMP = 'timestamp'
ARG_PATH = 'path' # Path of objects like Q1.rg.scg.1
ARG_ITEM_PATH = 'item_path' # Path of any object from a item
ARG_VALIDATION_KEY = 'validation_key'
KNOWN_ARG_ROLES = [
    ARG_SCALAR,
    ARG_SURVEYKEY,
    ARG_ITEM_KEY,
    ARG_RG_KEY,
    ARG_RG_ITEM_KEY,
    ARG_RG_COMP_KEY,
    ARG_RG_COMP_PREFIX,
    ARG_RG_COMP_FULL_PATH,
    ARG_STUDY_STATUS,
    ARG_QUALIFIED_RESPONSE,
    ARG_QUALIFIED_RG,
    ARG_FLAG_KEY,
    ARG_TIMESTAMP,
    ARG_PATH,
    ARG_VALIDATION_KEY
]

class Arg:
    """
        Argument descripton
    """
    def __init__(self, name:str, pos: int, role:str=None, variadic:bool=False, allow_this:bool=False, optional:bool=False, description:str=None):
        self.name = name
        self.pos = pos
        self.variadic = variadic
        self.allow_this = allow_this
        self.optional = optional
        self.description = description
        self.role = role

    def __repr__(self) -> str:
        return "<Arg %d %s>" % (self.pos, self.name)

    def to_readable(self, ctx):
        return self.name

class CompositeArgument:
    def __init__(self, args:List[Arg]):
        self.args = args

    def __repr__(self) -> str:
        return self.args.__repr__()
    

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

    def __repr__(self) -> str:
        return "<KeyRef %s %s>" % (self.role, self.param)

class ItemPathReference(Reference):
    """
        Reference to a key path of an item in the survey
        item_key: argument where the item key is defined
        paths : list of argument to construct the list
    """
    def __init__(self, role: str, item_key:Arg, path: Union[Arg, CompositeArgument] ):
        super(ItemPathReference, self).__init__(role)
        self.item_key = item_key
        self.path = path

    def __repr__(self) -> str:
        return '<ItemPath %s %s>' % (self.item_key, self.path)


class EnumerationReference(Reference):
    """
        Role with a predefined value
    """
    def __init__(self, role: str, param: Arg, values: List[str]):
        super(EnumerationReference, self).__init__(role)
        self.values = values
        self.param = param

    def __repr__(self) -> str:
        d = {"role": self.role, "param": self.param, "values": self.values}
        return d.__repr__()

class ArgList:

    def __init__(self, params: List[Arg]) -> None:
        self.params = params
        d = {}
        for p in params:
            if p.name in d: 
                raise Exception("Argument '%s' already in list" % (p.name,))
            d[p.name] = p
        self.names = d

    def __len__(self):
        return len(self.params)

    def get_by_name(self, name)->Optional[Arg]:
        if name in self.names:
            return self.names[name]
        return None

    def at(self, index)->Optional[Arg]:
        if index < 0:
            raise Exception("Out of bound index %d" % (index, ))
        if index >= len(self.params):
            raise Exception("Out of bound index %d" % (index, ))
        return self.params[index]

    def __getitem__(self, i):
        return self.at(i)

    def __iter__(self):
        return iter(self.params)

    def __repr__(self) -> str:
        return self.params.__repr__()

class BaseExpressionType:

    pass

class UnknownExpressionType(BaseExpressionType):
    """
        Expression only known by name (doesnt knows params)
    """
    def has_params(self):
        return False

    def has_refs(self):
        return False

    def __repr__(self) -> str:
        return '<UnknownExpr>'

class ExpressionType(BaseExpressionType):
    """
        Describe a type of expression
    """
    def __init__(self, params: Optional[ArgList]=None, references: Optional[List[Reference]]=None ):
        self.params = params
        self.references = references
        self.kind = None
        self.description = None

    def has_params(self):
        return self.params is not None and len(self.params) > 0
    
    def get_param(self, index):
        if self.params is None:
            return None
        if index > len(self.params)-1:
            return None
        return self.params[index]

    def has_refs(self):
        return self.references is not None and len(self.references) > 0

    def __repr__(self) -> str:
        d = {}
        if self.kind is not None:
            d['kind'] = self.kind
        if self.params is not None:
            d['params'] = self.params
        if self.references is not None:
            d['refs'] = self.references
        return '<Expr ' + d.__repr__() + '>'
