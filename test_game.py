import json, os, subprocess, tempfile, unittest
from pathlib import Path
from server import LEVELS, LEAN, RULES, ROOT, parse, source, verify, lean_board

NODE = 'node'
def lvl(i): return LEVELS[i - 1]

def node(script, payload):
    r = subprocess.run([NODE, '-e', script], input=json.dumps(payload), capture_output=True, text=True, timeout=60, cwd=ROOT)
    if r.returncode: raise AssertionError(r.stderr)
    return json.loads(r.stdout)

def lean(src, timeout=120):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'Check.lean'; path.write_text(src)
        return subprocess.run([LEAN, str(path)], capture_output=True, text=True, timeout=timeout)

class LeanProofs(unittest.TestCase):
    def test_every_level_solution_is_accepted(self):
        for level in LEVELS:
            with self.subTest(level=level['id']):
                r = verify(level, parse(level['solution']['helpers'], level['solution']['proof'], level))
                self.assertTrue(r['verified'], r)
                self.assertNotIn('sorryAx', r['axioms'])

    def test_downloaded_file_runs_with_plain_lean(self):
        level = lvl(7); s = level['solution']
        r = lean(source(level, parse(s['helpers'], s['proof'], level), standalone=True)[0])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("'level_7_solved' depends on axioms: [propext, Quot.sound]", r.stdout)

    def test_rejections_point_at_the_right_line(self):
        cases = [(1, '', 'swap 0 3', ('proof', 1, 'illegal')),            # diagonal
                 (1, '', 'swap 0 1', ('finish', None, 'mismatch')),       # legal but unfinished
                 (1, '', 'paint 0 blue\nswap 2 3', ('proof', 1, 'illegal')),  # no paint on level 1
                 (3, '', 'swap 0 1\nswap 2 3', ('proof', 2, 'illegal')),  # locked cell
                 (4, '', '-- hi\n\nrotate 9', ('proof', 3, 'illegal')),   # off the board
                 (6, 'macro "bad" : tactic => `(tactic| (swap 0 1; swap 2 3))', 'rotate 4\nbad', ('proof', 2, 'illegal'))]  # 2,3 differ by one but wrap rows
        for idx, helpers, code, expected in cases:
            with self.subTest(code=code):
                r = verify(lvl(idx), parse(helpers, code, lvl(idx)))
                self.assertFalse(r['verified'])
                self.assertEqual((r['errors'][0]['section'], r['errors'][0]['line'], r['errors'][0]['kind']), expected)

    def test_move_budget_is_enforced_by_lean_not_just_python(self):
        # Bypass the Python budget check: three legal swaps on a two-move level.
        level = dict(lvl(1)); level['moves'] = 9
        parsed = parse('', 'swap 0 1\nswap 0 1\nswap 0 1', level)
        r = verify(lvl(1), parsed)
        self.assertEqual(r['errors'][0]['line'], 3)

class Parser(unittest.TestCase):
    def test_injection_and_grammar(self):
        bad = ['sorry', '#eval IO.println "bad"', 'swap 0 1 <;> sorry', 'exact Reaches.finish (by native_decide)',
               'swap 0 123', 'shift', 'paint 0 red', 'decide', 'swap 0 1; swap 0 1']
        for code in bad:
            with self.subTest(code=code), self.assertRaises(ValueError): parse('', code, lvl(6))

    def test_helper_rules(self):
        bad_helpers = ['macro "sorry" : tactic => `(tactic| swap 0 1)', 'macro "ab" : tactic => `(tactic| swap 0 1)',
                       'macro "loop" : tactic => `(tactic| loop)', 'macro "x1y" : tactic => `(tactic| (sorry))',
                       'macro "aaa" : tactic => `(tactic| swap 0 1)\nmacro "aaa" : tactic => `(tactic| swap 0 1)',
                       'macro "evil" : tactic => `(tactic| (swap 0 1); sorry)']
        for h in bad_helpers:
            with self.subTest(h=h), self.assertRaises(ValueError): parse(h, '', lvl(6))
        with self.assertRaises(ValueError): parse('macro "ok1" : tactic => `(tactic| swap 0 1)', '', lvl(1))  # helpers locked early
        p = parse('macro "one" : tactic => `(tactic| swap 0 1)\nmacro "two" : tactic => `(tactic| (one; one))', 'two', lvl(6))
        self.assertEqual(p['total'], 2)

    def test_limits(self):
        with self.assertRaises(ValueError): parse('', 'swap 0 1\nswap 1 2\nrotate 4\nrotate 4', lvl(6))  # 4 lines > 3
        with self.assertRaises(ValueError): parse('', 'swap 0 1\nswap 0 1\nswap 0 1', lvl(1))             # 3 moves > 2

    def test_python_and_browser_parsers_agree(self):
        corpus = [('', 'swap 0 1'), ('', 'swap  0   1 -- note'), ('', 'paint 3 blue'), ('', 'rotate 12'), ('', 'sorry'),
                  ('', 'swap 0'), ('', 'Swap 0 1'), ('', 'unknownName'), ('', 'paint 1 red'), ('', '#eval 1'),
                  ('macro "abc" : tactic => `(tactic| (swap 0 1; rotate 4))', 'abc\nabc'),
                  ('macro "abc" : tactic => `(tactic| rotate 4)', 'abc'), ('macro "by" : tactic => `(tactic| rotate 4)', ''),
                  ('macro "abc" : tactic => `(tactic| (rotate 4;))', ''), ('macro "abc" : tactic => `(tactic| abc)', ''),
                  ('macro "abc" : tactic => `(tactic| (rotate 4))\nmacro "dbl" : tactic => `(tactic| (abc; abc))', 'dbl'),
                  ('', 'swap 0 1\nswap 1 2\nrotate 4\nrotate 4'), ('macro "abc" : tactic => `(tactic| swap 0 1)', 'swap 0 1 abc')]
        js = node("""const R=require('./web/rules.js');const {level,corpus}=JSON.parse(require('fs').readFileSync(0,'utf8'));
                     console.log(JSON.stringify(corpus.map(([h,p])=>R.parseProgram(h,p,level).errors.length===0)));""",
                  dict(level=lvl(6), corpus=corpus))
        for (h, p), ok in zip(corpus, js):
            try: parse(h, p, lvl(6)); py = True
            except ValueError: py = False
            with self.subTest(helpers=h, proof=p): self.assertEqual(py, ok)

class Differential(unittest.TestCase):
    """rules.js must agree with Lean's `run` on every sequence of up to two moves."""
    CONFIGS = [dict(width=2, locked=[2], start=lvl(3)['start'], target=lvl(3)['target'], paints=1, moves=2, cells=5),
               dict(width=2, locked=[], start=[['gold', 3], ['blue', 1], ['mint', 0], ['coral', 2]], target=lvl(1)['target'], paints=0, moves=1, cells=5),
               dict(width=3, locked=[4], start=[[c, i % 4] for i, c in enumerate(['coral', 'blue', 'gold', 'mint', 'mint', 'blue', 'gold', 'coral', 'blue'])],
                    target=lvl(7)['target'], paints=1, moves=2, cells=10)]

    def moves(self, cells):
        out = [('swap', a, b) for a in range(cells) for b in range(cells)]
        out += [('paint', a, c) for a in range(cells) for c in ('coral', 'gold')] + [('rotate', a) for a in range(cells)]
        return out

    def test_browser_simulator_matches_lean(self):
        for cfg in self.CONFIGS:
            with self.subTest(width=cfg['width'], locked=cfg['locked'], moves=cfg['moves']):
                ms = self.moves(cfg['cells'])
                lean_moves = ', '.join(f'.swap {m[1]} {m[2]}' if m[0] == 'swap' else f'.paint {m[1]} .{m[2]}' if m[0] == 'paint' else f'.rotate {m[1]}' for m in ms)
                src = RULES.read_text() + f'''
open ProofPuzzle
def L : Level := {{ width := {cfg['width']}, locked := {cfg['locked']}, target := {lean_board(cfg['target'])} }}
def s0 : State := {{ board := {lean_board(cfg['start'])}, paints := {cfg['paints']}, moves := {cfg['moves']} }}
def ms : List Move := [{lean_moves}]
def letter : Color → String | .coral => "c" | .blue => "b" | .mint => "m" | .gold => "g"
def enc : Option State → String
  | none => "none"
  | some s => String.join (s.board.map fun b => letter b.color ++ toString b.facing) ++ s!"/{{s.paints}}/{{s.moves}}"
def seqs : List (List Move) := ms.map (fun a => [a]) ++ (ms.map fun a => ms.map fun b => [a, b]).foldr (· ++ ·) []
#eval IO.println (String.intercalate "\\n" (seqs.map fun q => enc (run L s0 q)))
'''
                r = lean(src, timeout=300)
                self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
                lean_out = r.stdout.strip().split('\n')
                js_out = node("""const R=require('./web/rules.js');const {cfg,ms}=JSON.parse(require('fs').readFileSync(0,'utf8'));
                  const level={...cfg};const mv=m=>m[0]==='swap'?{kind:'swap',a:m[1],b:m[2]}:m[0]==='paint'?{kind:'paint',a:m[1],color:m[2]}:{kind:'rotate',a:m[1]};
                  const run=seq=>{let s=R.initial(level);for(const m of seq){const r=R.step(level,s,mv(m));if(r.error)return null;s=r.state;}return s;};
                  const seqs=ms.map(a=>[a]).concat(ms.flatMap(a=>ms.map(b=>[a,b])));
                  console.log(JSON.stringify(seqs.map(q=>R.encode(run(q)))));""", dict(cfg=cfg, ms=ms))
                self.assertEqual(len(lean_out), len(js_out))
                mismatches = [(i, a, b) for i, (a, b) in enumerate(zip(lean_out, js_out)) if a != b]
                self.assertFalse(mismatches, mismatches[:5])

if __name__ == '__main__': unittest.main()
