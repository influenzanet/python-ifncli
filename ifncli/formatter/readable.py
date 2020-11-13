
from .models import Expression, TranslatableList, Translatable, Timestamp
from .expression import render_expression
from .translatable import render_translatable

class RedeableRenderer:
    """
        Render a value (possibly an complex structure) to a human readable structure and render parsed elements
        
        This class handles the transformation of some elements parsed in object like Expression, Translatable
        The rendering here is just to transform some elements to a more friendly readable form once serialized in yaml
        It takes a context to be able to filter (for example only show one language).

        The intention here is not to maintain a machine readable structure, as some elements can be merged or output as string

    """

    def __init__(self, context):
        self.context = context

    def render(self, value):
        if isinstance(value, Expression):
            return render_expression(value, self.context)

        if isinstance(value, TranslatableList):
            return render_translatable(value, self.context)

        if isinstance(value, Timestamp):
            return value.to_time()

        if hasattr(value, 'to_readable'):
            r = value.to_readable()
            return self.render(r)

        if isinstance(value, dict):
            dd = {}
            for k, v in value.items():
                dd[k] = self.render(v)
            return dd
        if isinstance(value, list):
            dd = []
            for v in value:
                dd.append(self.render(v))
            return dd
        
        return value

        

def as_readable(value, context):
    """
        Transform a structure to a readable one
        value should first be parsed using parsers function to prepare some elements into more useable objects
        see study_parser, parse_translatable, expression_parser
    """
    renderer = RedeableRenderer(context)
    return renderer.render(value)