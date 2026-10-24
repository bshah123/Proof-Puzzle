// Isolated UI state tests: fake elements and deferred requests, no browser automation.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const R = require('./web/rules.js');
const level = {id:1, short:'First', name:'First', concept:'Proof', description:'Test', width:2,
  start:[['coral',0],['blue',0],['mint',0],['gold',0]], target:[['blue',0],['coral',0],['gold',0],['mint',0]],
  locked:[], paints:0, moves:2, starter:'', hints:['First','Second'],helpers_enabled:false};
async function setup() {
  const elements=new Map(), saved=new Map([['proofpuzzle-completed','[1]']]), requests=[];
  function element() { return {value:'',hidden:true,disabled:false,textContent:'',innerHTML:'',children:[],
    style:{setProperty(){}},append(...x){this.children.push(...x)},replaceChildren(){this.children=[]},
    setAttribute(){},addEventListener(){},focus(){},showModal(){this.hidden=false},close(){this.hidden=true}}; }
  const document={getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element};
  const context=vm.createContext({document,window:{PuzzleRules:R},console,setTimeout,clearTimeout,
    localStorage:{getItem:k=>saved.get(k)??null,setItem:(k,v)=>saved.set(k,v)},
    fetch:async url=>url==='/api/check'?new Promise(resolve=>requests.push(data=>resolve({json:async()=>data}))):
      {json:async()=>url==='/api/levels'?[structuredClone(level),{...structuredClone(level),id:6,helpers_enabled:true,line_limit:3,moves:6}]:{lean:true}}});
  vm.runInContext(fs.readFileSync('./web/app.js','utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return {elements,saved,requests,run:s=>vm.runInContext(s,context)};
}
test('editing during a check restores controls and ignores its stale result',async()=>{
  const t=await setup(); const check=t.run('check()');
  assert.equal(t.elements.get('verify').disabled,true);
  t.run("$('proof').value='swap 0 1';update()");
  assert.equal(t.elements.get('verify').disabled,false);
  t.requests.shift()({verified:true,message:'old proof'});await check;
  assert.equal(t.run('completed.length'),0);
  assert.match(t.elements.get('verify').innerHTML,/Check proof/);
});
test('an older response cannot re-enable controls for a newer check',async()=>{
  const t=await setup();const old=t.run('check()');t.run('update()');const current=t.run('check()');
  t.requests.shift()({verified:true});await old;
  assert.equal(t.elements.get('verify').disabled,true);
  assert.equal(t.run('busy'),true);
  t.requests.shift()({verified:true,message:'accepted'});await current;
  assert.equal(t.elements.get('verify').disabled,false);
  assert.equal(t.run('completed.length'),1);
});
test('old badges are ignored and redesigned levels have distinct completion keys',async()=>{
  const t=await setup();assert.equal(t.run('completed.length'),0);
  const before=t.run('completionKey(level)');t.run('level.moves=3');
  assert.notEqual(t.run('completionKey(level)'),before);
  assert.equal(t.saved.get('proofpuzzle-completed'),'[1]');
});
test('helper builder generates valid macros and rejects reserved names',async()=>{
  const t=await setup();t.run("select(6);$('helper-name').value='shift';$('helper-moves').value='swap 0 1\\nswap 1 2';$('create-helper').onclick()");
  assert.match(t.elements.get('helpers').value,/macro "shift" : tactic/);
  assert.equal(t.run("R.parseProgram($('helpers').value,'shift',level).errors.length"),0);
  const previous=t.elements.get('helpers').value;
  t.run("$('helper-name').value='sorry';$('create-helper').onclick()");
  assert.equal(t.elements.get('helpers').value,previous);
  assert.match(t.elements.get('helper-error').textContent,/reserved/);
});
