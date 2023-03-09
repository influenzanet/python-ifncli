import unittest

from .utils import resolve_vars, bind_content, bind_vars

class TemplateParserTest(unittest.TestCase):

    def testResolveVars(self):
        
        r, p = resolve_vars(None)
        self.assertIsNone(r)
        
        vars = {
            'var1':'1',
            'var2': '2',
            'var3': '{=var1=}+{= var2 =}'
        }
        r, p = resolve_vars(vars)
        self.assertEqual(r['var3'], '1+2')      

    def testResolveCircularDep(self):

        def run_expect(data):
            ex = None
            try:
                r, p = resolve_vars(data)
            except Exception as e:
                ex = e
            self.assertIsInstance(ex, Exception)
            self.assertIn("Circular", str(ex))

        vars = {
            'v1': '1',
            'v2': '{=v2=}'
        } 
        run_expect(vars)
        vars = {
            'v1': 'toto {=v3=} blibli',
            'v2': 'blabla {=v1=}',
            'v3': '{=v2=}'
        }
    
    def testResolveUnknownVar(self):
        value = 'toto {=v3=} blibli'
        vars = {
            'v1': value,
        }
        r, p = resolve_vars(vars)
        self.assertEqual(r['v1'], value)
        self.assertEqual(len(p), 2)
        if len(p) > 0:
            self.assertIn("'v3' not found", p[0] )

    def testBindVars(self):

        # Test with no vars
        value = "my value is not transformed without variable"
        r, p = bind_vars(value, None)
        self.assertEqual(r, value)
        self.assertEqual(len(p), 0)

        vars = {
            'v1':'1',
            'v2':'2',
            'v3': '3'
        }

        # Test with nothing to replace
        r, p = bind_vars(value, vars)
        self.assertEqual(r, value)
        self.assertEqual(len(p), 0)

        # Test with some vars
        r, p = bind_vars('{=v1=}+{=v2=}*{=v3=}', vars)
        self.assertEqual('1+2*3', r)
        self.assertEqual(0, len(p))

        # Test with unknown var
        vars = {'v1': 'toto'}
        r, p = bind_vars('{=v1=} {= v2 =}', vars)
        self.assertEqual(1, len(p))
        self.assertIn("'v2' not found", p)
        
if __name__ == '__main__':
    TemplateParserTest.main(verbosity=2)
