
from .models import Translatable, TranslatableList

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
            text = "[%s] %s" % (t.code, t.value_as_text())
        else:
            text = t.value_as_text()
        values.append(text)
    return values           

def readable_translatable(values, context):
   tt = parse_translatable(values)
   return render_translatable(tt, context)