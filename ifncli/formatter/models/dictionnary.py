"""
dictionary model


dictionary is a simplified view of the Influenzanet survey model centered on data collection and encoding

It's used to export as a simple structure (into 'readable' format) or to compare with the standard

"""
class ItemDictionnary:
    """
        Item dictionnary implements a simple question model from the Survey model, centered on data collection
        It only embeds information about data collection and encoding
    """
    def __init__(self, key, type, options, obj):
        self.key = key
        self.type = type
        self.options = options
        self._obj = obj

    def __repr__(self):
        return {'key': self.key, 'type': self.type}.__repr__()

    def to_readable(self):
        """
            Transforms the object into readable format
        """
        return {
            'key': self.key,
            'type': self.type,
            'options': self.options,
        }

class OptionDictionnary(dict):

    def __init__(self, key, role, item_key):
        self.key = key
        self.role = role
        self.item_key = item_key
    
    def __repr__(self):
        return self.to_readable().__repr__()

    def to_readable(self):
        """
            To readable representation (simple structure serializable as simple json or yaml)
        """
        return {
            'key': self.key, 
            'role': self.role, 
            'item_key': self.item_key
        }