from typing import  List, Optional

def parse_version(v:str):
    r = v.split('-')
    vv = []
    for idx, v in enumerate(r):
        try:
            item = int(v)
            vv.append(item)
        except Exception:
            raise ValueError("Unable to parse version in '{}' integer expected at position {}".format(v, idx))
    return SurveyVersion(vv)

class SurveyVersion:
    def __init__(self, items: list[int]):
        self.items = [int(x) for x in items]

    def __eq__(self, value):
        if not isinstance(value, SurveyVersion):
            raise ValueError("value must be an instance of `SurveyVersion`")
        return self.items == value.items
    
    def compare(self, value):
        if not isinstance(value, SurveyVersion):
            raise ValueError("value must be an instance of `SurveyVersion`")
        n = len(self.items)
        m = len(value.items)
        z = max(n, m)
        i = 0
        #print("Compare ", self, "<=>", value, " n=", n, " m=", m, " z=",z)
        #print(self.items, value.items)
        while(i < z):
            # Loop over maximum position, if an item is shorter infer 0 value for the position
            if i < n:
                x = self.items[i]
            else:
                x = 0
            if i < m:
                y = value.items[i]
            else:
                y = 0
            r = 0
            if x < y:
                r = -1
            if x > y:
                r = 1
            #print("i=",i, " x=", x, " y=", y, " r=", r)
            if r != 0:
                return r
            i += 1
        return 0

    def __gt__(self, value):
        comp = self.compare(value)
        return comp > 0
    
    def __lt__(self, value):
        comp = self.compare(value)
        return comp < 0
    
    def __ge__(self, value):
        comp = self.compare(value)
        return comp >= 0
    
    def __le__(self, value):
        comp = self.compare(value)
        return comp <= 0
    
    def __str__(self):
        return "<@{}>".format("-".join([ str(x) for x in self.items]))
    
class VersionSelectorRule:
    def is_version(self, version: SurveyVersion)->bool:
        raise NotImplementedError()

class VersionSelector(VersionSelectorRule):
    """
        Version selector define version selection criteria for a mapper rule
    """    

    def __init__(self, including_rules: list[VersionSelectorRule], excluding_rules: Optional[list[VersionSelectorRule]] = None):
        self.including_rules = including_rules
        self.excluding_rules = excluding_rules

    def is_version(self, version:str)->bool:
        v = parse_version(version)
        for r in self.excluding_rules:
            if r.is_version(v):
                return False
        for r in self.including_rules:
            if r.is_version(v):
                return True
        return False
    
    def __str__(self):
        return "Selector<In:{}, Exclude:{}>".format(self.including_rules, self.including_rules)

class VersionSelectorRange(VersionSelectorRule):
    """
        Range of version 
    """
    def __init__(self, min: Optional[SurveyVersion], max: Optional[SurveyVersion]):
        self.min = min
        self.max = max
    
    def is_version(self, version:SurveyVersion)->bool:
        in_range = True
        if self.min is not None:
            in_range = in_range and version >= self.min
            #print("Min", self.min, " =", in_range)
        if self.max is not None:
            in_range = in_range and version <= self.max
            #print("Max", self.max, " =", in_range)
        #print(self, version, " In range=", in_range)
        return in_range            

    def __str__(self):
        return "Range<{}:{}>".format(self.min, self.max)

class VersionSelectorEq(VersionSelectorRule):
    """
        Specific version
    """
    def __init__(self, candidate: SurveyVersion):
        self.candidate = candidate
    
    def is_version(self, version:SurveyVersion)->bool:
        return version == self.candidate
    
    def __str__(self):
        return "Eq<{}>".format(self.candidate)
    
class VersionSelectorIn(VersionSelectorRule):
    """
        Specific version list
    """
    def __init__(self, candidates: List[SurveyVersion]):
        self.candidates = set(candidates)
    
    def is_version(self, version:SurveyVersion)->bool:
        return version in self.candidates

    def __str__(self):
        return "In<{}>".format(",".join([str(x) for x in self.candidates]))
               



        
        

    