import unittest

from .processors import RemovePrefixRule, RenameRegexpRule, RenameFixedColumnRule
from .columns import ColumnSelector, FixedColumnSelector, PatternColumnSelector
class TestRenameProcessor(unittest.TestCase):

    def testRemovePrefixRule(self):
        rule = RemovePrefixRule('|')
        self.assertEqual(rule.apply('intake.main.Q1'), 'Q1')
        self.assertEqual(rule.apply('intake.main.Q1|1'), 'Q1|1')

    def testRenameRegexpRule(self):
        rule = RenameRegexpRule('|', r'<$>mat\.row(\d+)\.col(\d+)', r"<$>multi_row\1_col\2")
        self.assertEqual(rule.apply("Q2|mat.row1.col2"), "Q2|multi_row1_col2")
        rule = RenameRegexpRule('|', r"<$>likert_(\d+)", r"<$>lk_\1")
        self.assertEqual(rule.apply('Q10|likert_10'), 'Q10|lk_10')

    def testRenameFixedColumnRule(self):
        rule = RenameFixedColumnRule({'Q12':'Q23b', 'Q34':'Q26'})
        self.assertEqual(rule.apply('Q1'), "Q1")
        self.assertEqual(rule.apply('Q12'), "Q23b")
        self.assertEqual(rule.apply('Q34'), "Q26")
        

class TestColumnSelector(unittest.TestCase):
    def testFixedColumnSelector(self):
        sel = FixedColumnSelector(['Q12', 'Q15', 'intake.main.Q2'])
        self.assertEqual(list(sel.select(['Q2','Q15'])), ['Q15'])
        self.assertEqual(list(sel.select(['Q12'])), ['Q12'])

    def testPatternColumnSelector(self):
        sel = PatternColumnSelector(['*.Q2','Q10*'], 'glob')
        self.assertEqual(list(sel.select(['intake.main.Q2','Q15'])), ['intake.main.Q2'])
        self.assertEqual(list(sel.select(['Q2','Q10c','Q10d','Q10_2'])), ['Q10c','Q10d','Q10_2'])