from pathlib import Path
import re

p=Path('game.html')
s=p.read_text(encoding='utf-8')
marker='/* facing-combat-v2 */'
if marker in s:
    print('facing v2 already applied')
    raise SystemExit(0)

# Add universal 8-way direction helpers without touching targeting or spawn algorithms.
anchor="function paladinDirection(u,dx,dy,dt=.016)"
pos=s.find(anchor)
if pos<0:
    raise SystemExit('paladinDirection anchor not found')
helper="""const FACING_ORDER=['e','se','s','sw','w','nw','n','ne'];
function wantedDir(dx,dy,fallback='e'){
  if(Math.abs(dx)<.35&&Math.abs(dy)<.35)return fallback;
  const a=Math.atan2(dy,dx)*180/Math.PI;
  if(a>=-22.5&&a<22.5)return'e';
  if(a>=22.5&&a<67.5)return'se';
  if(a>=67.5&&a<112.5)return's';
  if(a>=112.5&&a<157.5)return'sw';
  if(a>=157.5||a<-157.5)return'w';
  if(a>=-157.5&&a<-112.5)return'nw';
  if(a>=-112.5&&a<-67.5)return'n';
  return'ne';
}
function rotateFacing(u,desired,dt=.016){
  if(!u.faceDir)u.faceDir=u.team==='red'?'e':'w';
  if(!desired||desired===u.faceDir){u.faceTurn=0;u.dir8=u.faceDir;return true}
  u.faceTurn=(u.faceTurn||0)+dt;
  const stepTime=.12;
  if(u.faceTurn<stepTime){u.dir8=u.faceDir;return false}
  u.faceTurn=0;
  const a=FACING_ORDER.indexOf(u.faceDir),b=FACING_ORDER.indexOf(desired);
  if(a<0||b<0){u.faceDir=desired;u.dir8=desired;return true}
  const cw=(b-a+8)%8,ccw=(a-b+8)%8;
  u.faceDir=FACING_ORDER[(a+(cw<=ccw?1:-1)+8)%8];
  u.dir8=u.faceDir;
  u.frame=0;
  return u.faceDir===desired;
}
/* facing-combat-v2 */
"""
s=s[:pos]+helper+s[pos:]

# Paladin renderer should use resolved facing instead of recalculating/teleporting orientation.
old="const dx=Number.isFinite(u.animDx)?u.animDx:(targetX-u.x),dy=Number.isFinite(u.animDy)?u.animDy:0,dirName=paladinDirection(u,dx,dy,dt),group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;u.dir8=dirName;"
new="const dirName=u.dir8||u.faceDir||'w',group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;"
if old not in s:
    raise SystemExit('paladin renderer anchor not found')
s=s.replace(old,new,1)

# Initialize facing state on regular mobs and paladin.
s=s.replace("facing:team==='red'?1:-1})", "facing:team==='red'?1:-1,faceDir:team==='red'?'e':'w',faceTurn:0,dir8:team==='red'?'e':'w'})", 1)
s=s.replace("facing:-1,damageMul:4", "facing:-1,faceDir:'w',faceTurn:0,dir8:'w',damageMul:4", 1)

# Normal mobs use the nearest horizontal representation available in their current art.
old2="const frames=u.frames||(u.team==='red'?RED_FRAMES:BLUE_FRAMES),dir=targetX<u.x?-1:1,native=u.team==='red'?1:-1;if(u.facing!==dir){u.facing=dir;img.style.transform=`scaleX(${dir*native})`}"
new2="const frames=u.frames||(u.team==='red'?RED_FRAMES:BLUE_FRAMES),fd=u.dir8||u.faceDir||(u.team==='red'?'e':'w'),dir=(fd==='w'||fd==='nw'||fd==='sw')?-1:(fd==='e'||fd==='ne'||fd==='se')?1:(u.facing||1),native=u.team==='red'?1:-1;if(u.facing!==dir){u.facing=dir;img.style.transform=`scaleX(${dir*native})`}"
if old2 not in s:
    raise SystemExit('regular facing anchor not found')
s=s.replace(old2,new2,1)

# Minimal combat change: preserve current targeting/movement. At contact, turn first; damage only after facing target.
needle="const rawTx=target.x,rawTy=target.y,dx=rawTx-u.x,dy=rawTy-u.y,d=Math.hypot(dx,dy)||.001,ur=unitRadius(u),tr=isCastle?0:unitRadius(target),stopRadius=isCastle?(ur+4):(ur+tr+5);let moving=false;if(d<=stopRadius){u.attackingCastle=isCastle;if(!u.fighting){u.fighting=true;u.el.classList.add('fight')}u.animDx=dx;u.animDy=dy;if(u.atk<=0){u.atk=ATTACK_CD;if(isCastle)hitCastle(u.team==='red'?'blue':'red',CASTLE_DAMAGE*(u.castleDamageMul||1));else{target.hp-=UNIT_DAMAGE*(u.damageMul||1);if(target.hp<=0)kill(target)}}}else{moving=true;u.attackingCastle=false;if(u.fighting){u.fighting=false;u.el.classList.remove('fight')}let vx=dx/d,vy=dy/d;u.x+=vx*UNIT_SPEED*(u.speedMul||1)*dt;u.y+=vy*UNIT_SPEED*(u.speedMul||1)*dt;u.animDx=rawTx-u.x;u.animDy=rawTy-u.y}"
replacement="const rawTx=target.x,rawTy=target.y,dx=rawTx-u.x,dy=rawTy-u.y,d=Math.hypot(dx,dy)||.001,ur=unitRadius(u),tr=isCastle?0:unitRadius(target),stopRadius=isCastle?(ur+4):(ur+tr+5),desiredDir=wantedDir(dx,dy,u.faceDir||(u.team==='red'?'e':'w')),facingReady=rotateFacing(u,desiredDir,dt);let moving=false;if(d<=stopRadius){u.attackingCastle=isCastle;u.animDx=dx;u.animDy=dy;if(!facingReady){if(u.fighting){u.fighting=false;u.el.classList.remove('fight')}}else{if(!u.fighting){u.fighting=true;u.el.classList.add('fight')}if(u.atk<=0){u.atk=ATTACK_CD;if(isCastle)hitCastle(u.team==='red'?'blue':'red',CASTLE_DAMAGE*(u.castleDamageMul||1));else{target.hp-=UNIT_DAMAGE*(u.damageMul||1);if(target.hp<=0)kill(target)}}}}else{moving=true;u.attackingCastle=false;if(u.fighting){u.fighting=false;u.el.classList.remove('fight')}let vx=dx/d,vy=dy/d;u.x+=vx*UNIT_SPEED*(u.speedMul||1)*dt;u.y+=vy*UNIT_SPEED*(u.speedMul||1)*dt;u.animDx=rawTx-u.x;u.animDy=rawTy-u.y}"
if needle not in s:
    raise SystemExit('combat loop anchor not found')
s=s.replace(needle,replacement,1)

# Version bump in manifest if present.
s=s.replace("version:'0.6'","version:'0.6.1'",1)

p.write_text(s,encoding='utf-8')
print('facing combat v2 applied')
