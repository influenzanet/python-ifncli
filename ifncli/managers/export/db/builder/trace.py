
from collections import UserDict

class DictWithOrigin(UserDict):
    """"
        Dictionnary like with data origin tracing.
        Each item is associated with an "origin" (any string you want)
    
        To set values with tracing use set_from, and merge_from instead of others methods
    """

    def __init__(self, values=None, /, values_origin=None, **kwargs):
        self.origins = {}
        if values is not None:
            if isinstance(values, DictWithOrigin):
                data = values.data.copy()
                self.origins = values.origins.copy()
                if values_origin is not None:
                    print("Warning `values_origin` cannot be used when passing DictWithOrigin as value")
                    values_origin = None
            else:
                data = values
        else:
            data = {}
        super().__init__(data, **kwargs)
        if values_origin is not None:
            for key in self.keys():
                self.origins[key] = values_origin

    def __setitem__(self, key, item):
        """
            If value is set directly using self[] operator or other "dict" way to set values
            Origin is canceled as it's not known any more
        """
        self.data[key] = item
        self.origins[key] = None

    def set_from(self, key, item, origin):
        self.data[key] = item
        self.origins[key] = origin

    def merge_from(self, values, origin=None, allow_none:bool=False):
        """
            Merge from is like update() keeping track of origin
            if allow_none is True, 
        """

        if isinstance(values, DictWithOrigin):
            if origin is not None:
                raise ValueError("Origin cannot be specified with DictWithOrigin")
            for key, item, item_origin in values.traced_items():
                if allow_none or item is not None:
                    self.set_from(key, item, item_origin)
        else:
            for key, item in values.items():
                if allow_none or item is not None:
                    self.set_from(key, item, origin)
        
    def origin(self, key):
        """
            Get origin of a value
        """
        return self.origins.get(key, None)

    def traced_items(self):
        """
            Get for each element a tuple of 3 elements : key, value and origin
        """
        
        return [ (key, item, self.origins.get(key, None)) for key, item in self.items()]

