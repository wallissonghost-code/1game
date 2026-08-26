from pathlib import Path
import os

p=Path('game.html')
s=p.read_text(encoding='utf-8')

# Canonical regular-mob asset paths.
s=s.replace("const BLUE_FRAMES=Array.from({length:8},(_,i)=>`./assets/mobs/regular/blue/frame_${String(i+1).padStart(3,'0')}%202.png`);","const BLUE_FRAMES=Array.from({length:8},(_,i)=>`./assets/mobs/regular/blue/frame_${String(i+1).padStart(3,'0')}.png`);")
s=s.replace("%202.png`);const PALADIN_BLUE_FRAMES",".png`);const PALADIN_BLUE_FRAMES",1)

# The actual 32 PNGs are 4 directions x 8 animation frames:
# 001-008 left, 009-016 back/up, 017-024 front/down, 025-032 right.
# Diagonal movement never gets its own visual state because diagonal art does not exist.
old_maps=[
"const PALADIN_DIRS={s:[0,1,2,3],se:[4,5,6,7],e:[8,9,10,11],ne:[12,13,14,15],n:[16,17,18,19],nw:[20,21,22,23],w:[24,25,26,27],sw:[28,29,30,31]};",
"const PALADIN_DIRS={s:[0,1,2,3],e:[4,5,6,7],n:[8,9,10,11],w:[12,13,14,15],se:[16,17,18,19],ne:[20,21,22,23],nw:[24,25,26,27],sw:[28,29,30,31]};",
"const PALADIN_DIRS={w:[0,1,2,3,4,5,6,7],n:[8,9,10,11,12,13,14,15],s:[16,17,18,19,20,21,22,23],e:[24,25,26,27,28,29,30,31],nw:[0,1,2,3,4,5,6,7],sw:[0,1,2,3,4,5,6,7],ne:[24,25,26,27,28,29,30,31],se:[24,25,26,27,28,29,30,31]};"
]
new_map="const PALADIN_DIRS={w:[0,1,2,3,4,5,6,7],n:[8,9,10,11,12,13,14,15],s:[16,17,18,19,20,21,22,23],e:[24,25,26,27,28,29,30,31]};"
for old in old_maps:
    if old in s:
        s=s.replace(old,new_map,1)
        break

# Replace the old 8-direction turner with a true 4-direction state machine.
# A diagonal target picks the horizontal side it is actually on. It must remain requested
# briefly before a turn starts, preventing crowd/separation jitter from spinning the unit.
start=s.find("function rotateFacing(u,desired,dt=.016){")
if start!=-1:
    end=s.find("\nfunction ", start+1)
    if end!=-1:
        new_rotate=r'''function cardinalFacing(d,fallback='w'){
  if(d==='nw'||d==='sw')return'w';
  if(d==='ne'||d==='se')return'e';
  return(d==='n'||d==='s'||d==='e'||d==='w')?d:fallback;
}
function rotateFacing(u,desired,dt=.016){
  if(!u.faceDir)u.faceDir=u.team==='red'?'e':'w';
  u.faceDir=cardinalFacing(u.faceDir,u.team==='red'?'e':'w');
  desired=cardinalFacing(desired,u.faceDir);
  if(desired===u.faceDir){
    u.facePending=desired;u.facePendingTime=0;u.faceTurn=0;u.dir8=u.faceDir;return true;
  }
  if(u.facePending!==desired){
    u.facePending=desired;u.facePendingTime=0;u.dir8=u.faceDir;return false;
  }
  u.facePendingTime=(u.facePendingTime||0)+dt;
  const intentHold=(typeof perfAlive!=='undefined'&&perfAlive>70)?.10:.16;
  if(u.facePendingTime<intentHold){u.dir8=u.faceDir;return false}
  u.faceTurn=(u.faceTurn||0)+dt;
  const stepTime=(typeof perfAlive!=='undefined'&&perfAlive>70)?.085:.13;
  if(u.faceTurn<stepTime){u.dir8=u.faceDir;return false}
  u.faceTurn=0;
  const order=['n','e','s','w'];
  const a=order.indexOf(u.faceDir),b=order.indexOf(desired);
  if(a<0||b<0){u.faceDir=desired;u.dir8=u.faceDir;u.frame=0;return true}
  const cw=(b-a+4)%4,ccw=(a-b+4)%4;
  u.faceDir=order[(a+(cw<=ccw?1:-1)+4)%4];
  u.dir8=u.faceDir;
  u.frame=0;
  return u.faceDir===desired;
}'''
        s=s[:start]+new_rotate+s[end:]

# Keep animation lookup cardinal even if stale state from an older session exists.
s=s.replace("const dirName=u.dir8||u.faceDir||'w',group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;","const dirName=cardinalFacing(u.dir8||u.faceDir||'w','w'),group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;",1)

# Castle pursuit: horizontal while far away, then smooth Y alignment only near the castle.
old_castles=[
"function castlePoint(team,u=null){const cy=battle.clientHeight*.48,y=clamp(u?.y??cy,cy-78,cy+78),front=castleFrontAtY(y)??80;return team==='red'?{x:front,y}:{x:battle.clientWidth-front,y}}",
"function castlePoint(team,u=null){const cy=battle.clientHeight*.48,baseFront=86,baseX=team==='red'?baseFront:battle.clientWidth-baseFront;if(!u)return{x:baseX,y:cy};const far=Math.abs(u.x-baseX)>150;if(far)return{x:baseX,y:u.y};const y=clamp(u.y,cy-78,cy+78),front=castleFrontAtY(y)??72;return team==='red'?{x:front,y}:{x:battle.clientWidth-front,y}}"
]
new_castle="function castlePoint(team,u=null){const cy=battle.clientHeight*.48,baseFront=86,baseX=team==='red'?baseFront:battle.clientWidth-baseFront;if(!u)return{x:baseX,y:cy};const far=Math.abs(u.x-baseX)>150;if(far)return{x:baseX,y:u.y};const y=clamp(u.y,cy-78,cy+78),front=castleFrontAtY(y)??72;return team==='red'?{x:front,y}:{x:battle.clientWidth-front,y}}"
for old in old_castles:
    if old in s:
        s=s.replace(old,new_castle,1)
        break
s=s.replace("function castleFrontAtY(y){const cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54)return 96;if(dy<=78)return 80;return null}","function castleFrontAtY(y){const cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54)return 86;if(dy<=78)return 72;return null}",1)
s=s.replace("stopRadius=isCastle?(ur+4):(ur+tr+5)","stopRadius=isCastle?(ur+1.5):(ur+tr+5)",1)
s=s.replace("const own=castlePoint(u.team),targetCastle=castlePoint(u.team==='red'?'blue':'red');","const own=castlePoint(u.team,u),targetCastle=castlePoint(u.team==='red'?'blue':'red',u);",1)

# Organized panel preview paths.
s=s.replace("https://wallissonghost-code.github.io/1game/assets/mobs/red/frame_001.png","https://wallissonghost-code.github.io/1game/assets/mobs/regular/red/frame_001.png")
s=s.replace("https://wallissonghost-code.github.io/1game/assets/mobs/blue/frame_001%202.png","https://wallissonghost-code.github.io/1game/assets/mobs/regular/blue/frame_001.png")

marker='/* paladin-cardinal-facing-v2 */'
if marker not in s:
    for old_marker in ['/* paladin-4dir-8frames-v1 */','/* paladin-facing-contact-v5 */','/* facing-combat-v2 */']:
        if old_marker in s:
            s=s.replace(old_marker,marker+old_marker,1)
            break

p.write_text(s,encoding='utf-8')
print('patched game.html: cardinal facing only; no fake diagonal rotation; 4x8 paladin frames')
