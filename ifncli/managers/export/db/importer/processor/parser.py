from .processors import BasePreprocessor, RuleBasedProcessor, ToBooleanRule, ToDatetimeRule, RenameRegexpRule, RenameFixedColumnRule,RenamingProcessor
from .columns import ColumnSelector

rules_processors = {
    'to_bool': ToBooleanRule,
    'to_date': ToDatetimeRule,
}

class ProcessorParserSpec:

    def __init__(self, separator:str):
        self.separator = separator

    def parse(self, conf: dict)->BasePreprocessor:
        proc_name = conf['name']
        if proc_name in rules_processors:
            columns_def = conf['columns']
            selector = ColumnSelector(columns_def)
            rule_class = rules_processors[proc_name]
            return RuleBasedProcessor(rule_class, selector)
        if proc_name == 'rename':
            rules_def = conf.get('rules')
            excluded = conf.get('excluded')
            if rules_def is None:
                raise ValueError("Processor rename must have a 'rules' entry")
            if not isinstance(rules_def, list):
                raise ValueError("Processor rename 'rules' entry must be a list")
            rules = []
            for index, rule_def in enumerate(rules_def):
                try:
                    rr = self.parse_rename_rule(rule_def)
                    rules.extend(rr)
                except ValueError as e:
                    raise ValueError("In rename rules at rule {} : {}".format(index, e)) from e
            return RenamingProcessor(rules, [])
        raise ValueError("Unknown processor name '{}'".format(proc_name))

    def parse_rename_rule(self, rule_def):
        rules = []
        if 'regex' in rule_def:
            regexp = rule_def['regex']
            if not isinstance(regexp, dict):
                raise ValueError("'regex' entry must be a dictionnary with pattern:replace")
            for pattern, replace in regexp.items():
                rule = RenameRegexpRule(self.separator, pattern, replace)
                rules.append(rule)
        if 'fixed' in rule_def:
            fixed = rule_def['fixed']
            if not isinstance(fixed, dict):
                raise ValueError("'fixed' entry must be a dictionnary with old_name:new_name")
            rule = RenameFixedColumnRule(fixed)
            rules.append(rule)
        if len(rules) == 0:
            raise ValueError("No known renamed rule has been found")
        return rules
        