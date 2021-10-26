
import os
import json

from .types import *

def load_library():
    path = os.path.dirname(__file__)
    data = json.load(os.path.join(path, 'expressions.json'))
    knowns = {}
    defs = data['expressions']
    for name, expDef in defs.items():
        exp = parse_exp_definition(expDef)
        knowns[name] = exp
    return knowns

def parse_arguments(args: List, refs:List):
    params = []
    ref = None
    for index, a in enumerate(args):
        variadic = False
        if isinstance(a, str):
            # We only get name
            name = a
           
        else:
            # Object description
            if 'variadic' in a:
                variadic = a['variadic']
            name = a['name']
            if 'ref' in a:
                role = a['ref']
        p = Arg(name, pos=index, variadic=variadic)
        if role is not None:
            ref = KeyReference(role, p)
            refs.append(ref)
        params.append(p)
    return params


def parse_exp_definition(expDef):
    params = []
    refs = [] # References
    if isinstance(expDef, list):
        # This is a argument list
        params = parse_arguments(expDef, refs)
    else:
        # Object describing the function
        if 'params' in expDef:
            params = parse_arguments(expDef['params'], refs)


