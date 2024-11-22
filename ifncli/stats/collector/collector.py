## Base definition of collector

from typing import Dict, List, OrderedDict
from collections import OrderedDict


class StatResult:

    def __init__(self, type, label: str, values) -> None:
        self.type = type
        self.label = label
        self.values = values
    
    def show(self):
        print(self.label)
        if(isinstance(self.values, dict)):
           for name, value in self.values.items():
               print("  %s = %s" % (name, str(value)))
        else:
           print(self.values)

    def to_dict(self):
        return {
            'label': self.label,
            'type': self.type,
            'values': self.values
        }


class Collector(object):

    need_field = False

    def __init__(self, name):
        self.name = name

    def collect(self, data: Dict):
        """
        Collect statistics about data
        """
        raise NotImplementedError()

    def get_stats(self)->StatResult: 
        """
            get statistics results
        """
        raise NotImplementedError()

class FieldCollector(Collector):
    """
        Collect info about a field
    """
    need_field = True

    def __init__(self, name, field:str):
        super().__init__(name)
        self.field = field

class FieldCountCollector(Collector):
    """
        Count fields occurence in data
    """

    default_name = 'counts'

    def __init__(self, name: str):
        super().__init__(name)
        self.counts: Dict[int] = {}

    def collect(self, data: Dict):
        for name, _ in data.items():
           self.counts[name] = 1 + self.counts.get(name, 0)

    def get_stats(self):
        return StatResult('frequency', 'Field occurence frequency', self.counts)
        
