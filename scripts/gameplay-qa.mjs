import { chromium } from 'playwright';
import { spawn as spawnProcess } from 'node:child_process';

const PORT=4175, BASE=`http://127.0.0.1:${PORT}`;
const server=spawnProcess('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1'],{stdio:['ignore','pipe','pipe']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

async function waitServer(){for(let i=0;i<40;i++){try{const r=await fetch(`${BASE}/game.html`,{cache:'no-store'});if(r.ok)return}catch{}await sleep(250)}throw Error('QA server did not start')}
const assert=(ok,msg)=>{if(!ok)throw Error(msg)};
const minDistance=arr=>{let best=Infinity;for(let i=0;i<arr.length;i++)for(let j=i+1;j<arr.length;j++)best=Math.min(best,Math.hypot(arr[i].x-arr[j].x,arr[i].y-arr[j].y));return best};

async function runScenario(browser,name,viewport){
  const context=await browser.newContext({viewport});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(`pageerror: ${e.message}`));
  page.on('console',m=>{if(m.type()==='error'&&!/Failed to load resource|PeerJS/i.test(m.text()))errors.push(`console: ${m.text()}`)});
  page.on('requestfailed',r=>{if(!/peerjs|tiktokcdn|favicon/i.test(r.url()))errors.push(`requestfailed: ${r.url()} :: ${r.failure()?.errorText||'unknown'}`)});

  await page.goto(`${BASE}/game.html?qa=1&t=${Date.now()}`,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>window.OneGameTest?.snapshot,{timeout:10000});
  const snap=()=>page.evaluate(()=>window.OneGameTest.snapshot());
  const call=(method,...args)=>page.evaluate(({method,args})=>window.OneGameTest[method](...args),{method,args});

  await page.waitForTimeout(600);
  assert(errors.length===0,`[${name}] runtime errors at boot: ${errors.join(' | ')}`);
  const assets=await page.evaluate(()=>({red:document.getElementById('redCastleImg')?.naturalWidth||0,blue:document.getElementById('blueCastleImg')?.naturalWidth||0,bg:getComputedStyle(document.getElementById('battle')).backgroundImage}));
  assert(assets.red>0&&assets.blue>0,`[${name}] castle asset failed to load`);
  assert(assets.bg&&assets.bg!=='none',`[${name}] battlefield map missing`);

  // Formation sanity: specials must not stack into one another.
  await call('reset');for(let i=0;i<8;i++)await call('paladin');await sleep(1400);
  let p=await snap();const pals=p.units.filter(u=>u.kind==='paladin');
  assert(pals.length===8,`[${name}] expected 8 paladins, got ${pals.length}`);
  assert(pals.every(u=>Number.isFinite(u.x)&&Number.isFinite(u.y)),`[${name}] paladin position became NaN/Infinity`);
  const palMin=minDistance(pals);
  assert(palMin>=30,`[${name}] PALADIN OVERLAP: minimum center distance ${palMin.toFixed(1)}px (expected >=30px)`);
  const bw=viewport.width;
  assert(pals.every(u=>u.x>=112&&u.x<=bw-112),`[${name}] CASTLE BODY OVERLAP: special unit entered player/castle body`);

  // Direction stability: moving toward one objective must not spin through directions every frame.
  const history=[];for(let i=0;i<18;i++){const s=await snap();history.push(s.units.find(u=>u.kind==='paladin')?.dir8);await sleep(110)}
  const clean=history.filter(Boolean),changes=clean.slice(1).reduce((n,v,i)=>n+(v!==clean[i]?1:0),0);
  assert(changes<=2,`[${name}] PALADIN DIRECTION FLICKER: ${changes} direction changes in ~2s (${clean.join(',')})`);

  // Mixed armies: both sides must stay alive, finite and inside a sane world envelope.
  await call('reset');await call('spawn','red',40);await call('spawn','blue',40);for(let i=0;i<4;i++)await call('paladin');await sleep(2500);
  let mixed=await snap();
  assert(mixed.red>0&&mixed.blue>0,`[${name}] one army vanished immediately: red=${mixed.red} blue=${mixed.blue}`);
  assert(mixed.units.every(u=>Number.isFinite(u.x)&&Number.isFinite(u.y)&&u.x>-180&&u.x<viewport.width+180&&u.y>-120&&u.y<viewport.height+120),`[${name}] unit escaped battlefield / invalid coordinates`);
  assert(errors.length===0,`[${name}] runtime errors during mixed battle: ${errors.join(' | ')}`);

  // Round logic: time finish must end the battle and automatic next round must recover.
  await call('reset');await call('damageCastle','red',80);await call('damageCastle','blue',10);await call('finishTime');await sleep(250);
  const ended=await snap();assert(ended.ended===true,`[${name}] time tiebreak did not end round`);
  await sleep(5600);const restarted=await snap();assert(restarted.ended===false&&restarted.redHp===100&&restarted.blueHp===100,`[${name}] automatic next round failed`);

  // Stress similar to Caos Live: loop must keep advancing under a large army.
  await call('reset');await call('spawn','red',80);await call('spawn','blue',80);await sleep(5500);
  const stress=await snap();
  assert(stress.red+stress.blue>20,`[${name}] stress battle unexpectedly lost nearly all units`);
  assert(stress.fps>=15,`[${name}] stress FPS collapsed: ${stress.fps}`);
  assert(errors.length===0,`[${name}] runtime errors under stress: ${errors.join(' | ')}`);

  console.log(`1GAME QA OK [${name}] fps=${stress.fps} mobs=${stress.red+stress.blue} paladinMin=${palMin.toFixed(1)}px dirChanges=${changes}`);
  await context.close();
}

let browser;
try{
  await waitServer();
  browser=await chromium.launch({headless:true});
  await runScenario(browser,'mobile',{width:390,height:844});
  await runScenario(browser,'desktop',{width:1440,height:900});
  console.log('1GAME GAMEPLAY QA: ALL SCENARIOS PASSED');
}finally{if(browser)await browser.close();server.kill('SIGTERM')}
