from .model import Expression, Scalar

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

