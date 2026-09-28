from typing import Dict
from .collector import FieldCollector, StatResult
import math
try:
    from tdigest import TDigest
    tdigest_available = True
except ModuleNotFoundError:
    tdigest_available = False

class CategoricalCollector(FieldCollector):

    def __init__(self, name, field: str):
        super().__init__(name, field)
        self.counts:Dict[int] = {}
    
    def collect(self, data: Dict):
        if self.field not in data:
            return
        def incr(name):
            self.counts[name] = 1 + self.counts.get(name, 0)
        value = data[self.field]
        if value is None:
            incr('_NA_')
        else:
            incr(value)
    
    def get_stats(self):
        return StatResult('frequency', "Values frequency of field %s" % (self.field), self.counts)

        
class SummaryCollector(FieldCollector):

    def __init__(self, name, field: str):
        super().__init__(name, field)
        self.n: int = 0
        self.sum: float = 0
        self.sum_square: float = 0
        self.min: float = float('nan')
        self.max: float = float('nan')
        self.nan: int = 0
        self.invalid: int = 0

    def collect(self, data: Dict):
        if self.field not in data:
            return
        value = data[self.field]
        v: float
        try:
            v = float(value)
        except:
            self.invalid += 1
            return
        if math.isnan(v):
            self.nan += 1
            return
        self.n += 1
        self.sum = v + self.sum
        self.sum_square = v * v + self.sum_square
        if math.isnan(self.min) or self.min > v:
            self.min = v
        if math.isnan(self.max) or self.max < v:
            self.max = v
    
    def get_stats(self):
        mean = self.sum / self.n
        variance = (self.sum_square / self.n) - mean ** 2
        values = {
            "n": self.n,
            "mean": mean,
            "var": variance,
            "min": self.min,
            "max": self.max,
            "nan": self.nan,
            "invalid": self.invalid,
        }
        return StatResult('summary', "Summary of field '%s'" % (self.field), values)