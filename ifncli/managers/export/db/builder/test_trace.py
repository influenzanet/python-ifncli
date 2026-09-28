from .trace import DictWithOrigin

import unittest

class TestTraceDictionnary(unittest.TestCase):

    def test_init_origin(self):
        prev = {"toto": True, "titi": 12}
        d = DictWithOrigin(prev, values_origin="me")
        self.assertEqual(d['toto'], True)
        self.assertEqual(d['titi'], 12)
        self.assertEqual(d.origin('toto'), 'me')
        self.assertEqual(d.origin('titi'), 'me')
        self.assertIsNone(d.origin('tutu'))

    def test_legacy_origin(self):
        prev = {"toto": True, "titi": 12}
        d = DictWithOrigin(prev, values_origin="me")
        d['titi'] = 'another_value'
        self.assertEqual(d.origin('toto'), 'me')
        self.assertEqual(d['titi'], 'another_value')
        self.assertIsNone(d.origin('titi'))
       # print(d.traced_items())

    def test_merge_from(self):
        print("merge_from")
        prev = {"toto": True, "titi": 12}
        d = DictWithOrigin(prev, values_origin="me")
        
        self.assertEqual(d.origin('toto'), 'me')
        self.assertEqual(d["toto"], True)
        
        u = {"toto": False, "titi":None}
        d.merge_from(u, origin="other", allow_none=False)
        self.assertEqual(d.origin('toto'), 'other')
        self.assertEqual(d["toto"], False)
        self.assertEqual(d["titi"], 12)
        
        z = {"titi":None}
        d.merge_from(u, origin="z", allow_none=True)
        self.assertIsNone(d["titi"])
        self.assertEqual(d.origin('titi'), 'z')

    def test_traced_items(self):
        prev = {"toto": True, "titi": 12}
        d = DictWithOrigin(prev, values_origin="me")
        #print("Values:")
        #for key, value, origin in d.traced_items():
        #    print(f"- {key}, {value}, {origin}")
        
        
