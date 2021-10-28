"""
dictionary model


dictionary is a simplified view of the Influenzanet survey model centered on data collection and encoding

It's used to export as a simple structure (into 'readable' format) or to compare with the standard

"""
from typing import List,Optional

class OptionDictionnary:

    def __init__(self, key:str, role:str, item_key:str, rg_item: str, obj):
        self.key = key
        self.role = role
        self.item_key = item_key
        self.rg_item = rg_item
        self._obj = obj
    
    def __repr__(self):
        return self.to_readable().__repr__()

    def to_readable(self, ctx=None):
        """
            To readable representation (simple structure serializable as simple json or yaml)
        """
        return {
            'key': self.key, 
            'role': self.role, 
            'item_key': self.item_key,
            'rg_item': self.rg_item
        }
    
    def get_component(self):
        return self._obj

class ItemDictionnary:
    """
        Item dictionnary implements a simple question model from the Survey model, centered on data collection
        It only embeds information about data collection and encoding
    """
    def __init__(self, key:str, type:str, options:Optional[List[OptionDictionnary]], parent_key:str, obj):
        self.key = key
        self.type = type
        self.options = options
        self.parent_key = parent_key # Parent prefix
        self.rg_key = None # Response group key
        self._obj = obj

    def __repr__(self):
        return {'key': self.key, 'type': self.type}.__repr__()

    def to_readable(self, ctx=None):
        """
            Transforms the object into readable format
        """
        return {
            'key': self.key,
            'type': self.type,
            'options': self.options,
        }

    def get_survey_item(self):
        return self._obj