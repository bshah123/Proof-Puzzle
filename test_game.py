import unittest
from server import LEVELS, parse, simulate, source, verify

class GameTests(unittest.TestCase):
    def test_all_level_solutions(self):
        for level in LEVELS:
            with self.subTest(level=level['id']):
                moves=parse(level['solution'],level)
                states,error=simulate(level,moves)
                self.assertIsNone(error)
                self.assertEqual(states[-1]['board'],level['target'])
                checked=verify(source(level,moves))
                self.assertTrue(checked['verified'],checked)
    def test_illegal_moves_rejected_by_lean(self):
        cases=[(1,'.swap 0 3'),(3,'.swap 0 2'),(1,'.paint 0 .blue'),(1,'')]
        for idx,code in cases:
            with self.subTest(code=code):
                level=LEVELS[idx-1]
                checked=verify(source(level,parse(code,level)))
                self.assertTrue(checked['available'])
                self.assertFalse(checked['verified'])
                self.assertIn('decide',checked.get('diagnostics',''))
    def test_move_budget_and_code_injection(self):
        for code in ['.swap 0 1\n.swap 0 1','sorry','#eval IO.println "bad"','.swap 0 7','flipTop']:
            with self.assertRaises(ValueError): parse(code,LEVELS[0])
    def test_resource_and_lock_errors(self):
        for idx,code in [(1,'.paint 0 .blue'),(3,'.swap 0 2'),(1,'.swap 0 3')]:
            level=LEVELS[idx-1]
            self.assertIsNotNone(simulate(level,parse(code,level))[1])

if __name__=='__main__': unittest.main()
