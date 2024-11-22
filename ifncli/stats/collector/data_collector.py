

from typing import Dict, List, OrderedDict
from collections import OrderedDict

from .collector import Collector, StatResult

class DataCollector:

    def __init__(self):
        self.collectors: Dict[str, Collector] = OrderedDict()

    def register(self, *newcollectors: Collector):
        """
            Register collectors
        """
        for collector in newcollectors:
            name = collector.name
            if name in self.collectors:
                raise ValueError("Collector '%s' is already registered" % (name))
            self.collectors[name] = collector

    def collect(self, data: Dict):
        for collector in self.collectors.values():
            collector.collect(data)

    def get_stats(self):
        stats = {}
        for name, collector in self.collectors.items():
            stats[name] = collector.get_stats()
        return Results(stats)
    
class Results:

    def __init__(self, stats: Dict[str, StatResult]) -> None:
        self.stats = stats

    def __iter__(self):
        return self.stats
    
    def show(self):
        for name, r in self.stats.items():
            print(name," :")
            r.show()
    
    def to_dict(self):
        d = {}
        for name, r in self.stats.items():
            d[name] = r.to_dict()
        return d
