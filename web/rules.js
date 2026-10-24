// Browser preview of lean/ProofPuzzle/Rules.lean. Lean stays the judge; test_game.py
// checks this file move-for-move against Lean's own `step`.
(function(root){
const COLORS=['coral','blue','mint','gold'];
const RESERVED=new Set(`swap paint rotate macro tactic by at do fun have show from then else with match let open
end done exact apply intro simp decide sorry rfl refine next legal run step in if for where deriving theorem
def example calc admit omega trivial skip repeat first try case cases induction rename rw unfold native_decide
import namespace section variable axiom instance structure inductive class abbrev private protected noncomputable
puzzle start finish move Reaches Level Block State Move Color ProofPuzzle print axioms true false`.split(/\s+/).concat(COLORS));
const NAME=/^[A-Za-z][A-Za-z0-9]{2,15}$/;
const MAX_HELPERS=4,MAX_HELPER_BODY=8;
const MOVE_RES=[['swap',/^swap\s+(\d{1,2})\s+(\d{1,2})$/],['paint',/^paint\s+(\d{1,2})\s+(coral|blue|mint|gold)$/],['rotate',/^rotate\s+(\d{1,2})$/]];
const HELPER_RE=/^macro\s+"([A-Za-z][A-Za-z0-9]{2,15})"\s*:\s*tactic\s*=>\s*`\(tactic\|\s*(.*)\)$/;
const strip=raw=>raw.split('--')[0].trim();

function parseItem(text,helpers){
  text=text.split(/\s+/).filter(Boolean).join(' ');
  for(const [kind,rx] of MOVE_RES){const m=text.match(rx);if(m)return kind==='swap'?{kind,a:+m[1],b:+m[2]}:kind==='paint'?{kind,a:+m[1],color:m[2]}:{kind,a:+m[1]};}
  if(NAME.test(text)&&helpers.has(text))return {kind:'call',name:text};
  if(NAME.test(text)&&!RESERVED.has(text))throw new Error(`There is no helper named ${text} yet.`);
  throw new Error('Use swap 0 1, paint 0 blue, rotate 0, or a helper you defined above.');
}
const expand=(item,helpers)=>item.kind==='call'?helpers.get(item.name):[item];

/** Parse both boxes without throwing; every problem is attached to its line. */
function parseProgram(helpersCode,proofCode,level){
  const helpers=new Map(),helperLines=[],proof=[],errors=[];
  helpersCode.split('\n').forEach((raw,i)=>{
    const line=strip(raw),n=i+1;
    if(!line){helperLines.push({line:n,status:'idle'});return;}
    try{
      if(!level.helpers_enabled)throw new Error('Helpers unlock on level 6.');
      const m=line.match(HELPER_RE);
      if(!m)throw new Error('Write macro "name" : tactic => `(tactic| (move; move)).');
      const name=m[1],body=m[2].trim();
      if(RESERVED.has(name))throw new Error(`${name} is a reserved word. Pick another name.`);
      if(helpers.has(name))throw new Error(`${name} is already defined.`);
      const inner=body.startsWith('(')&&body.endsWith(')')?body.slice(1,-1):body;
      const parts=inner.split(';').map(p=>p.trim());
      if(parts.length<1||parts.length>MAX_HELPER_BODY||parts.some(p=>!p))throw new Error(`A helper holds 1 to ${MAX_HELPER_BODY} moves separated by semicolons.`);
      const moves=parts.flatMap(p=>expand(parseItem(p,helpers),helpers));
      if(helpers.size>=MAX_HELPERS)throw new Error(`At most ${MAX_HELPERS} helpers per level.`);
      helpers.set(name,moves);helperLines.push({line:n,status:'ok',name,count:moves.length});
    }catch(e){helperLines.push({line:n,status:'parse'});errors.push({section:'helpers',line:n,message:e.message});}
  });
  proofCode.split('\n').forEach((raw,i)=>{
    const line=strip(raw),n=i+1;
    if(!line){proof.push({line:n,status:'idle',moves:[]});return;}
    try{const item=parseItem(line,helpers);proof.push({line:n,status:'ok',item,moves:expand(item,helpers)});}
    catch(e){proof.push({line:n,status:'parse',moves:[]});errors.push({section:'proof',line:n,message:e.message});}
  });
  const played=proof.filter(p=>p.status!=='idle');
  if(level.line_limit&&played.length>level.line_limit)errors.push({section:'proof',line:played[level.line_limit].line,message:`This level allows at most ${level.line_limit} proof lines. Name a helper to say more with less.`});
  return {helpers,helperLines,proof,errors,lineCount:played.length};
}

const adjacent=(w,a,b)=>(Math.floor(a/w)===Math.floor(b/w)&&(a+1===b||b+1===a))||a+w===b||b+w===a;

/** Mirror of `step` in Rules.lean: returns {state} or {error, cells}. */
function step(level,s,m){
  const n=s.board.length,locked=c=>level.locked.includes(c),off=c=>c>=n;
  if(s.moves===0)return {error:`No moves left. This level allows ${level.moves}.`,cells:[m.a,m.b??m.a]};
  if(m.kind==='swap'){
    if(locked(m.a)||locked(m.b))return {error:`Cell ${locked(m.a)?m.a:m.b} is locked. It can't move, change color, or turn.`,cells:[m.a,m.b]};
    if(!adjacent(level.width,m.a,m.b))return {error:`Cells ${m.a} and ${m.b} don't share an edge.`,cells:[m.a,m.b]};
    if(off(m.a)||off(m.b))return {error:`There is no cell ${off(m.a)?m.a:m.b} on this board.`,cells:[]};
    const board=s.board.map(x=>x.slice());[board[m.a],board[m.b]]=[board[m.b],board[m.a]];
    return {state:{board,paints:s.paints,moves:s.moves-1}};
  }
  if(m.kind==='paint'&&s.paints===0)return {error:'No paint left.',cells:[m.a]};
  if(locked(m.a))return {error:`Cell ${m.a} is locked. It can't move, change color, or turn.`,cells:[m.a]};
  if(off(m.a))return {error:`There is no cell ${m.a} on this board.`,cells:[]};
  const board=s.board.map(x=>x.slice());
  if(m.kind==='paint'){board[m.a][0]=m.color;return {state:{board,paints:s.paints-1,moves:s.moves-1}};}
  board[m.a][1]=(board[m.a][1]+1)%4;return {state:{board,paints:s.paints,moves:s.moves-1}};
}

const initial=level=>({board:level.start.map(x=>x.slice()),paints:level.paints,moves:level.moves});

/** Play every parsed move. frames[k] is the state after k moves; stops at the first illegal move. */
function simulate(level,program){
  const frames=[{state:initial(level),move:null,line:null}];let failure=null;
  for(const p of program.proof){
    if(p.status!=='ok'){continue;}
    if(failure){p.status='after';continue;}
    for(const m of p.moves){
      const r=step(level,frames[frames.length-1].state,m);
      if(r.error){failure={line:p.line,move:m,message:r.error,cells:r.cells,at:frames.length-1};p.status='bad';break;}
      frames.push({state:r.state,move:m,line:p.line});
    }
  }
  const last=frames[frames.length-1].state;
  return {frames,failure,solved:!failure&&!program.errors.length&&sameBoard(last.board,level.target)};
}
const sameBoard=(a,b)=>a.length===b.length&&a.every((x,i)=>x[0]===b[i][0]&&x[1]===b[i][1]);

/** Encoding shared with the Lean differential test. */
const encode=s=>s?s.board.map(([c,f])=>c[0]+f).join('')+`/${s.paints}/${s.moves}`:'none';

root.PuzzleRules={COLORS,parseProgram,step,simulate,initial,sameBoard,encode,adjacent};
if(typeof module!=='undefined')module.exports=root.PuzzleRules;
})(typeof window!=='undefined'?window:globalThis);
