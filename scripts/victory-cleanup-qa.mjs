import { chromium } from 'playwright';
import { spawn as spawnProcess } from 'node:child_process';

const PORT=4182, BASE=`http://127.0.0.1:${PORT}`;
const server=spawnProcess('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1'],{stdio:['ignore','pipe','pipe']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(ok,msg)=>{if(!ok)throw Error(msg)};

async function waitServer(){for(let i=0;i<40;i++){try{const r=await fetch(`${BASE}/game.html`,{cache:'no-store'});if(r.ok)return}catch{}await sleep(250)}throw Error('QA server did not start')}

async function scenario(browser,count){
  const context=await browser.newContext({viewport:{width:390,height:844}});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${BASE}/game.html?victoryqa=1&t=${Date.now()}`,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>window.OneGameTest?.victoryDiagnostics&&window.OneGameTest?.placePaladinsNearCastle,{timeout:10000});
  const call=(method,...args)=>page.evaluate(({method,args})=>window.OneGameTest[method](...args),{method,args});

  await call('reset');
  for(let i=0;i<count;i++)await call('paladin');
  await call('placePaladinsNearCastle');
  const before=await call('victoryDiagnostics');
  assert(before.unitCount===count,`expected ${count} units before result, got ${before.unitCount}`);

  const firstFrame=await page.evaluate(async()=>{
    const overlay=document.getElementById('victoryOverlay');
    return await new Promise((resolve,reject)=>{
      const timeout=setTimeout(()=>reject(new Error('overlay did not become visible')),2000);
      const obs=new MutationObserver(()=>{
        if(overlay.classList.contains('show')){
          clearTimeout(timeout);obs.disconnect();
          const units=[...document.querySelectorAll('.unit')];
          const card=document.querySelector('.victory-card');
          const cardRect=card?.getBoundingClientRect();
          resolve({
            unitCount:units.length,
            hidden:units.every(el=>{const s=getComputedStyle(el);return s.display==='none'||s.visibility==='hidden'}),
            runningAnimations:units.reduce((n,el)=>n+el.getAnimations({subtree:true}).filter(a=>a.playState==='running').length,0),
            overlap:units.some(el=>{const r=el.getBoundingClientRect();return cardRect&&r.right>cardRect.left&&r.left<cardRect.right&&r.bottom>cardRect.top&&r.top<cardRect.bottom})
          });
        }
      });
      obs.observe(overlay,{attributes:true,attributeFilter:['class']});
      window.OneGameTest.damageCastle('red',100);
    });
  });

  assert(firstFrame.unitCount===0||firstFrame.hidden,`FIRST VISIBLE FRAME DIRTY: ${firstFrame.unitCount} units still visible`);
  assert(firstFrame.overlap===false,'a unit overlaps victory-card on first visible frame');
  assert(firstFrame.runningAnimations===0,`unit animations still running: ${firstFrame.runningAnimations}`);

  const ended=await call('victoryDiagnostics');
  assert(ended.ended&&ended.overlayShown,'result did not end/open correctly');
  assert(ended.unitCount===0,'DOM units remained after showVictory');
  assert(ended.activeAnimations===0,'unit animation remained after ended=true');
  assert(ended.overlayZ>=100,`overlay z-index too low: ${ended.overlayZ}`);

  const hpBefore=await page.evaluate(()=>window.OneGameTest.snapshot().redHp);
  await call('damageCastle','red',20);
  const hpAfter=await page.evaluate(()=>window.OneGameTest.snapshot().redHp);
  assert(hpAfter===hpBefore,'castle kept receiving attacks/damage after ended=true');

  await sleep(5400);
  const restarted=await page.evaluate(()=>window.OneGameTest.snapshot());
  assert(restarted.ended===false&&restarted.redHp===100&&restarted.blueHp===100,'next round did not reset normally');
  await call('paladin');
  const afterSpawn=await page.evaluate(()=>window.OneGameTest.snapshot());
  assert(afterSpawn.units.some(u=>u.kind==='paladin'),'next round did not accept new units after reset');
  assert(errors.length===0,`runtime errors: ${errors.join(' | ')}`);
  console.log(`VICTORY CLEANUP OK count=${count} firstFrameUnits=${firstFrame.unitCount} overlap=${firstFrame.overlap} animations=${firstFrame.runningAnimations}`);
  await context.close();
}

let browser;
try{
  await waitServer();
  browser=await chromium.launch({headless:true});
  for(const count of [1,5,20])await scenario(browser,count);
  console.log('1GAME VICTORY CLEANUP QA: ALL SCENARIOS PASSED');
}finally{if(browser)await browser.close();server.kill('SIGTERM')}
