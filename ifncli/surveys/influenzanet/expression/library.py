
import os
import json
from typing import Dict

from . import KNOWN_EXPRESSIONS, library_path

from .types import *

class ParserException(Exception):
    pass

def load_library():
    path = library_path()
    parser = ExpressionTypeParser()
    parser.parse(path, KNOWN_EXPRESSIONS)

class ExpressionTypeParser:

    def __init__(self) -> None:
        self.enums = {}

    def parse(self, path, knows: Dict[str, ExpressionType]):
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
            if isinstance(a, str):
                # We only get name
                name = a
            else:
                # Object description
                if 'variadic' in a:
                    variadic = a['variadic']
                name = a['name']
                if 'role' in a:
                    role = a['role']
            p = Arg(name, pos=index, variadic=variadic)
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
        return ExpressionType(params, roles)

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
        


