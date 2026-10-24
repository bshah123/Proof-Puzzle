const $=id=>document.getElementById(id);
const R=window.PuzzleRules;
let levels=[],level,program,sim,position=0,revision=0,currentSource='',hintTier=0,busy=false,leanErrors=[];
const store={get(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch{return d;}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch{}}};
const PROGRESS_KEY='proofpuzzle-completed-v2';
const completionKey=l=>JSON.stringify([l.id,l.width,l.start,l.target,l.locked,l.paints,l.moves,l.line_limit||null]);
let completed=store.get(PROGRESS_KEY,[]);if(!Array.isArray(completed))completed=[];
const symbols={coral:'●',blue:'◆',mint:'✦',gold:'■'},facings=['north','east','south','west'];
const pad=n=>String(n).padStart(2,'0');
let verifiedRevision=-1;

function notice(title,message,type=''){const el=$('notice');el.className=type;el.replaceChildren();const icon=document.createElement('span');icon.className='notice-icon';icon.textContent=type==='success'?'✓':type==='error'?'!':'✧';const div=document.createElement('div');const h=document.createElement('strong');h.textContent=title;const p=document.createElement('p');p.textContent=message;div.append(h,p);el.append(icon,div);return div;}

function drawBoard(id,board,changed=[],invalid=[]){
  const el=$(id);el.replaceChildren();el.style.setProperty('--cols',level.width);el.className=`board w${level.width}${id==='target'?' target':''}`;
  const labels=[];
  board.forEach(([color,facing],i)=>{
    const locked=level.locked.includes(i),tile=document.createElement('div');
    tile.className=`tile ${color}${changed.includes(i)?' changed':''}${invalid.includes(i)?' invalid':''}`;
    tile.innerHTML=`<small>${i}</small><i class="face" style="--turn:${facing*90}deg"></i><b>${symbols[color]}</b>${locked?'<span class="lock">⌑</span>':''}`;
    labels.push(`cell ${i} ${color} facing ${facings[facing]}${locked?' locked':''}`);el.append(tile);
  });
  el.setAttribute('aria-label',`${id==='target'?'Goal':'Current board'}: ${labels.join(', ')}`);
}

function gutter(id,lines,count){
  const el=$(id);el.replaceChildren();
  for(let n=1;n<=count;n++){const row=lines.find(l=>l.line===n),s=document.createElement('span');s.textContent=n;
    const lean=leanErrors.find(e=>e.section===(id==='proof-lines'?'proof':'helpers')&&e.line===n);
    s.className=lean?'bad':row?row.status:'idle';if(lean)s.title='Lean rejected this line';el.append(s);}
}

function render(){
  const frame=sim.frames[position],end=sim.frames.length-1,f=sim.failure;
  const showFail=f&&position===end;
  drawBoard('board',frame.state.board,frame.move?[frame.move.a,frame.move.b??frame.move.a]:[],showFail?f.cells:[]);
  drawBoard('target',level.target);
  $('step-label').textContent=position?`AFTER LINE ${frame.line}`:'START';
  $('timeline').textContent=`${position} of ${end} moves`;
  $('moves-left').textContent=frame.state.moves;$('paint-left').textContent=frame.state.paints;
  gutter('helper-lines',program.helperLines,$('helpers').value.split('\n').length);
  gutter('proof-lines',program.proof,$('proof').value.split('\n').length);
  $('first').disabled=$('back').disabled=!position;$('fwd').disabled=$('last').disabled=position===end;
  $('verify').disabled=busy;
  const matches=frame.state.board.filter((cell,i)=>cell[0]===level.target[i][0]&&cell[1]===level.target[i][1]).length;
  $('goal-count').textContent=`${matches} / ${level.target.length} tiles match`;
  $('goal-detail').textContent=matches===level.target.length?(verifiedRevision===revision?'Lean verified this proof. Every move is legal and the target is reached.':'This frame matches the target. Check the complete proof with Lean.'):'Match both color and direction. The proof goal is to reach the target using legal moves.';
}

function explain(){
  const e=program.errors[0],f=sim.failure;
  if(e)return notice(`${e.section==='helpers'?'Helper line':'Line'} ${e.line} isn't a move yet.`,e.message,'error');
  if(f)return notice(`Line ${f.line} is illegal.`,`${f.message} Lean would reject the proof here.`,'error');
  if(sim.solved)return notice('The board matches the goal.','Now ask Lean to check it. Only the kernel can clear the level.','');
  const n=sim.frames.length-1;
  if(!n)return notice('Your next move is an idea.','Write a move on the right. The board follows every line.');
  notice(`${n} legal move${n>1?'s':''} so far.`,'Keep going until your board matches the goal.');
}

function update(){
  revision++;busy=false;leanErrors=[];currentSource='';
  $('verify').innerHTML='Check proof <span>⌘↵</span>';
  program=R.parseProgram($('helpers').value,$('proof').value,level);sim=R.simulate(level,program);
  position=sim.frames.length-1;
  $('proof-source').textContent='Press Check proof (or open this drawer again) to generate the full Lean file.';$('diagnostics').hidden=true;$('axioms').textContent='';
  store.set(`proofpuzzle-draft-${level.id}`,{helpers:$('helpers').value,proof:$('proof').value});
  render();explain();
  clearTimeout(sourceTimer);if(!$('proof-content').hidden)sourceTimer=setTimeout(refreshSource,400);
}

let sourceTimer;
async function refreshSource(){const rev=revision;try{const data=await post(false);if(rev!==revision)return;if(data.error)$('proof-source').textContent=`Fix this first: ${data.error.message}`;else showSource(data);}catch{}}

function followCursor(){
  const line=$('proof').value.slice(0,$('proof').selectionStart).split('\n').length;
  let k=0;sim.frames.forEach((fr,i)=>{if(fr.line!==null&&fr.line<=line)k=i;});
  position=k;render();
}

function select(id){
  level=levels.find(x=>x.id===id);hintTier=0;busy=false;
  $('hint').textContent='Need a hint?';
  const draft=store.get(`proofpuzzle-draft-${id}`,null);
  $('proof').value=draft?.proof??level.starter;$('helpers').value=draft?.helpers??(level.helper_starter||'');
  $('title').textContent=level.name;$('concept').textContent=level.concept;$('description').textContent=level.description;
  $('chapter').textContent=`${pad(id)} / THE EXPEDITION`;$('file-name').textContent=`Level${id}.lean`;$('theorem-name').textContent=`level_${id}_solved`;
  $('lock-count').textContent=level.locked.length;$('line-limit-wrap').hidden=!level.line_limit;$('line-limit').textContent=level.line_limit||'';
  $('helpers-block').hidden=$('insert-helper').hidden=!level.helpers_enabled;
  $('verify').innerHTML='Check proof <span>⌘↵</span>';
  store.set('proofpuzzle-level',id);update();progress();
}

function progress(){
  const count=levels.filter(l=>completed.includes(completionKey(l))).length;
  $('completed').textContent=pad(count);$('total').textContent=pad(levels.length);$('progress').style.width=`${count/levels.length*100}%`;
  $('levels').replaceChildren();
  levels.forEach(l=>{const b=document.createElement('button');b.className=(l.id===level.id?'active ':'')+(completed.includes(completionKey(l))?'done':'');
    b.innerHTML=`<span>${pad(l.id)}</span>${l.short}`;b.setAttribute('aria-current',l.id===level.id?'step':'false');b.onclick=()=>select(l.id);$('levels').append(b);});
}

async function post(verify){
  const r=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({level:level.id,helpers:$('helpers').value,proof:$('proof').value,verify})});
  return r.json();
}

function showSource(data){
  if(!data.source)return;currentSource=data.source;$('proof-source').textContent=data.source;
  if(data.axioms)$('axioms').textContent=data.verified?`Axioms used: ${data.axioms.join(', ')||'none'}. No sorry.`:'';
  $('diagnostics').textContent=data.diagnostics||'';$('diagnostics').hidden=!data.diagnostics||data.verified;
}

async function check(){
  if(busy)return;const rev=revision;busy=true;render();
  $('verify').textContent='Checking with Lean…';notice('Asking Lean to check your proof…','The kernel checks each move, the resources, and the final board.');
  try{
    const data=await post(true);if(rev!==revision)return;
    showSource(data);
    if(data.error)return notice('Lean was not asked yet.',data.error.message,'error');
    if(data.verified){
      verifiedRevision=revision;
      if(!completed.includes(completionKey(level)))completed.push(completionKey(level));store.set(PROGRESS_KEY,completed);progress();
      const nextLevel=levels.find(l=>l.id===level.id+1);
      const div=notice(nextLevel?'Q.E.D. You proved it.':'Expedition complete. Seven proofs, all yours.',`${data.message}${data.cached?' (cached)':''}`,'success');
      if(nextLevel){const b=document.createElement('button');b.textContent='Next puzzle →';b.onclick=()=>select(nextLevel.id);div.append(b);}
      return;
    }
    if(data.available===false)return notice('Preview only: Lean is unavailable',data.message,'error');
    leanErrors=data.errors||[];render();
    const e=leanErrors.find(x=>x.kind==='illegal')||leanErrors.find(x=>x.section!=='finish')||leanErrors[0];
    if(!e)return notice('Not proven yet.',data.message,'error');
    if(e.kind==='illegal'){const why=sim.failure&&sim.failure.line===e.line?` ${sim.failure.message}`:'';return notice(`Lean rejected line ${e.line}.`,`That move is illegal here.${why}`,'error');}
    if(e.kind==='mismatch')return notice('Every move is legal, but this is not the goal.','Lean could not close the proof because your final board differs from the target.','error');
    notice(`Lean rejected ${e.line?`line ${e.line}`:'the proof'}.`,e.message.split('\n')[0],'error');
  }catch{if(rev===revision)notice('Cannot reach the local verifier.','Start server.py and try again. Your proof is still here.','error');}
  finally{if(rev===revision){busy=false;$('verify').innerHTML='Check proof <span>⌘↵</span>';render();}}
}

function insert(box,text){const el=$(box);el.value+=(el.value===''||el.value.endsWith('\n')?'':'\n')+text+'\n';el.focus();el.selectionStart=el.selectionEnd=el.value.length;update();}

for(const id of ['helpers','proof']){$(id).addEventListener('input',update);$(id).addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();check();}});}
$('proof').addEventListener('click',followCursor);$('proof').addEventListener('keyup',e=>{if(e.key.startsWith('Arrow'))followCursor();});
$('verify').onclick=check;
$('first').onclick=()=>{position=0;render();};$('last').onclick=()=>{position=sim.frames.length-1;render();};
$('back').onclick=()=>{position=Math.max(0,position-1);render();};$('fwd').onclick=()=>{position=Math.min(sim.frames.length-1,position+1);render();};
$('insert-swap').onclick=()=>insert('proof','swap 0 1');$('insert-paint').onclick=()=>insert('proof','paint 0 blue');$('insert-rotate').onclick=()=>insert('proof','rotate 0');
$('insert-helper').onclick=()=>{$('helper-name').value='';$('helper-moves').value='';$('helper-error').textContent='';$('helper-dialog').showModal();};
$('close-helper').onclick=()=>$('helper-dialog').close();
$('create-helper').onclick=()=>{
  const name=$('helper-name').value.trim();
  const body=$('helper-moves').value.split('\n').map(x=>x.trim()).filter(Boolean).join('; ');
  const macro='macro "'+name+'" : tactic => `(tactic| ('+body+'))';
  const draft=$('helpers').value+'\n'+macro;
  const parsed=R.parseProgram(draft,'',level);
  if(parsed.errors.length){$('helper-error').textContent=parsed.errors[0].message;return;}
  insert('helpers',macro);$('helper-dialog').close();
  notice('Your helper is ready.',`Write ${name} on a proof line to play its moves. Its Lean macro is visible above the theorem.`);
};
$('hint').onclick=()=>{const h=level.hints[Math.min(hintTier,level.hints.length-1)];notice(hintTier?'The full route.':'A nudge in the right direction.',h);hintTier++;$('hint').textContent=hintTier<level.hints.length?'Show the answer':'Need a hint?';};
$('help').onclick=()=>$('help-dialog').showModal();$('close-help').onclick=()=>$('help-dialog').close();
$('show-proof').onclick=async()=>{const open=$('proof-content').hidden;$('proof-content').hidden=!open;$('show-proof').setAttribute('aria-expanded',open);
  if(open&&!currentSource)refreshSource();};
$('download').onclick=async()=>{const rev=revision;if(!currentSource){try{const data=await post(false);if(rev!==revision)return;if(data.error)return notice('Fix the proof text first.',data.error.message,'error');showSource(data);}catch{return notice('Cannot reach the local verifier.','Start server.py and try again.','error');}}
  const url=URL.createObjectURL(new Blob([currentSource],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download=`ProofPuzzle-Level${level.id}.lean`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};

async function init(){
  try{const [l,h]=await Promise.all([fetch('/api/levels').then(r=>r.json()),fetch('/api/health').then(r=>r.json())]);levels=l;
    $('engine').textContent=h.lean?'Local Lean verifier':'Lean setup pending';
    const saved=store.get('proofpuzzle-level',1);select(levels.some(x=>x.id===saved)?saved:1);}
  catch{notice('The local server is unavailable.','Run python3 server.py, then open http://127.0.0.1:8765.','error');}
}
init();
