import { chromium } from 'playwright';
import { spawn as spawnProcess } from 'node:child_process';

const PORT=4176, BASE=`http://127.0.0.1:${PORT}`;
const server=spawnProcess('python3',['-m','http.server',String(PORT),'--bind','127.0.0.1'],{stdio:['ignore','pipe','pipe']});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const assert=(ok,msg)=>{if(!ok)throw new Error(msg)};

const peerStub=`(()=>{
 class E{constructor(){this.h={}} on(n,f){(this.h[n]??=[]).push(f);return this} emit(n,...a){for(const f of this.h[n]||[])f(...a)}}
 class C extends E{constructor(){super();this.open=true;setTimeout(()=>this.emit('open'),0)} send(d){(window.__peerSent??=[]).push(d);if(d?.type==='session_hello')setTimeout(()=>this.emit('data',{type:'session_accept',token:'qa-token'}),0)} close(){this.open=false;this.emit('close')}}
 window.Peer=class extends E{constructor(id){super();this.id=id;setTimeout(()=>this.emit('open',id),0)} connect(){const c=new C();window.__lastPeerConn=c;return c} destroy(){}};
})();`;

async function waitServer(){for(let i=0;i<50;i++){try{const r=await fetch(BASE+'/index.html');if(r.ok)return}catch{}await sleep(200)}throw new Error('release gate server did not start')}

async function waitCurrentUnitSkins(page){
 await page.waitForFunction(()=>{
   const red=[...document.querySelectorAll('.unit.red:not(.paladin) .mob-sprite')];
   const blue=[...document.querySelectorAll('.unit.blue:not(.paladin) .mob-sprite')];
   const pal=[...document.querySelectorAll('.unit.paladin .mob-sprite')];
   const ok=a=>a.length>0&&a.every(i=>i.complete&&i.naturalWidth>0&&i.naturalHeight>0);
   return red.length>=2&&blue.length>=2&&pal.length>=1&&ok(red)&&ok(blue)&&ok(pal);
 },null,{timeout:5000});
 // Two samples avoid accepting the instant between animated src swaps.
 await page.waitForTimeout(140);
 await page.waitForFunction(()=>{
   const all=[...document.querySelectorAll('.unit .mob-sprite')];
   return all.length>=5&&all.every(i=>i.complete&&i.naturalWidth>0&&i.naturalHeight>0);
 },null,{timeout:3000});
}

async function test(browser,name,viewport){
 const context=await browser.newContext({viewport});
 const page=await context.newPage();
 const errors=[];
 page.on('pageerror',e=>errors.push('pageerror: '+e.message));
 page.on('console',m=>{if(m.type()==='error'&&!/tiktokcdn|favicon/i.test(m.text()))errors.push('console: '+m.text())});
 page.on('requestfailed',r=>{if(!/tiktokcdn|favicon/i.test(r.url()))errors.push('requestfailed: '+r.url())});
 await page.route('https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js',route=>route.fulfill({status:200,contentType:'application/javascript',body:peerStub}));

 // 1) Lobby must render and actually complete panel handshake.
 await page.goto(BASE+'/index.html?qa='+Date.now(),{waitUntil:'domcontentloaded'});
 assert(await page.locator('#panelCode').count()===1,`[${name}] lobby panel input missing`);
 assert(await page.locator('#play').count()===1,`[${name}] lobby play button missing`);
 await page.locator('#panelCode').fill('TEST1234');
 await page.locator('#connectPanel').click();
 await page.waitForFunction(()=>document.querySelector('#connectionState')?.textContent?.includes('PAINEL CONECTADO'),null,{timeout:5000});
 assert(errors.length===0,`[${name}] lobby runtime errors: ${errors.join(' | ')}`);

 // 2) Handoff Lobby -> Game must preserve panel session and reconnect.
 await Promise.all([page.waitForURL(/game\.html/,{timeout:5000}),page.locator('#play').click()]);
 await page.waitForFunction(()=>window.OneGameTest?.snapshot,{timeout:8000});
 await page.waitForFunction(()=>document.querySelector('#linkStatus')?.textContent?.includes('PAINEL ON'),null,{timeout:5000});
 const sent=await page.evaluate(()=>window.__peerSent||[]);
 assert(sent.some(x=>x?.type==='game_manifest'),`[${name}] game did not send manifest to panel`);

 // 3) Critical visual assets must really load in browser.
 await page.waitForTimeout(500);
 const baseAssets=await page.evaluate(()=>({
   red:document.querySelector('#redCastleImg')?.naturalWidth||0,
   blue:document.querySelector('#blueCastleImg')?.naturalWidth||0,
   map:getComputedStyle(document.querySelector('#battle')).backgroundImage
 }));
 assert(baseAssets.red>0&&baseAssets.blue>0,`[${name}] castle skin failed to load`);
 assert(baseAssets.map&&baseAssets.map!=='none',`[${name}] map failed to load`);

 // 4) Spawn through gameplay API and verify every current skin class renders.
 const call=(method,...args)=>page.evaluate(({method,args})=>window.OneGameTest[method](...args),{method,args});
 await call('reset');
 await call('spawn','red',2);await call('spawn','blue',2);await call('paladin');
 await waitCurrentUnitSkins(page);
 const skins=await page.evaluate(()=>({
   red:[...document.querySelectorAll('.unit.red:not(.paladin) .mob-sprite')].map(i=>({w:i.naturalWidth,src:i.getAttribute('src')})),
   blue:[...document.querySelectorAll('.unit.blue:not(.paladin) .mob-sprite')].map(i=>({w:i.naturalWidth,src:i.getAttribute('src')})),
   pal:[...document.querySelectorAll('.unit.paladin .mob-sprite')].map(i=>({w:i.naturalWidth,src:i.getAttribute('src')}))
 }));
 assert(skins.red.length>=2&&skins.red.every(x=>x.w>0),`[${name}] red mob skin missing/broken: ${JSON.stringify(skins.red)}`);
 assert(skins.blue.length>=2&&skins.blue.every(x=>x.w>0),`[${name}] blue mob skin missing/broken: ${JSON.stringify(skins.blue)}`);
 assert(skins.pal.length>=1&&skins.pal.every(x=>x.w>0),`[${name}] paladin skin missing/broken: ${JSON.stringify(skins.pal)}`);

 // 5) Real panel command must invoke a special troop, not only direct test hooks.
 const before=(await page.evaluate(()=>window.OneGameTest.snapshot())).units.filter(u=>u.kind==='paladin').length;
 await page.evaluate(()=>window.__lastPeerConn?.emit('data',{type:'command',action:'spawn_blue_paladin'}));
 await page.waitForTimeout(250);
 const after=(await page.evaluate(()=>window.OneGameTest.snapshot())).units.filter(u=>u.kind==='paladin').length;
 assert(after===before+1,`[${name}] panel command did not spawn paladin`);

 // 6) Battle loop smoke: coordinates stay finite and simulation advances.
 await call('spawn','red',12);await call('spawn','blue',12);await page.waitForTimeout(1300);
 const snap=await page.evaluate(()=>window.OneGameTest.snapshot());
 assert(snap.units.length>10,`[${name}] spawn/battle loop failed`);
 assert(snap.units.every(u=>Number.isFinite(u.x)&&Number.isFinite(u.y)),`[${name}] invalid unit coordinates`);
 assert(errors.length===0,`[${name}] game runtime errors: ${errors.join(' | ')}`);
 console.log(`RELEASE GATE OK [${name}] assets+panel+spawn+gameplay`);
 await context.close();
}

let browser;
try{
 await waitServer();
 browser=await chromium.launch({headless:true});
 await test(browser,'mobile',{width:390,height:844});
 await test(browser,'desktop',{width:1440,height:900});
 console.log('1GAME RELEASE GATE: ALL CRITICAL FLOWS PASSED');
}finally{if(browser)await browser.close();server.kill('SIGTERM')}
