from .processors import BasePreprocessor, RuleBasedProcessor, ToBooleanRule, ToDatetimeRule
from .columns import ColumnSelector

rules_processors = {
    'to_bool': ToBooleanRule,
    'to_date': ToDatetimeRule
}

def parse_processor_def(conf: dict)->BasePreprocessor:
    proc_name = conf['name']
    if proc_name in rules_processors:
        columns_def = conf['columns']
        selector = ColumnSelector(columns_def)
        rule_class = rules_processors[proc_name]
        return RuleBasedProcessor(rule_class, selector)
    raise ValueError("Unknown processor name '{}'".format(proc_name))