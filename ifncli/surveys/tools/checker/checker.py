from collections import OrderedDict
from ...influenzanet.expression import KNOWN_EXPRESSIONS, ExpressionType, find_expression_type
from ...influenzanet import Study, Survey, SurveyItem, SurveyItemComponent, Expression, OptionDictionnary, RGROLES
from ...context import Context

from typing import List, Optional,Dict

class CheckContext(dict):

    def __init__(self, parent=None, **kwargs):
        super(CheckContext, self).__init__(**kwargs)
        self.parent = parent

class Problem:
    DUPLICATE_KEY = 'dup_key'
    DUPLICATE_RESPONSE_KEY = 'dup_response_key'
    UNKNOWN_EXP = 'unknown_exp'

    def __init__(self, pb_type, value=None, ctx:CheckContext=None):
        self.type = pb_type
        self.value = value
        self.ctx = ctx

    def to_readable(self, ctx: Context):
        return {'type': self.type, 'value': self.value, 'ctx': self.ctx }

class SurveyChecker:

    def __init__(self):
        self.item_keys = OrderedDict()
        self.problems = []

    def check(self, survey: Survey):

        definition = survey.getCurrent()
    
        self.discover(definition)

        ctx = CheckContext(survey="current")
        self.check_item(definition, ctx)

        return self.problems

    def notify(self, pb_type, ctx:CheckContext, **kwargs):
        pb = Problem(pb_type, ctx=ctx, **kwargs)
        self.problems.append(pb)

    def discover(self, survey: SurveyItem):
        """
            Discover create data about survey to supports check
        """
        dd = survey.get_dictionnary()
        for item in dd:
            ctx = CheckContext(item=item.key)
            if item.key in self.item_keys:
                self.notify(Problem.DUPLICATE_KEY, ctx)
            else:
                self.item_keys[item.key] = item
            if item.options is not None:
                if item.type in [RGROLES.SINGLE, RGROLES.DROPDOWN, RGROLES.LIKERT, RGROLES.MULTIPLE]:
                    self.check_options(item.options, ctx)
                    
    def check_options(self, options:List[OptionDictionnary], parent:CheckContext):
        kk = dict()
        for o in options:
            if o.key in kk:
               ctx = CheckContext(parent=parent, key=o.key)
               self.notify(Problem.DUPLICATE_RESPONSE_KEY, ctx=ctx)
            else:
                kk[o.key] = True
        
    def check_item(self, surveyItem: SurveyItem, parent: CheckContext):
        if surveyItem.is_group():
            # GroupItem
            for item in surveyItem.items:
                self.check_item(item, parent=parent)
            
            if surveyItem.selection is not None:
                ctx = CheckContext(item=item.key, field="selection", parent=parent)
                self.check_expression(surveyItem.selection, ctx)
        else:
            # SingleItem
            if surveyItem.validations is not None:
                for index, validation in enumerate(surveyItem.validations):
                    ctx = CheckContext(parent=parent, item=surveyItem.key, field="validations", index=index)
                    self.check_expression(validation['rule'], ctx)
            ctx = CheckContext(parent=parent, item=surveyItem.key, field='components')
            self.check_component(surveyItem.components, ctx)
    
    def check_component(self, component:SurveyItemComponent, parent:CheckContext):
        fields = ['displayCondition','disabled']
        if component.is_group():
            for index, comp in enumerate(component.items):
                ctx = CheckContext(parent=parent, key=component.key, field="items", index=index)
                self.check_component(comp, ctx)
            fields.append('order')
        
        for field in fields:
            if hasattr(component, field) and getattr(component, field) is not None:
                ctx = CheckContext(parent=parent, key=component.key, field=field)
                self.check_expression(getattr(component, field), ctx)
        
        props = getattr(component, 'properties', None)
        if props is not None:
            for name, expr in props.items():
                ctx = CheckContext(parent=parent, key=component.key, field="properties", name=name)
                self.check_expression(expr, ctx)

    def check_expression(self, exp: Expression, ctx):
        if exp.is_scalar():
            return
        context = CheckContext(parent=ctx, name=exp.name)
        if exp.is_expression():
            has_params = len(exp.params) == 0
            exp_type = find_expression_type(exp.name)
            if exp_type is None:
                self.notify(Problem.UNKNOWN_EXP, context)
            else:
                if expType.has_params() and has_params:
                    self.check_expression_refs(exp, exp_type, context)
        if not has_params:
            return            

        for p in exp.params:
            if p.is_expression():
                self.check_expression(p, context)

    def check_expression_refs(self, exp:Expression, exp_type:ExpressionType, ctx: CheckContext):
        for index, p in enumerate(exp_type.params):
            if isinstance(p, RefArg):
                context = CheckContext(parent=ctx, param=index, exp=exp.name)
                self.check_reference(p, )

        
        
    