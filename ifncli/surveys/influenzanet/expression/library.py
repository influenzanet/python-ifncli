
import os
import json
from typing import Dict

from . import KNOWN_EXPRESSIONS,KNOWN_ENUMS, library_path

from .types import *

class ParserException(Exception):
    pass

def load_library():
    path = library_path()
    parser = ExpressionTypeParser()
    parser.parse(path, KNOWN_EXPRESSIONS, KNOWN_ENUMS)
    return (KNOWN_EXPRESSIONS, KNOWN_ENUMS)

class ExpressionTypeParser:

    def __init__(self) -> None:
        self.enums = None

    def parse(self, path, knows: Dict[str, ExpressionType], enums: Dict[str, List] ):
        self.enums = enums
        try:
            data = json.load(open(path, 'r', encoding='UTF-8'))
        except Exception as e:
            raise ParserException("Unable to load json in %s" % path) from e

        for name, values in data['enums'].items():
            self.enums[name] = values

        defs = data['expressions']
        for name, expDef in defs.items():
            try:
                exp = self.parse_exp_definition(expDef)
            except Exception as e:
                raise ParserException("Error parsing '%s'" % name) from e
            knows[name] = exp

    def parse_arguments(self, args: List, refs:List)->ArgList:
        params = []
        role = None
        for index, a in enumerate(args):
            variadic = False
            role = None

            extra = {}

            if isinstance(a, str):
                # We only get name
                name = a
            else:
                # Object description
                if 'variadic' in a:
                    extra['variadic'] = a['variadic']
                if 'allow_this' in a:
                    extra['allow_this'] = a['allow_this']
                if 'optional' in a:
                    extra['optional'] = a['optional']
                if 'description' in a:
                    extra['description'] = a ['description']
                name = a['name']
                if 'role' in a:
                    role = a['role']
            p = Arg(name, pos=index, role=role, **extra)
            
            if role is not None:
                if role in self.enums:
                    ref = EnumerationReference(role, p, self.enums[role])
                else:
                    if not role in KNOWN_ARG_ROLES:
                        raise Exception("Unknown role '%s'" % (role, ))
                    ref = KeyReference(role, p)
                refs.append(ref)
            params.append(p)
        return ArgList(params)
    
    def parse_exp_definition(self, expDef):
        params = None
        roles = [] # References
        if isinstance(expDef, list):
            # This is a argument list
            params = self.parse_arguments(expDef, roles)
        else:
            # Object describing the function
            if 'params' in expDef:
                params = self.parse_arguments(expDef['params'], roles)
            else:
                return UnknownExpressionType()
            if 'roles' in expDef:
                for r in expDef['roles']:
                    role = self.parse_role(r, params)
                    roles.append(role)
        if len(roles) == 0:
            roles = None
        exp_type=  ExpressionType(params, roles)
        if 'description' in expDef:
            exp_type.description = expDef['description']
        return exp_type

    def parse_role(self, roleDef, params:ArgList):
        """
            Parse a role definition in the "roles" entry or an expression definition
            Those definitions can create roles combining several arguments 
        """

        def get_arg(name):
            arg = params.get_by_name(name)
            if arg is None:
                raise Exception("Unknown argument '%s'" % (name))
            return arg

        def get_arg_list(names):
            pp = []
            for p in names:
                arg = get_arg(p)
                pp.append(arg)
            return pp

        role = roleDef['role']

        if role == ARG_ITEM_PATH:
            item_arg = get_arg(roleDef['params']['item_key'])
            path_args = get_arg_list(roleDef['params']['path'])
            if len(path_args) == 1:
                path_args = path_args[0]
            else:
                path_args = CompositeArgument(path_args)

            return ItemPathReference(role, item_arg, path_args)

        return None
        

def render_library(funcs: Dict[str, ExpressionType])->str:
    output = [
        "# Survey Engine Expressions"
    ]
    for name, func in funcs.items():
        out = render_func(name, func)
        output.append("")
        output.append(out)
    return "\n".join(output)

ROLE_NAMES = {
    ARG_FLAG_KEY:"Flag name",
    ARG_ITEM_KEY:"Survey item key",
    ARG_SURVEYKEY:"Survey key",
    ARG_STUDY_STATUS:"Study status name",
    ARG_ITEM_PATH:"Component path of an item",
    ARG_RG_COMP_KEY:"Individual key of a component",
    ARG_RG_COMP_PREFIX:"Prefix of a response group component, e.g. 'rg.scg.', 'rg.mcg.'",
    ARG_RG_KEY:"Key of a response group, e.g. 'rg'",
    ARG_TIMESTAMP:"timestamp",
    ARG_VALIDATION_KEY:"Key of a 'validations' rule of a component"
}

def render_func(name:str, func: ExpressionType)->str:
    o = [
        "## " + name
    ]

    if isinstance(func, UnknownExpressionType):
       return "\n".join(o)

    if func.kind == "action":
        o.append("Survey **action**, useable in survey rules")
    if func.kind == "client":
        o.append("Client side function")
    if func.kind == "service":
        o.append("Service side function, useable in survey rules")

    if func.has_params():
        o.append("")
        o.append("** Parameters **")
        o.append("")
        for p in func.params:
            d = "- `%s`" % (p.name, )
            if p.variadic:
                d += "... " 
            if p.description is not None:
                d += " " + p.description
            else:
                if p.role in ROLE_NAMES:
                    d += " " + ROLE_NAMES[p.role] 
            if p.allow_this:
                d += " [accepts `this` as special value]"
            if p.optional:
                d += " **optional**"
            o.append(d)
    return "\n".join(o)
