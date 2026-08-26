import { chromium } from 'playwright';
import { spawn as spawnProcess } from 'node:child_process';

const PORT=4177, BASE=`http://127.0.0.1:${PORT}`;
const server=spawnProcess('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1'],{stdio:['ignore','pipe','pipe']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(ok,msg)=>{if(!ok)throw Error(msg)};
const minDistance=arr=>{let best=Infinity;for(let i=0;i<arr.length;i++)for(let j=i+1;j<arr.length;j++)best=Math.min(best,Math.hypot(arr[i].x-arr[j].x,arr[i].y-arr[j].y));return best};

async function waitServer(){for(let i=0;i<40;i++){try{const r=await fetch(`${BASE}/game.html`,{cache:'no-store'});if(r.ok)return}catch{}await sleep(250)}throw Error('QA server did not start')}

async function run(browser,name,viewport){
  const context=await browser.newContext({viewport});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${BASE}/game.html?finalqa=1&t=${Date.now()}`,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>window.OneGameTest?.roundEndDiagnostics&&window.OneGameTest?.castleContactAt&&window.OneGameTest?.setCastleHpForTest,{timeout:10000});
  const call=(method,...args)=>page.evaluate(({method,args})=>window.OneGameTest[method](...args),{method,args});
  const snap=()=>page.evaluate(()=>window.OneGameTest.snapshot());

  const diag0=await call('roundEndDiagnostics');
  assert(diag0.overlayZ>=100,`[${name}] victory overlay z-index too low: ${diag0.overlayZ}`);
  assert(diag0.paladinStopRadius===3.5,`[${name}] unexpected castle stopRadius ${diag0.paladinStopRadius}`);

  for(const count of [1,5,12]){
    await call('reset');
    await call('setCastleHpForTest','red',100000); // QA-only: real reset HP remains 100.
    for(let i=0;i<count;i++)await call('paladin');
    const requiredFront=count===1?1:(count===5?3:4);
    const deadline=Date.now()+Math.max(26000,Math.ceil(viewport.width*42));
    let s,attackers=[],pals=[];
    do{
      await sleep(250);
      s=await snap();
      pals=s.units.filter(u=>u.kind==='paladin');
      attackers=pals.filter(u=>u.attackingCastle);
      const approach=pals.filter(u=>u.x<150);
      if(attackers.length>=requiredFront&&approach.length===count)break;
    }while(Date.now()<deadline);
    assert(pals.length===count,`[${name}] ${count} paladins expected, got ${pals.length}`);
    assert(attackers.length>=requiredFront,`[${name}] only ${attackers.length}/${count} paladins formed the attack line; required ${requiredFront}`);
    const approach=pals.filter(u=>u.x<150);
    assert(approach.length===count,`[${name}] collective assault not assembled near castle: ${approach.length}/${count}`);
    if(count>1){const d=minDistance(pals);assert(d>=30,`[${name}] collective castle assault overlapped units: ${d.toFixed(1)}px`)}
    const checked=[];
    for(const u of attackers){
      const contact=await call('castleContactAt',u.y,17);
      assert(u.x>=contact.safeLeft-2.5,`[${name}] paladin crossed castle collision: x=${u.x.toFixed(1)} safe=${contact.safeLeft.toFixed(1)} y=${u.y.toFixed(1)}`);
      assert(u.x<=contact.safeLeft+6,`[${name}] paladin too far from castle: x=${u.x.toFixed(1)} safe=${contact.safeLeft.toFixed(1)} y=${u.y.toFixed(1)}`);
      checked.push({x:u.x,y:u.y,safe:contact.safeLeft,front:contact.front,scale:contact.scale});
    }
    const c=checked[0];
    console.log(`CASTLE GROUP [${name}] count=${count} frontAttackers=${attackers.length} assembled=${approach.length}/${count} x=${c.x.toFixed(1)} safe=${c.safe.toFixed(1)} front=${c.front.toFixed(1)} scale=${c.scale.toFixed(2)}`);
  }

  // Real 100 HP again: destroy castle, open result, fade and remove every unit.
  await call('reset');
  for(let i=0;i<12;i++)await call('paladin');
  await sleep(300);
  await call('damageCastle','red',100);
  let d=await call('roundEndDiagnostics');
  assert(d.ended&&d.overlayShown,`[${name}] victory overlay did not open`);
  assert(d.unitCount===12,`[${name}] units should still exist during fade start, got ${d.unitCount}`);
  await sleep(120);
  d=await call('roundEndDiagnostics');
  assert(d.unitOpacity.every(v=>Number(v)<1),`[${name}] unit fade did not start: ${d.unitOpacity.join(',')}`);
  await sleep(380);
  d=await call('roundEndDiagnostics');
  assert(d.unitCount===0,`[${name}] units remained over victory screen: ${d.unitCount}`);
  assert(d.overlayShown&&d.overlayZ>=100,`[${name}] overlay lost visibility/z-index after despawn`);
  assert(errors.length===0,`[${name}] runtime errors: ${errors.join(' | ')}`);
  console.log(`ROUND END [${name}] fade=400ms remove=420ms unitsAfter=0 overlayZ=${d.overlayZ}`);
  await context.close();
}

let browser;
try{
  await waitServer();
  browser=await chromium.launch({headless:true});
  await run(browser,'mobile',{width:390,height:844});
  await run(browser,'desktop',{width:1440,height:900});
  console.log('1GAME FINAL ROUND/CASTLE QA: ALL SCENARIOS PASSED');
}finally{if(browser)await browser.close();server.kill('SIGTERM')}
