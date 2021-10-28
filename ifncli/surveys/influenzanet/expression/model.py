from __future__ import annotations

from ...context import Context
from . import KNOWN_EXPRESSIONS
from .types import Arg
from typing import Optional, List
class Expression:
    
    def __init__(self, name, params=Optional[List]):
        self.name = name
        if params is None:
            params = []
        self.params = params
        self._has_expression_param = False
        for p in params:
            if p.is_expression():
                self._has_expression_param = True
                break
    
    def is_expression(self):
        return True

    def has_expression_param(self):
        return self._has_expression_param

    def is_scalar(self):
        return False

    def param_name(self, index):
        if not self.name in KNOWN_EXPRESSIONS:
            return None
        expType = KNOWN_EXPRESSIONS[self.name]
        if expType.has_params():
            p = expType.get_param(index)
            if isinstance(p, Arg):
                return p.name
            return p

    def to_readable(self, ctx):
        return render_expression(self, ctx)

    def __repr__(self) -> str:
        return render_expression(self, Context()).__repr__()

class Scalar:

    def __init__(self, type, value):
        self.type = type
        self.value = value

    def is_expression(self):
        return False

    def is_scalar(self):
        return True

    def __repr__(self):
        if self.type == "str":
            return '"' + self.value + '"'
        return str(self.value)
    
    def __str__(self):
        return str(self.value)


def with_default_names(args):
    """
    From a list of tuples (name, value) where name is the infered parameter name (None if not found)
    Transform the name of each by its index if is None
    """
    index = 0
    pp = []
    for a in args:
        if a[0] is None:
            a = ("%d" % (index), a[1])
        pp.append(a)
        index = index + 1
    return pp


def render_expression(ee, context):
    """
        Render an Expression object to a Yaml-ready readable data structure
    """
    if ee.is_expression():
        pp = []
        index = 0
        for p in ee.params:
            name = ee.param_name(index)
            pp.append( (name, render_expression(p, context)) )
            index = index + 1
        d = {}
        if ee.has_expression_param():
            pp = with_default_names(pp)
            pp = dict(pp)
            d[ee.name] = pp
        else:
            # All args are scalars
            ss = []
            for p in pp:
                if p[0] is not None:
                    s = "%s=%s" % (p[0], str(p[1]))
                else:
                    s = str(p[1])
                ss.append(s)
            pp = ', '.join(ss)
            d = "%s(%s)" % (ee.name, pp)
        return d
    if ee.is_scalar():
        return str(ee.value)
    return {'_unknown':'Unknown type'}  


