from pathlib import Path

p=Path('game.html')
s=p.read_text(encoding='utf-8')

# 1) Victory overlay always stays above units.
s=s.replace('.victory-overlay{position:absolute;inset:0;z-index:30;', '.victory-overlay{position:absolute;inset:0;z-index:100;', 1)

# 2) Castle front/contact: proportional to the rendered castle width.
old="function castleFrontAtY(y){const cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54)return 86;if(dy<=78)return 72;return null}function castlePoint(team,u=null){const cy=battle.clientHeight*.48,y=clamp(u?.y??cy,cy-78,cy+78),front=castleFrontAtY(y)??80;return team==='red'?{x:front,y}:{x:battle.clientWidth-front,y}}"
new="function castleContactScale(){const w=battle.querySelector('.castle.red')?.offsetWidth||112;return clamp(w/112,.9,1.18)}function castleFrontAtY(y){const scale=castleContactScale(),cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54*scale)return 68*scale;if(dy<=78*scale)return 58*scale;return null}function castlePoint(team,u=null){const scale=castleContactScale(),cy=battle.clientHeight*.48,y=clamp(u?.y??cy,cy-78*scale,cy+78*scale),front=castleFrontAtY(y)??64*scale,r=u?unitRadius(u):0,gap=u?1.5:0,x=team==='red'?front+r+gap:battle.clientWidth-front-r-gap;return{x,y}}"
if old not in s:
    raise SystemExit('castle front/contact block not found')
s=s.replace(old,new,1)

# Keep the collision body aligned with the same small 1.5 px visual gap.
old="function resolveCastleBodies(u){const r=unitRadius(u),front=castleFrontAtY(u.y);if(front==null)return;const left=front+r+1,right=battle.clientWidth-front-r-1;if(u.x<left)u.x=left;if(u.x>right)u.x=right;}"
new="function resolveCastleBodies(u){const r=unitRadius(u),front=castleFrontAtY(u.y);if(front==null)return;const gap=1.5,left=front+r+gap,right=battle.clientWidth-front-r-gap;if(u.x<left)u.x=left;if(u.x>right)u.x=right;}"
if old not in s:
    raise SystemExit('castle collision block not found')
s=s.replace(old,new,1)

# Reduced castle stop radius: target is now the actual safe contact point, not the castle face.
old="stopRadius=isCastle?(ur+1.5):(ur+tr+5)"
new="stopRadius=isCastle?3.5:(ur+tr+5)"
if old not in s:
    raise SystemExit('castle stopRadius expression not found')
s=s.replace(old,new,1)

# Round-end despawn: freeze via ended=true, fade every unit, then remove from DOM.
anchor="function scheduleNextRound(){clearTimeout(roundResetTimer);clearInterval(roundCountdownTimer);let left=5;const c=$('nextRoundCount');if(c)c.textContent=left;roundCountdownTimer=setInterval(()=>{left--;if(c)c.textContent=Math.max(0,left);if(left<=0)clearInterval(roundCountdownTimer)},1000);roundResetTimer=setTimeout(()=>reset(),5000)}"
despawn="function despawnRoundUnits(){const doomed=[...units];for(const u of doomed){u.attackingCastle=false;u.fighting=false;u.target=null;u.el.classList.remove('fight');u.el.style.pointerEvents='none';u.el.style.transition='opacity .4s ease';u.el.style.opacity='0'}setTimeout(()=>{for(const u of doomed)u.el.remove();const gone=new Set(doomed);units=units.filter(u=>!gone.has(u));update();sendState(true)},420)}"
if despawn not in s:
    if anchor not in s:
        raise SystemExit('scheduleNextRound anchor not found')
    s=s.replace(anchor,anchor+despawn,1)

old="function showVictory(winner,reason='CASTELO DESTRUÍDO'){if(ended)return;ended=true;if(winner==='red')redStars++;"
new="function showVictory(winner,reason='CASTELO DESTRUÍDO'){if(ended)return;ended=true;despawnRoundUnits();if(winner==='red')redStars++;"
if old not in s:
    raise SystemExit('showVictory block not found')
s=s.replace(old,new,1)

# Once the result is up, the simulation must not move or fight any unit.
old="function loop(now){if(document.hidden){last=now;requestAnimationFrame(loop);return}if(paused){last=now;requestAnimationFrame(loop);return}"
new="function loop(now){if(document.hidden){last=now;requestAnimationFrame(loop);return}if(paused||ended){last=now;requestAnimationFrame(loop);return}"
if old not in s:
    raise SystemExit('loop guard not found')
s=s.replace(old,new,1)

# Expose only diagnostics needed by final QA.
needle="finishTime(){finishByTime();return true},\n  pause(value=true){paused=!!value;return paused}"
repl="finishTime(){finishByTime();return true},\n  roundEndDiagnostics(){const overlay=$('victoryOverlay'),unitEls=[...battle.querySelectorAll('.unit')];return{ended,unitCount:unitEls.length,unitOpacity:unitEls.map(el=>getComputedStyle(el).opacity),overlayShown:!!overlay?.classList.contains('show'),overlayZ:Number(getComputedStyle(overlay).zIndex||0),castleScale:castleContactScale(),centerFront:castleFrontAtY(battle.clientHeight*.48),paladinStopRadius:3.5}},\n  pause(value=true){paused=!!value;return paused}"
if needle not in s:
    raise SystemExit('OneGameTest diagnostics anchor not found')
s=s.replace(needle,repl,1)

p.write_text(s,encoding='utf-8')
print('patched final round cleanup + close castle contact: stopRadius=3.5, fade=400ms, remove=420ms')
