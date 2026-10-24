"""Local-only Proof Puzzle server. Only an allowlisted tactic grammar reaches Lean."""
import hashlib, json, os, re, subprocess, tempfile, threading
from collections import OrderedDict
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
TOOLCHAIN = Path.home() / '.elan/toolchains/leanprover--lean4---v4.19.0'
LEAN = str(TOOLCHAIN / 'bin/lean')
RULES = ROOT / 'lean/ProofPuzzle/Rules.lean'
BUILD = ROOT / 'build'
OLEAN = BUILD / 'ProofPuzzle/Rules.olean'
PORT = 8765
GATE = threading.Semaphore(2)
BUILD_LOCK = threading.Lock()
CACHE, CACHE_LOCK, CACHE_SIZE = OrderedDict(), threading.Lock(), 256
COLORS = ('coral', 'blue', 'mint', 'gold')
ALLOWED_AXIOMS = {'propext', 'Quot.sound', 'Classical.choice'}
MAX_HELPERS, MAX_HELPER_BODY = 4, 8

def blocks(*spec):
    """'coral' or ('coral', facing) → [color, facing] pairs (facing in quarter turns)."""
    return [[b, 0] if isinstance(b, str) else list(b) for b in spec]

C, B, M, G = COLORS
LEVELS = [
 dict(id=1, short='First moves', name='Two small trades', concept='Your first proof', width=2,
      description='Each row is in the wrong order. Two swaps, one per line, and Lean checks every step.',
      start=blocks(C,B,M,G), target=blocks(B,C,G,M), locked=[], paints=0, moves=2,
      hints=['A swap trades two tiles that share an edge. Each row needs one trade.', 'swap 0 1, then swap 2 3.'],
      starter='-- One move per line. Try: swap 0 1\n', solution=dict(helpers='', proof='swap 0 1\nswap 2 3')),
 dict(id=2, short='Composition', name='Around the corner', concept='Order matters', width=2,
      description='Two swaps again, but now the first move changes what the second one picks up.',
      start=blocks(C,B,M,G), target=blocks(B,G,M,C), locked=[], paints=0, moves=2,
      hints=['Coral has to travel two cells. Move it one hop at a time.', 'swap 0 1, then swap 1 3.'],
      starter='-- Every line is a move\n', solution=dict(helpers='', proof='swap 0 1\nswap 1 3')),
 dict(id=3, short='One drop', name='A little color', concept='Resource constraints', width=2,
      description='No swap can make a second blue tile. You have one drop of paint: spend it where it matters.',
      start=blocks(C,B,M,G), target=blocks(B,C,M,B), locked=[2], paints=1, moves=2,
      hints=['Swaps only rearrange colors. The target has two blues, so one tile must be painted.', 'swap 0 1, then paint 3 blue.'],
      starter='-- Cell 2 is locked\n', solution=dict(helpers='', proof='swap 0 1\npaint 3 blue')),
 dict(id=4, short='Rotation', name='A quarter turn', concept='Orientation is state', width=2,
      description='Blocks face a direction, and the goal cares. A rotation turns one block a quarter turn clockwise.',
      start=blocks(C,B,M,G), target=blocks(C,G,M,(B,2)), locked=[], paints=0, moves=3,
      hints=['A block keeps its facing when it moves. Blue must end in cell 3, facing south.', 'swap 1 3, then rotate 3 twice. Rotating first also works.'],
      starter='-- rotate 3 turns cell 3 clockwise\n', solution=dict(helpers='', proof='swap 1 3\nrotate 3\nrotate 3')),
 dict(id=5, short='Invariants', name='The long way home', concept='Invariants', width=2,
      description='The mint tile is locked. Bring gold and coral around it in exactly three steps.',
      start=blocks(C,B,M,G), target=blocks(G,B,M,C), locked=[2], paints=0, moves=3,
      hints=['Cell 2 never changes, so every route goes through the top row.', 'swap 0 1, swap 1 3, swap 0 1.'],
      starter='-- Never touch the locked tile\n', solution=dict(helpers='', proof='swap 0 1\nswap 1 3\nswap 0 1')),
 dict(id=6, short='Helpers', name='Name the pattern', concept='Reusable helpers', width=3, line_limit=3,
      description='Shift the top row left twice and turn the center around, in at most three proof lines. Name your patterns.',
      start=blocks(C,B,G,M,M,M,G,B,C), target=blocks(G,C,B,M,(M,2),M,G,B,C), locked=[3,5], paints=0, moves=6,
      hints=['One left shift of the top row is swap 0 1 then swap 1 2. You need two shifts and two quarter turns of cell 4.',
             'Helpers: macro "shift" : tactic => `(tactic| (swap 0 1; swap 1 2)) and macro "halfTurn" : tactic => `(tactic| (rotate 4; rotate 4)). Proof: shift, shift, halfTurn.'],
      starter='-- Use your helpers here, one per line\n',
      helper_starter='-- macro "name" : tactic => `(tactic| (move; move))\n',
      solution=dict(helpers='macro "shift" : tactic => `(tactic| (swap 0 1; swap 1 2))\nmacro "halfTurn" : tactic => `(tactic| (rotate 4; rotate 4))',
                    proof='shift\nshift\nhalfTurn')),
 dict(id=7, short='Composition II', name='Turn the corners', concept='Helpers built from helpers', width=3, line_limit=3,
      description='Every corner must face south and one edge turns gold. Helpers can call earlier helpers.',
      start=blocks(C,B,C,B,M,B,C,B,C), target=blocks((C,2),G,(C,2),B,M,B,(C,2),B,(C,2)), locked=[4], paints=1, moves=9,
      hints=['A quarter turn of all four corners is one helper. Turning south needs it twice.',
             'Helpers: macro "corners" : tactic => `(tactic| (rotate 0; rotate 2; rotate 6; rotate 8)) and macro "south" : tactic => `(tactic| (corners; corners)). Proof: south, then paint 1 gold.'],
      starter='-- Three lines at most\n',
      helper_starter='-- macro "name" : tactic => `(tactic| (move; move))\n',
      solution=dict(helpers='macro "corners" : tactic => `(tactic| (rotate 0; rotate 2; rotate 6; rotate 8))\nmacro "south" : tactic => `(tactic| (corners; corners))',
                    proof='south\npaint 1 gold')),
]
for _l in LEVELS: _l['helpers_enabled'] = 'line_limit' in _l
PUBLIC = [{k: v for k, v in l.items() if k != 'solution'} for l in LEVELS]

# Words a helper may not be named: player moves, Lean keywords/tactics, and names the generated file uses.
RESERVED = set('''swap paint rotate macro tactic by at do fun have show from then else with match let open
end done exact apply intro simp decide sorry rfl refine next legal run step in if for where deriving theorem
def example calc admit omega trivial skip repeat first try case cases induction rename rw unfold native_decide
import namespace section variable axiom instance structure inductive class abbrev private protected noncomputable
puzzle start finish move Reaches Level Block State Move Color ProofPuzzle print axioms true false'''.split()) | set(COLORS)
NAME = r'[A-Za-z][A-Za-z0-9]{2,15}'
MOVE_RES = [('swap', re.compile(r'swap\s+(\d{1,2})\s+(\d{1,2})')),
            ('paint', re.compile(r'paint\s+(\d{1,2})\s+(coral|blue|mint|gold)')),
            ('rotate', re.compile(r'rotate\s+(\d{1,2})'))]
HELPER_RE = re.compile(r'macro\s+"(' + NAME + r')"\s*:\s*tactic\s*=>\s*`\(tactic\|\s*(.*)\)')

def strip(raw):
    return raw.split('--')[0].strip()

def parse_item(text, helpers, where):
    """One move or helper call → canonical Lean text and its expanded move count."""
    text = ' '.join(text.split())
    for kind, rx in MOVE_RES:
        m = rx.fullmatch(text)
        if m: return dict(kind=kind, text=text, args=list(m.groups()), count=1)
    if re.fullmatch(NAME, text) and text in helpers:
        return dict(kind='call', text=text, name=text, count=helpers[text])
    if re.fullmatch(NAME, text) and text not in RESERVED:
        raise ValueError(f'{where}: there is no helper named {text} yet.')
    raise ValueError(f'{where}: use swap 0 1, paint 0 blue, rotate 0, or a helper you defined above.')

def parse(helpers_code, proof_code, level):
    """Validate player text against the allowlist. Returns helpers and proof lines with source line numbers."""
    for code in (helpers_code, proof_code):
        if not isinstance(code, str) or len(code) > 4000: raise ValueError('Keep each box under 4,000 characters.')
    helpers, counts = [], {}
    for n, raw in enumerate(helpers_code.splitlines(), 1):
        line = strip(raw)
        if not line: continue
        where = f'Helper line {n}'
        if not level['helpers_enabled']: raise ValueError('Helpers unlock on level 6.')
        m = HELPER_RE.fullmatch(line)
        if not m: raise ValueError(f'{where}: write macro "name" : tactic => `(tactic| (move; move)).')
        name, body = m[1], m[2].strip()
        if name in RESERVED: raise ValueError(f'{where}: {name} is a reserved word. Pick another name.')
        if name in counts: raise ValueError(f'{where}: {name} is already defined.')
        inner = body[1:-1] if body.startswith('(') and body.endswith(')') else body
        parts = [p.strip() for p in inner.split(';')]
        if not 1 <= len(parts) <= MAX_HELPER_BODY or not all(parts):
            raise ValueError(f'{where}: a helper holds 1 to {MAX_HELPER_BODY} moves separated by semicolons.')
        items = [parse_item(p, counts, where) for p in parts]
        counts[name] = sum(i['count'] for i in items)
        helpers.append(dict(line=n, name=name, items=items))
        if len(helpers) > MAX_HELPERS: raise ValueError(f'At most {MAX_HELPERS} helpers per level.')
    proof = []
    for n, raw in enumerate(proof_code.splitlines(), 1):
        line = strip(raw)
        if line: proof.append(dict(line=n, **parse_item(line, counts, f'Line {n}')))
    if 'line_limit' in level and len(proof) > level['line_limit']:
        raise ValueError(f"This level allows at most {level['line_limit']} proof lines. Name a helper to say more with less.")
    total = sum(p['count'] for p in proof)
    if total > level['moves']:
        raise ValueError(f"Your proof plays {total} moves, but this level allows {level['moves']}.")
    return dict(helpers=helpers, proof=proof, total=total)

def lean_board(board):
    return '[' + ', '.join(f'⟨.{c}, {f}⟩' for c, f in board) + ']'

def helper_text(h):
    body = '; '.join(i['text'] for i in h['items'])
    return f'macro "{h["name"]}" : tactic => `(tactic| ({body}))'

def source(level, parsed, standalone=False):
    """The complete Lean file and a map from its line numbers to player lines."""
    name = f"level_{level['id']}_solved"
    head = RULES.read_text().rstrip() + '\n' if standalone else 'import ProofPuzzle.Rules\n'
    lines = (head + f'''
open ProofPuzzle

/-- Level {level['id']}: {level['name']} -/
def puzzle : Level :=
  {{ width := {level['width']}, locked := {level['locked']},
    target := {lean_board(level['target'])} }}

def start : State :=
  {{ board := {lean_board(level['start'])}, paints := {level['paints']}, moves := {level['moves']} }}
''').split('\n')
    where = {}
    if parsed['helpers']:
        lines.append('-- Your helpers')
        for h in parsed['helpers']:
            lines.append(helper_text(h)); where[len(lines)] = ('helpers', h['line'])
        lines.append('')
    lines.append(f'theorem {name} : Reaches puzzle start := by')
    for p in parsed['proof']:
        lines.append('  ' + p['text']); where[len(lines)] = ('proof', p['line'])
    lines.append('  exact Reaches.finish (by decide)'); where[len(lines)] = ('finish', None)
    lines += ['', f'#print axioms {name}', '']
    return '\n'.join(lines), where

def rules_ready():
    """Compile Rules.lean to an .olean once per content/toolchain change. False → inline the rules."""
    stamp = BUILD / 'rules.sha256'
    digest = hashlib.sha256(RULES.read_bytes() + LEAN.encode()).hexdigest()
    with BUILD_LOCK:
        if OLEAN.exists() and stamp.exists() and stamp.read_text() == digest: return True
        OLEAN.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([LEAN, f'--root={ROOT / "lean"}', '-o', str(OLEAN), str(RULES)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0: return False
        stamp.write_text(digest); return True

DIAG_RE = re.compile(r'^.*?:(\d+):(\d+): (error|warning): ', re.M)

def diagnostics(output, where):
    """Split Lean output into messages tagged with the player line they came from."""
    found = list(DIAG_RE.finditer(output)); out = []
    for i, m in enumerate(found):
        text = output[m.end(): found[i + 1].start() if i + 1 < len(found) else len(output)].strip()
        text = re.sub(r"\n'level_\d+_solved' depends on axioms.*", '', text, flags=re.S)
        section, line = where.get(int(m[1]), ('generated', None))
        kind = ('illegal' if 'proposition\n  legal' in text else 'mismatch' if section == 'finish'
                else 'unknown' if 'unknown' in text else 'lean')
        out.append(dict(severity=m[3], section=section, line=line, kind=kind, message=text[:1500]))
    return out

def verify(level, parsed):
    if not Path(LEAN).exists():
        return dict(verified=False, available=False, message='Lean is not installed yet. The board preview still works, but nothing is verified.')
    imported = rules_ready()
    src, where = source(level, parsed, standalone=not imported)
    key = hashlib.sha256(src.encode()).hexdigest()
    with CACHE_LOCK:
        if key in CACHE: CACHE.move_to_end(key); return dict(CACHE[key], cached=True)
    if not GATE.acquire(blocking=False): return dict(verified=False, available=True, message='The verifier is busy. Try again in a moment.')
    try:
        with tempfile.TemporaryDirectory(prefix='proofpuzzle-') as d:
            path = Path(d) / 'Solution.lean'; path.write_text(src)
            env = dict(os.environ, LEAN_PATH=f'{BUILD}:{TOOLCHAIN / "lib/lean"}')
            r = subprocess.run([LEAN, '--threads=1', str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return dict(verified=False, available=True, message='The Lean check timed out. Please retry.')
    finally: GATE.release()
    output = r.stdout + r.stderr
    errors = [e for e in diagnostics(output, where) if e['severity'] == 'error']
    ax = re.search(r"depends on axioms: \[(.*?)\]", output, re.S)
    axioms = [a.strip() for a in ax[1].split(',')] if ax else []
    clean = bool(ax or 'does not depend on any axioms' in output) and set(axioms) <= ALLOWED_AXIOMS
    ok = r.returncode == 0 and not errors and clean
    result = dict(verified=ok, available=True, errors=errors, axioms=axioms, diagnostics=output[-6000:],
                  message='The Lean kernel checked every move and proved the board reaches the goal.' if ok else 'Lean did not accept this proof.')
    if ok or errors:
        with CACHE_LOCK:
            CACHE[key] = result
            if len(CACHE) > CACHE_SIZE: CACHE.popitem(last=False)
    return result

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)
    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff'); super().end_headers()
    def send_json(self, data, status=200):
        body = json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
    def local(self):
        hosts = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
        origin = self.headers.get('Origin')
        return self.headers.get('Host') in hosts and (not origin or origin in {f'http://{h}' for h in hosts})
    def do_GET(self):
        if self.path == '/api/levels': return self.send_json(PUBLIC)
        if self.path == '/api/health': return self.send_json(dict(lean=Path(LEAN).exists()))
        super().do_GET()
    def do_POST(self):
        if self.path != '/api/check': return self.send_json(dict(error='Not found'), 404)
        if not self.local(): return self.send_json(dict(error=dict(message='Requests must come from this machine.')), 403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 12000: raise ValueError('Request too large or empty.')
            data = json.loads(self.rfile.read(size))
            level = next((l for l in LEVELS if l['id'] == data.get('level')), None)
            if not level: raise ValueError('Unknown level.')
            parsed = parse(data.get('helpers', ''), data.get('proof'), level)
            result = dict(source=source(level, parsed, standalone=True)[0], verified=False)
            if data.get('verify'): result.update(verify(level, parsed))
            return self.send_json(result)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return self.send_json(dict(error=dict(message=str(e)), verified=False), 400)
        except Exception:
            return self.send_json(dict(error=dict(message='The local verifier could not finish. Check the terminal.'), verified=False), 500)

if __name__ == '__main__':
    if Path(LEAN).exists(): print('Rules precompiled.' if rules_ready() else 'Rules failed to precompile; inlining them.', flush=True)
    print(f'Proof Puzzle → http://127.0.0.1:{PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
