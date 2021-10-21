from ..context import Context

KNOWN_EXPRESSION = {
    'IFTHEN': {
        'params': ['condition']
    },
    'ADD_NEW_SURVEY': {
        'params': ['surveyKey','validFrom','validUntil','category']
    },
    'responseHasKeysAny': {
        'params': ['item', 'response']
    },
    'checkEventType': {
        'params': ['type']
    },
    'hasStudyStatus': {
        'params': ['status']
    }
}

class Expression:
    
    def __init__(self, name, params=None):
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
        if not self.name in KNOWN_EXPRESSION:
            return None
        action = KNOWN_EXPRESSION[self.name]
        if 'params' in action:
            params_list = action['params']
            if(index > len(params_list)-1):
                return None
            return params_list[index]

    def to_readable(self, ctx):
        return render_expression(self, ctx)


class Scalar:

    def __init__(self, type, value):
        self.type = type
        self.value = value

    def is_expression(self):
        return False

    def is_scalar(self):
        return True

    def __str__(self):
        if self.type == "str":
            return '"' + self.value + '"'
        return str(self.value)


# Expression to object nodes
def expression_arg_parser(expr, level=0, idx=0):
    if not 'dtype' in expr:
        dtype = 'str'
    else:
        dtype = expr['dtype']
    
    if not dtype in expr:
        print("Invalid expression claim to be %s but no entry" % (dtype, ))
    value = expr[dtype]
    if dtype == 'exp':
        return expression_parser(value)
    return Scalar(dtype, value)

def expression_parser(expr, level=0, idx=0):
    params = []
    level = level + 1
    if 'data' in expr:
        idx = 0
        for d in expr['data']:
            p = expression_arg_parser(d, level, idx)
            params.append(p)
            idx = idx + 1
    if 'name' in expr:
        name = expr['name']
    else:
        name = "_%d" % (idx, )
    return Expression(name, params)    

def readable_expression(expr, context):
    """
        Create a readable structure from an expression json object
        
        It turns an expression to a structure more easily readable once represented in yaml
    """
    ee = expression_parser(expr)
    return render_expression(ee, context)


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