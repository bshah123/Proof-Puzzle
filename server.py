"""Local-only Proof Puzzle server. Only a constrained move grammar reaches Lean."""
import json, re, subprocess, tempfile, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
COLORS = ['coral', 'blue', 'mint', 'gold']
LEAN = str(Path.home() / '.elan/toolchains/leanprover--lean4---v4.19.0/bin/lean')
GATE = threading.Semaphore(2)
LEVELS = [
 dict(id=1, name='A change of places', concept='Your first proof', description='Trade the two top tiles. One small move, one complete proof.', start=['coral','blue','mint','gold'], target=['blue','coral','mint','gold'], locked=[], paints=0, limit=1, hint='Adjacent cells share an edge. Try .swap 0 1.', starter='-- Swap two adjacent cells\n', solution='.swap 0 1'),
 dict(id=2, name='Around the corner', concept='Composition', description='Two swaps, in the right order. Watch how one move changes the next.', start=['coral','blue','mint','gold'], target=['blue','gold','mint','coral'], locked=[], paints=0, limit=2, hint='First swap the top row. Then swap the right column.', starter='-- Every line is a move\n', solution='.swap 0 1\n.swap 1 3'),
 dict(id=3, name='A little color', concept='Resource constraints', description='You have one drop of paint. Spend it where it matters.', start=['coral','blue','mint','gold'], target=['blue','coral','mint','blue'], locked=[2], paints=1, limit=2, hint='Swap cells 0 and 1, then paint cell 3 blue.', starter='-- Cell 2 is locked\n', solution='.swap 0 1\n.paint 3 .blue'),
 dict(id=4, name='The long way home', concept='Invariants', description='The mint tile is locked. Move the others around it in three steps.', start=['coral','blue','mint','gold'], target=['gold','blue','mint','coral'], locked=[2], paints=0, limit=3, hint='Swap the top row, then the right column, then the top row again.', starter='-- Never touch the locked tile\n', solution='.swap 0 1\n.swap 1 3\n.swap 0 1'),
 dict(id=5, name='A reusable idea', concept='Reusable helpers', description='Name a sequence, then reuse it. The helper flipTop swaps the top row.', start=['coral','blue','mint','gold'], target=['gold','blue','mint','coral'], locked=[2], paints=0, limit=3, hint='Use flipTop, then .swap 1 3, then flipTop again.', starter='-- flipTop expands to [.swap 0 1]\n', solution='flipTop\n.swap 1 3\nflipTop'),
]

def parse(code, level):
    if not isinstance(code, str) or len(code) > 4000: raise ValueError('Keep the proof under 4,000 characters.')
    moves=[]
    for line_no, raw in enumerate(code.splitlines(),1):
        line=raw.split('--')[0].strip().rstrip(',').strip()
        if not line: continue
        if line == 'flipTop' and level['id'] == 5:
            moves.append(dict(kind='swap',a=0,b=1,line=line_no,helper=True)); continue
        m=re.fullmatch(r'\.swap\s+([0-3])\s+([0-3])',line)
        p=re.fullmatch(r'\.paint\s+([0-3])\s+\.(coral|blue|mint|gold)',line)
        if m: moves.append(dict(kind='swap',a=int(m[1]),b=int(m[2]),line=line_no))
        elif p: moves.append(dict(kind='paint',a=int(p[1]),color=p[2],line=line_no))
        else: raise ValueError(f'Line {line_no}: use .swap 0 1 or .paint 0 .blue'+ (' or flipTop.' if level['id']==5 else '.'))
    if len(moves)>level['limit']: raise ValueError(f"This level allows at most {level['limit']} moves.")
    return moves

def simulate(level,moves):
    board=level['start'][:]; paints=level['paints']; states=[dict(board=board[:],paints=paints)]
    for m in moves:
        a=m['a']; b=m.get('b',a)
        error=None
        if a in level['locked'] or b in level['locked']: error='That tile is locked. Its color must stay fixed.'
        elif m['kind']=='swap':
            if abs(a//2-b//2)+abs(a%2-b%2)!=1: error='Only tiles sharing an edge can be swapped.'
            else: board[a],board[b]=board[b],board[a]
        elif paints<=0: error='No paint remains. Try solving this with swaps.'
        else: board[a]=m['color']; paints-=1
        if error: return states,dict(message=error,line=m['line'],cells=[a,b])
        states.append(dict(board=board[:],paints=paints))
    return states,None

def source(level,moves):
    board=lambda xs:'['+', '.join('.'+x for x in xs)+']'
    terms=[]
    for m in moves:
        terms.append('flipTop' if m.get('helper') else '['+(f".swap {m['a']} {m['b']}" if m['kind']=='swap' else f".paint {m['a']} .{m['color']}")+']')
    program=' ++ '.join(terms) or '[]'
    return (ROOT/'lean/Rules.lean').read_text()+f'''\nopen ProofPuzzle
def flipTop : List Move := [.swap 0 1]
def moves : List Move := {program}
theorem level_{level['id']}_solved :
    Solves {board(level['start'])} {board(level['target'])}
      {level['locked']} {level['paints']} {level['limit']} moves := by
  decide
'''

def verify(src):
    if not Path(LEAN).exists(): return dict(verified=False,available=False,message='Lean is not installed yet. The board preview is available, but this is not a verified win.')
    if not GATE.acquire(blocking=False): return dict(verified=False,available=True,message='Verifier is busy. Try again shortly.')
    try:
        with tempfile.TemporaryDirectory(prefix='proofpuzzle-') as d:
            path=Path(d)/'Solution.lean'; path.write_text(src)
            result=subprocess.run([LEAN,'--threads=1',str(path)],cwd=ROOT,capture_output=True,text=True,timeout=20)
        return dict(verified=result.returncode==0,available=True,message='Lean checked every rule and proved the target is reached.' if result.returncode==0 else 'Lean rejected this proof.',diagnostics=(result.stdout+result.stderr)[-6000:])
    except subprocess.TimeoutExpired: return dict(verified=False,available=True,message='Lean check timed out. Please retry.')
    finally: GATE.release()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def send_json(self,data,status=200):
        body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path=='/api/levels': return self.send_json([{k:v for k,v in l.items() if k!='solution'} for l in LEVELS])
        if self.path=='/api/health': return self.send_json(dict(lean=Path(LEAN).exists()))
        super().do_GET()
    def do_POST(self):
        if self.path!='/api/check': return self.send_json(dict(error='Not found'),404)
        origin=self.headers.get('Origin')
        if origin and origin not in ['http://127.0.0.1:8765','http://localhost:8765']: return self.send_json(dict(error='Origin not allowed'),403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8000: raise ValueError('Request too large or empty.')
            data=json.loads(self.rfile.read(size)); level=next((l for l in LEVELS if l['id']==data.get('level')),None)
            if not level: raise ValueError('Unknown level.')
            moves=parse(data.get('code'),level); states,error=simulate(level,moves); src=source(level,moves)
            result=dict(states=states,error=error,moves=moves,source=src,verified=False)
            if data.get('verify'): result.update(verify(src))
            return self.send_json(result)
        except (ValueError,TypeError,json.JSONDecodeError) as e: return self.send_json(dict(error=dict(message=str(e)),verified=False),400)
        except Exception: return self.send_json(dict(error=dict(message='The local verifier could not finish. Check the terminal.'),verified=False),500)

if __name__=='__main__':
    print('Proof Puzzle → http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
