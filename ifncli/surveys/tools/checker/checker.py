from collections import OrderedDict
import logging
from inspect import getframeinfo, stack

from ifncli.surveys.influenzanet.translatable import TranslatableList


from ...influenzanet.survey import SurveyPath
from ...influenzanet.expression.types import ARG_ITEM_KEY, ARG_SURVEYKEY, Arg, CompositeArgument, EnumerationReference, ItemPathReference, KeyReference, UnknownExpressionType
from ...influenzanet.expression import KNOWN_EXPRESSIONS, ExpressionType, find_expression_type
from ...influenzanet.expression.library import load_library

from ...influenzanet import Study, Survey, SurveyItem, SurveyItemComponent, Expression, OptionDictionnary, RGROLES
from ...context import Context

from typing import List, Optional,Dict

logger = logging.getLogger(__name__)

def get_arg_value(arg:Arg, exp:Expression):
    if len(exp.params)-1 < arg.pos:
        return None
    return exp.params[arg.pos]

class CheckContext(dict):

    def __init__(self, parent=None, **kwargs):
        super(CheckContext, self).__init__(**kwargs)
        self.parent = parent
        self.caller = getframeinfo(stack()[1][0])
    
    def to_readable(self, ctx):
        """
            Create a readable form of context as a list (parents first) of key values
        """
        pp = []
        self.parents(pp)
        d = []
        pp.reverse()
        for p in pp:
            kw = []
            for k,v in p.items():
                kw.append("%s=%s" % (k,v))
            line = "%s at %d" % (','.join(kw), p.caller.lineno)
            d.append(line)
        return d

    def parents(self, stack:List):
        """
            Walk up into parents hierarchy
        """
        stack.append(self)
        if self.parent is not None:
            self.parent.parents(stack)

class Problem:
    """
        Describe a problem
    """
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
        d = {'type': self.type, }
        if self.value is not None:
            d['value'] = self.value
        d['context'] = self.ctx
        return d

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

    def notify(self, pb_type, ctx:CheckContext, value=None):
        pb = Problem(pb_type, ctx=ctx, value=value)
        self.problems.append(pb)

    def discover(self, survey: SurveyItem):
        """
            Discover create data about survey to supports check of unicity of keys
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
            logger.debug("check component field '%s' of '%s'" % (field, component.key))
            if hasattr(component, field) and getattr(component, field) is not None:
                ctx = CheckContext(parent=parent, key=component.key, field=field)
                self.check_expression(getattr(component, field), ctx)
        
        props = getattr(component, 'properties', None)
        if props is not None:
            for name, expr in props.items():
                logger.debug("check component prop '%s' of '%s'" % (name, component.key))
                ctx = CheckContext(parent=parent, key=component.key, field="properties", name=name)
                self.check_expression(expr, ctx)

        tt = ['content','description']
        for field in tt:
            if hasattr(component, field):
                logger.debug("check component field '%s' of '%s'" % (field, component.key))
                ctx = CheckContext(parent=parent, field=field)
                self.check_localized(getattr(component, field), parent=ctx)

    def check_localized(self, localized, parent: CheckContext):
        if isinstance(localized, TranslatableList):
            translates = localized.get_translates()
        else:
            translates = [localized]
        for t in translates:
            for index, part in enumerate(t.get_parts()):
                if isinstance(part, Expression):
                    ctx = CheckContext(parent=parent, index=index, code=t.get_code())
                    self.check_expression(part, ctx)

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
           if isinstance(ref, EnumerationReference):
               self.check_enumeration_ref(exp, ref, parent)
           if isinstance(ref, KeyReference):
               self.check_key_reference(exp, ref, parent)
           if isinstance(ref, ItemPathReference):
               self.check_path_reference(exp, ref, parent)

    def check_enumeration_ref(self, exp:Expression, ref:EnumerationReference, parent: CheckContext):
        logger.debug("check enumeration %s" % (ref))
        ctx = CheckContext(parent=parent, role=ref.role, param=ref.param)
        p = get_arg_value(ref.param, exp)
        if p is None:
            return
        if isinstance(p, Expression):
            self.notify(Problem.UNCHECKABLE, ctx)
            return
        # It's a scalar
        if not p.value in ref.values:
            self.notify(Problem.UNEXPECTED_VALUE, ctx)

    def check_key_reference(self, exp:Expression, ref:KeyReference, parent: CheckContext):
        logger.debug("check key %s in %s" % (ref, exp))
        ctx = CheckContext(parent=parent, role=ref.role, param=ref.param)
        p = get_arg_value(ref.param, exp)
        if p is None:
            return
        if isinstance(p, Expression):
            self.notify(Problem.UNCHECKABLE, ctx)
            return
        value = str(p.value)
        if ref.role == ARG_ITEM_KEY:

            if value =="this" and ref.param.allow_this:
                logger.debug("Item key is 'this', skipping")
                return

            if not value in self.item_keys:
                self.notify(Problem.UNKNOWN_REF, CheckContext(parent=ctx, value=value))
            logger.debug("Item key '%s' found" % value)
            return
        if ref.role == ARG_SURVEYKEY:
            if not value in self.known_surveys:
                self.notify(Problem.UNKNOWN_REF, CheckContext(parent=ctx, value=value))
            logger.debug("Survey key '%s' found" % value)
        
    def check_path_reference(self, exp:Expression, ref:ItemPathReference, parent: CheckContext):
        logger.debug("Check path %s in %s" % (ref, exp))
        item_key = get_arg_value(ref.item_key, exp)
        
        if item_key is None:
            logger.debug("Item %s not found %s" % (item_key))
            # Cannot check
            return
        
        ctx = CheckContext(parent=parent, param=ref.item_key)
        if isinstance(item_key, Expression):
            self.notify(Problem.UNCHECKABLE, ctx)
            return

        item_key = str(item_key)
        
        if item_key in self.item_keys:
            item = self.item_keys[item_key].get_survey_item()
        else:
            logger.debug("Unable to find item '%s'" % (item_key))
            self.notify(Problem.UNKNOWN_REF, ctx, value=item_key)
            # Should have been already notified by the argument check ?
            return

        args = []

        if isinstance(ref.path, CompositeArgument):
            args = ref.path.args
        else:
            args = [ref.path]
        pp = []
        
        for index,arg in enumerate(args):
            p = get_arg_value(arg, exp)
            if p is None:
                logger.debug("Path %d  %s not found" % (index, arg))
            if isinstance(p, Expression):
                ctx = CheckContext(parent=parent, param=index)
                self.notify(Problem.UNCHECKABLE, ctx)
                return
            pp.append(str(p))

        if len(pp) == 0:
            logger.debug("No path in expression")

        # Currently consider all path segments doesnt contains '.' as it's path separator (SurveyItem keys are an exception)
        path = SurveyPath(pp)
        obj = item.get_in_path(path)

        p = '/'.join(path.traversed)
        if obj is None:
            self.notify(Problem.UNKNOWN_REF, parent, value=p)
            return
        logger.debug("Item path found %s in %s" % (p, item_key))



            
               
                


                   

        
        
    