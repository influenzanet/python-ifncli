from collections import OrderedDict
import logging
from ...influenzanet.expression.types import ARG_ITEM_KEY, ARG_SURVEYKEY, Arg, EnumerationReference, KeyReference, UnknownExpressionType
from ...influenzanet.expression import KNOWN_EXPRESSIONS, ExpressionType, find_expression_type
from ...influenzanet.expression.library import load_library

from ...influenzanet import Study, Survey, SurveyItem, SurveyItemComponent, Expression, OptionDictionnary, RGROLES
from ...context import Context

from typing import List, Optional,Dict

logger = logging.getLogger(__name__)

def get_exp_param(exp:Expression, p:Arg):
    pos = p.pos
    if len(exp.params)-1 < pos:
        return None
    return exp.params[pos]

class CheckContext(dict):

    def __init__(self, parent=None, **kwargs):
        super(CheckContext, self).__init__(**kwargs)
        self.parent = parent

class Problem:
    DUPLICATE_KEY = 'dup_key'
    DUPLICATE_RESPONSE_KEY = 'dup_response_key'
    UNKNOWN_EXP = 'unknown_exp'
    UNCHECKABLE = 'uncheckable'
    UNKNOWN_REF = 'unknown_ref'

    def __init__(self, pb_type, value=None, ctx:CheckContext=None):
        self.type = pb_type
        self.value = value
        self.ctx = ctx

    def to_readable(self, ctx: Context):
        return {'type': self.type, 'value': self.value, 'ctx': self.ctx }

class SurveyChecker:

    LOADED = False

    def __init__(self):

        if not self.LOADED:
            load_library()
            self.LOADED = True
        self.item_keys = OrderedDict()
        self.known_surveys = set()
        self.problems = []

    def check(self, survey: Survey):
        
        definition = survey.getCurrent()
    
        self.known_surveys.add(definition.key)

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
            logger.debug("check option %s" % (o.key))
            if o.key in kk:
               ctx = CheckContext(parent=parent, key=o.key)
               self.notify(Problem.DUPLICATE_RESPONSE_KEY, ctx=ctx)
            else:
                kk[o.key] = True
        
    def check_item(self, surveyItem: SurveyItem, parent: CheckContext):
        logger.debug("check item %s" % (surveyItem.key))
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
        logger.debug("check component '%s'" % (component.key))
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

    def check_expression(self, exp: Expression, parent:CheckContext):
        logger.debug("check expr %s" % (exp))
        if exp.is_scalar():
            return
        context = CheckContext(parent=parent, name=exp.name)
        if exp.is_expression():
            has_params = len(exp.params) > 0
            exp_type = find_expression_type(exp.name)
            if exp_type is None or isinstance(exp_type, UnknownExpressionType):
                self.notify(Problem.UNKNOWN_EXP, context)
            else:
                if exp_type.has_refs() and has_params:
                    self.check_expression_refs(exp, exp_type, context)
            if not has_params:
                return
            for p in exp.params:
                if p.is_expression():
                    self.check_expression(p, context)

    def check_expression_refs(self, exp:Expression, exp_type:ExpressionType, parent: CheckContext):
       for ref in exp_type.references:
           logger.debug("check ref %s" % (ref))
           if isinstance(ref, EnumerationReference):
               self.check_enumeration_ref(exp, ref, parent)
           if isinstance(ref, KeyReference):
               self.check_key_reference(exp, ref, parent)

    def check_enumeration_ref(self, exp:Expression, ref:EnumerationReference, parent: CheckContext):
        ctx = CheckContext(parent=parent, role=ref.role, param=ref.param)
        p = get_exp_param(exp, ref.param)
        if p is None:
            return
        if isinstance(p, Expression):
            self.notify(Problem.UNCHECKABLE, ctx)
            return
        # It's a scalar
        if not p.value in ref.values:
            self.notify(Problem.UNEXPECTED_VALUE, ctx)

    def check_key_reference(self, exp:Expression, ref:KeyReference, parent: CheckContext):
        ctx = CheckContext(parent=parent, role=ref.role, param=ref.param)
        p = get_exp_param(exp, ref.param)
        if p is None:
            return
        if isinstance(p, Expression):
            self.notify(Problem.UNCHECKABLE, ctx)
            return
        value = str(p.value)
        if ref.role == ARG_ITEM_KEY:
            if not value in self.item_keys:
                self.notify(Problem.UNKNOWN_REF, CheckContext(parent=ctx, value=value))
            logger.debug("Item key '%s' found" % value)
            return
        if ref.role == ARG_SURVEYKEY:
            if not value in self.known_surveys:
                self.notify(Problem.UNKNOWN_REF, CheckContext(parent=ctx, value=value))
            logger.debug("Survey key '%s' found" % value)
        

                


                   

        
        
    