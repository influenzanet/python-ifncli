
class DataDictionnary:

    def __init__(self, key, type, options):
        """
        docstring
        """
        self.key = key
        self.type = type
        self.options = options

    def __repr__(self):
        return {'key': self.key, 'type': self.type}