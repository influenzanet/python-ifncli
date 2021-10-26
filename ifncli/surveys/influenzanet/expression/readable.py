from .model import render_expression
from .parser import expression_parser

def readable_expression(expr, context):
    """
        Create a readable structure from an expression json object
        
        It turns an expression to a structure more easily readable once represented in yaml
    """
    ee = expression_parser(expr)
    return render_expression(ee, context)