from pathlib import Path

p = Path('game.html')
s = p.read_text(encoding='utf-8')

# Keep the victory overlay high, including the fullscreen HUD override.
s = s.replace('.victory-overlay{position:absolute;inset:0;z-index:30;', '.victory-overlay{position:absolute;inset:0;z-index:100;', 1)
s = s.replace('.clash,.castle,.unit,.victory-overlay{z-index:4}', '.clash,.castle,.unit{z-index:4}.victory-overlay{z-index:100!important}', 1)

anchor = "function scheduleNextRound(){clearTimeout(roundResetTimer);clearInterval(roundCountdownTimer);let left=5;const c=$('nextRoundCount');if(c)c.textContent=left;roundCountdownTimer=setInterval(()=>{left--;if(c)c.textContent=Math.max(0,left);if(left<=0)clearInterval(roundCountdownTimer)},1000);roundResetTimer=setTimeout(()=>reset(),5000)}"
cleanup = "function clearRoundUnitsImmediate(){const doomed=units;units=[];for(const u of doomed){u.attackingCastle=false;u.fighting=false;u.target=null;u.targetIsCastle=false;u.atk=0;u.anim=0;if(u.img){u.img.style.animation='none';u.img.style.transition='none'}if(u.el){u.el.classList.remove('fight');u.el.style.animation='none';u.el.style.transition='none';u.el.style.display='none';u.el.remove()}}}"
if cleanup not in s:
    if anchor not in s:
        raise SystemExit('scheduleNextRound anchor not found')
    s = s.replace(anchor, anchor + cleanup, 1)

old_show = "function showVictory(winner,reason='CASTELO DESTRUÍDO'){if(ended)return;ended=true;if(winner==='red')redStars++;"
new_show = "function showVictory(winner,reason='CASTELO DESTRUÍDO'){if(ended)return;ended=true;clearRoundUnitsImmediate();if(winner==='red')redStars++;"
if old_show in s:
    s = s.replace(old_show, new_show, 1)
elif new_show not in s:
    raise SystemExit('showVictory prefix not found')

# Do not run AI/movement/animation while a result is open. Reset keeps the RAF alive.
old_loop = "function loop(now){if(document.hidden){last=now;requestAnimationFrame(loop);return}if(paused){last=now;requestAnimationFrame(loop);return}"
new_loop = "function loop(now){if(document.hidden){last=now;requestAnimationFrame(loop);return}if(paused||ended){last=now;requestAnimationFrame(loop);return}"
if old_loop in s:
    s = s.replace(old_loop, new_loop, 1)
elif new_loop not in s:
    raise SystemExit('loop guard not found')

# QA-only diagnostics/helpers. They do not alter normal gameplay rules.
needle = "finishTime(){finishByTime();return true},\n  pause(value=true){paused=!!value;return paused}"
if needle in s:
    repl = "finishTime(){finishByTime();return true},\n  placePaladinsNearCastle(){const pals=units.filter(u=>u.kind==='paladin');const cy=battle.clientHeight*.48;pals.forEach((u,i)=>{u.x=112+(i%4)*18;u.y=cy+(Math.floor(i/4)-2)*28;u.el.style.transform=`translate3d(${u.x}px,${u.y}px,0)`});return pals.length},\n  victoryDiagnostics(){const overlay=$('victoryOverlay'),card=overlay?.querySelector('.victory-card'),els=[...battle.querySelectorAll('.unit')];return{ended,unitCount:els.length,hiddenCount:els.filter(el=>getComputedStyle(el).display==='none'||getComputedStyle(el).visibility==='hidden').length,activeAnimations:els.reduce((n,el)=>n+el.getAnimations({subtree:true}).filter(a=>a.playState==='running').length,0),overlayShown:!!overlay?.classList.contains('show'),overlayZ:Number(getComputedStyle(overlay).zIndex||0),cardRect:card?card.getBoundingClientRect().toJSON():null}},\n  pause(value=true){paused=!!value;return paused}"
    s = s.replace(needle, repl, 1)

p.write_text(s, encoding='utf-8')
print('victory cleanup patched: immediate DOM removal before overlay, no fade')
