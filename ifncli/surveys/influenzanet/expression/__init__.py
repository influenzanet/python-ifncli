
KNOWN_EXPRESSIONS = {}
KNOWN_ENUMS = {}
import os

from typing import Optional

from .model import *
from .parser import expression_parser, expression_arg_parser
from .readable import readable_expression
from .types import ExpressionType

def find_expression_type(name:str)->Optional[ExpressionType]:
    if name in KNOWN_EXPRESSIONS:
        return KNOWN_EXPRESSIONS[name]
    return None

def library_path():
    return os.path.join(os.path.dirname(__file__), 'expressions.json')

def schema_path():
    return os.path.join(os.path.dirname(__file__), 'expressions.schema')