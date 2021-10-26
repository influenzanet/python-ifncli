import unittest
from ifncli.surveys.influenzanet.expression import Expression
from ifncli.surveys.influenzanet.responses import RG_ROLES, RGROLES

from ifncli.surveys.influenzanet.survey import ROLE_RESPONSE_GROUP, Survey, SurveyGroupItem, SurveyItemComponent, SurveyItemGroupComponent, SurveyItemResponseComponent, SurveySingleItem

def create_surveys(name, questions, selection=None):
    survey = Survey()
    
    items = []
    for quid, q in questions.items():
        
        comps = []
        if 'options' in q:
            rg = SurveyItemResponseComponent('rg', role=q['type'])
            rg_items = []
            for k,o in q['options'].items():
                rgi = SurveyItemComponent(k, 'option')
                rg_items.append(rgi)
            comps.append(rg_items)
                
        if len(comps) > 0:
            components=SurveyItemGroupComponent('root','root', comps, Expression('sequential'))
        else: 
            components = None
        validations = None
        item = SurveySingleItem(quid, components, validations, type=None)
        items.append(item)
    survey['current'] = SurveyGroupItem(name, items, selection=selection)
    
    return survey

class TestChecker(unittest.TestCase):

    def test_expression(self):
        survey = create_surveys('weekly', {
            'Q1': {'type':RGROLES.SINGLE, 'options' : {'0': {}, '1':{}}},
            'Q2': {'type':RGROLES.SINGLE, 'options' : {'0': {}, '1':{}}},
        })
