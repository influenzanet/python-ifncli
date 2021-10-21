"""
dictionary model


dictionary is a simplified view of the Influenzanet survey model centered on data collection and encoding

It's used to export as a simple structure (into 'readable' format) or to compare with the standard

"""
from typing import List

class OptionDictionnary:

    def __init__(self, key:str, role:str, item_key:str):
        self.key = key
        self.role = role
        self.item_key = item_key
    
    def __repr__(self):
        return self.to_readable().__repr__()

    def to_readable(self, ctx):
        """
            To readable representation (simple structure serializable as simple json or yaml)
        """
        return {
            'key': self.key, 
            'role': self.role, 
            'item_key': self.item_key
        }

class ItemDictionnary:
    """
        Item dictionnary implements a simple question model from the Survey model, centered on data collection
        It only embeds information about data collection and encoding
    """
    def __init__(self, key:str, type:str, options:List[OptionDictionnary], obj):
        self.key = key
        self.type = type
        self.options = options
        self._obj = obj

    def __repr__(self):
        return {'key': self.key, 'type': self.type}.__repr__()

    def to_readable(self, ctx):
        """
            Transforms the object into readable format
        """
        return {
            'key': self.key,
            'type': self.type,
            'options': self.options,
        }