from .expression import Expression, expression_parser

from typing import List, Union

TranslatePart = Union[str, Expression]

class Translatable:
    
    def __init__(self, code:str, value):
        """
        docstring
        """
        self.code = code
        self.value = value

    def value_as_text(self, context):
        if isinstance(self.value, list):
            vv = []
            for item in self.value:
                if(isinstance(item, Expression)):
                    v = item.to_readable(context)
                else:
                    v = str(item)
                vv.append(v)
            return ' '.join(vv)

    def get_parts(self) -> List[TranslatePart]:
        return self.value

    def get_code(self)->str: 
        return self.code

    def __repr__(self):
        return "<T[%s, %s]>" % (self.code, self.value)
        
class TranslatableList:

    def __init__(self, values:List[Translatable]):
        self.values = values

    def get_with_context(self, context)->List[Translatable]:
        language = context.get_language()
        if language is None:
            return self.get_translates()
        tt = []
        if isinstance(language, str):
            language = [language]

        for t in self.values:
            if t.code in language or t.code.startswith('_'):
                tt.append(t)
        return tt

    def get_translates(self)->List[Translatable]:
        return self.values

    def to_readable(self, ctx):
        render_translatable(self, ctx)


def to_translatable(data, fields):
    """
        Transform some fields of a dictionnary to translatable object
    """
    for field in fields:
        data[field] = parse_translatable(data[field])
    return data

def parse_translatable(values):
    """
        Parse a translatable data structure {code:, parts: [...]} to an object based structure
        Returns TranslatableList
    """
    tt = []
    for value in values:
        code = value['code']
        texts = []
        for p in value['parts']:
            if 'str' in p:
                texts.append(p['str'])
                break
            if 'num' in p:
                texts.append(str(p['num']))
            if 'exp' in p:
                exp = expression_parser(p['exp'])
                texts.append(exp)

        tt.append(Translatable(code, texts))
    return TranslatableList(tt)

def render_translatable(t, context):
    """
        Render a Translatable list object
    """
    trans_to_render = t.get_with_context(context)
    values = []

    several = len(trans_to_render) > 1
    for t in trans_to_render:
        if several:
            text = "[%s] %s" % (t.code, t.value_as_text(context))
        else:
            text = t.value_as_text(context)
        values.append(text)
    if len(values) == 0:
        return ''
    if len(values) == 1:
        return values[0]
    return values 

def readable_translatable(values, context):
   tt = parse_translatable(values)
   return render_translatable(tt, context)

