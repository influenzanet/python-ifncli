from .model import VersionSelectorRule, VersionSelectorEq, VersionSelectorRange, parse_version
from .parser import *
import unittest


class TestSurveyVersion(unittest.TestCase):

    def apply(self, selector, candidates):
        #print("Selector ", selector)
        for version, result in candidates.items():
            v = parse_version(version)
            r = selector(v)
            print(v, result, r)
            self.assertEqual(r, result)

    def testEqual(self):
        v = parse_version('25-10-1') 
        self.apply(v.__eq__, {'25-10-1': True, '25-10-2': False, '26-2-10': False})
       
    def testRange(self):
        v = parse_version('25-0-0')
        self.apply(v.__gt__, {'25-10-1': False, '25-10-2': False, '25-2-2': False})
        self.apply(v.__lt__, {'25-10-1': True, '25-10-2': True, '25-2-2': True})
        
class TestModelCase(unittest.TestCase):

    def applySelector(self, selector:VersionSelectorRule, candidates):
        print("Selector ", selector)
        for version, result in candidates.items():
            v = parse_version(version)
            r = selector.is_version(v)
            print(v, result, r)
            self.assertEqual(r, result)        

    def testVersionEqSelector(self):
        r = VersionSelectorEq(parse_version('25-10-1'))
        self.applySelector(r, {'24-1-12': False, '25-10-2': False, '25-10-1': True})
        
    def testVersionSelectorRange(self):
        r = VersionSelectorRange(parse_version('25-0-0'), parse_version('25-12-99'))
        self.applySelector(r, {'24-1-12': False, '25-10-2': True, '25-10-1': True, '23-10-12': False, '25-2-2':True})
        
