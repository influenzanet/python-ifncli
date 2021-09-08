
class TranslatableList:

    def __init__(self, values):
        self.values = values

    def get_with_context(self, context):
        language = context.get_language()
        if language is None:
            return self.values
        tt = []
        if isinstance(language, str):
            language = [language]

        for t in self.values:
            if t.code in language:
                tt.append(t)
        return tt


class Translatable:

    def __init__(self, code, value):
        """
        docstring
        """
        self.code = code
        self.value = value

    def value_as_text(self):
        if isinstance(self.value, list):
            return ' '.join(self.value)

    def __repr__(self):
        return "<T[%s, %s]>" % (self.code, self.value)
        
    


