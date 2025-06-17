
from .model import VersionSelector, VersionSelectorEq, VersionSelectorRange, VersionSelectorRule, SurveyVersion, parse_version

class ParserError(Exception):
    pass


class VersionSelectorParser:

    def __init__(self):
        self.including_rules: list[VersionSelectorRule] = []
        self.excluding_rules: list[VersionSelectorRule] = []

    def parse(self, conf):
        self.parse_selector(conf)
        return VersionSelector(self.including_rules, self.excluding_rules)

    def parse_selector(self, conf):
        if isinstance(conf, str):
            self.parse_str(conf)
        if isinstance(conf, list):
            self.parse_list(conf)

    def parse_str(self, conf:str):
        conf = conf.strip()
        if conf == '':
            return
        if ';' in conf:
            vv = conf.split(';')
            vv = [ v.strip() for v in vv]
            vv = [ v for v in vv if v != '']
            for v in vv:
                self.parse_item(v)
        else:
            self.parse_item(conf)
    
    def parse_list(self, conf:list):
        for index, vspec in enumerate(conf):
            try:
                self.parse_selector(vspec)
            except Exception as e:
                raise ParserError("Version spec {}".format(index)) from e
    
    def parse_item(self, spec:str):
        excluding = False
        spec = spec.strip()
        if spec == '':
            return
        if spec.startswith('!'):
            excluding = True
            spec = spec[1:]
        if ':' in spec:
            r = spec.split(':')
            if len(r) != 2:
                raise ParserError("Version spec range must have 2")
            v_min = r[0].strip()
            if v_min == '':
                v_min = None
            else:
                v_min = parse_version(v_min)
            v_max = r[1].strip()
            if v_max == '':
                v_max = None
            else:
                v_max = parse_version(v_max)
            selector = VersionSelectorRange(v_min, v_max)
        else:
            v = parse_version(spec)
            selector = VersionSelectorEq(v)
        if excluding:
            self.excluding_rules.append(selector)
        else:
            self.including_rules.append(selector)

