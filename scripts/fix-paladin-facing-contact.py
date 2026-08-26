from pathlib import Path
import re

p=Path('game.html')
s=p.read_text(encoding='utf-8')

# Canonical regular-mob asset paths only; no gameplay tuning here.
s=s.replace("const BLUE_FRAMES=Array.from({length:8},(_,i)=>`./assets/mobs/regular/blue/frame_${String(i+1).padStart(3,'0')}%202.png`);","const BLUE_FRAMES=Array.from({length:8},(_,i)=>`./assets/mobs/regular/blue/frame_${String(i+1).padStart(3,'0')}.png`);")
s=s.replace("%202.png`);const PALADIN_BLUE_FRAMES",".png`);const PALADIN_BLUE_FRAMES",1)

# Real sprite taxonomy: 4 directions x 8 frames.
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

# SINGLE SOURCE OF TRUTH for any direction stored/exposed by the Paladin.
# Diagonal movement remains physically possible, but visual/state direction is cardinal.
cardinal_block=r'''function cardinalFacing(d,fallback='w'){
  if(d==='nw'||d==='sw')return'w';
  if(d==='ne'||d==='se')return'e';
  return(d==='n'||d==='s'||d==='e'||d==='w')?d:fallback;
}
function setFacingState(u,d,fallback){
  const c=cardinalFacing(d,fallback||u.faceDir||(u.team==='red'?'e':'w'));
  u.faceDir=c;u.dir8=c;
  if(u.kind==='paladin')u.palDir=c;
  return c;
}
function rotateFacing(u,desired,dt=.016){
  const fallback=u.team==='red'?'e':'w';
  const current=setFacingState(u,u.faceDir||u.dir8||u.palDir||fallback,fallback);
  desired=cardinalFacing(desired,current);
  if(desired===current){u.facePending=desired;u.facePendingTime=0;u.faceTurn=0;setFacingState(u,current,fallback);return true}
  if(u.facePending!==desired){u.facePending=desired;u.facePendingTime=0;setFacingState(u,current,fallback);return false}
  u.facePendingTime=(u.facePendingTime||0)+dt;
  const intentHold=(typeof perfAlive!=='undefined'&&perfAlive>70)?.10:.16;
  if(u.facePendingTime<intentHold){setFacingState(u,current,fallback);return false}
  u.faceTurn=(u.faceTurn||0)+dt;
  const stepTime=(typeof perfAlive!=='undefined'&&perfAlive>70)?.085:.13;
  if(u.faceTurn<stepTime){setFacingState(u,current,fallback);return false}
  u.faceTurn=0;
  const order=['n','e','s','w'];
  const a=order.indexOf(current),b=order.indexOf(desired);
  if(a<0||b<0){setFacingState(u,desired,fallback);u.frame=0;return true}
  const cw=(b-a+4)%4,ccw=(a-b+4)%4;
  const next=order[(a+(cw<=ccw?1:-1)+4)%4];
  setFacingState(u,next,fallback);u.frame=0;
  return next===desired;
}'''

start=s.find("function rotateFacing(u,desired,dt=.016){")
if start!=-1:
    # Include a pre-existing cardinalFacing immediately before rotateFacing if present.
    cstart=s.rfind("function cardinalFacing(",0,start)
    block_start=cstart if cstart!=-1 and start-cstart<600 else start
    end=s.find("\nfunction paladinDirection",start)
    if end!=-1:
        s=s[:block_start]+cardinal_block+s[end:]

# palDir must never retain a diagonal either, even if this legacy helper is called later.
pal_start=s.find("function paladinDirection(u,dx,dy,dt=.016){")
if pal_start!=-1:
    pal_end=s.find("\nfunction animateUnit",pal_start)
    if pal_end!=-1:
        pal_fn=r'''function paladinDirection(u,dx,dy,dt=.016){
  const fallback=u.palDir||u.faceDir||'w';
  if(Math.abs(dx)<.35&&Math.abs(dy)<.35)return setFacingState(u,fallback,'w');
  return setFacingState(u,wantedDir(dx,dy,fallback),'w');
}'''
        s=s[:pal_start]+pal_fn+s[pal_end:]

# Animation reads only normalized state.
s=s.replace("const dirName=u.dir8||u.faceDir||'w',group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;","const dirName=cardinalFacing(u.dir8||u.faceDir||u.palDir||'w','w'),group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;",1)
s=s.replace("const dirName=cardinalFacing(u.dir8||u.faceDir||'w','w'),group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;","const dirName=cardinalFacing(u.dir8||u.faceDir||u.palDir||'w','w'),group=PALADIN_DIRS[dirName]||PALADIN_DIRS.w;",1)

# Public QA snapshot must expose exactly the stored cardinal states, never stale diagonals.
old="units:alive.map(u=>({team:u.team,kind:u.kind||'mob',x:u.x,y:u.y,hp:u.hp,formationLane:u.formationLane,formationRow:u.formationRow,dir8:u.dir8??null,targetIsCastle:!!u.targetIsCastle,attackingCastle:!!u.attackingCastle}))"
new="units:alive.map(u=>({team:u.team,kind:u.kind||'mob',x:u.x,y:u.y,hp:u.hp,formationLane:u.formationLane,formationRow:u.formationRow,dir8:cardinalFacing(u.dir8,u.team==='red'?'e':'w'),faceDir:cardinalFacing(u.faceDir,u.team==='red'?'e':'w'),palDir:u.kind==='paladin'?cardinalFacing(u.palDir||u.faceDir,'w'):null,targetIsCastle:!!u.targetIsCastle,attackingCastle:!!u.attackingCastle}))"
if old in s:s=s.replace(old,new,1)

# Expose normalization only for deterministic QA of all direction cases.
s=s.replace("reset(){reset();return true},","normalizeDir(d,fallback='w'){return cardinalFacing(d,fallback)},\n  reset(){reset();return true},",1)

# Preserve castle approach and all other gameplay as-is.
# Only normalize state after separation/collision in case any future helper touched direction.
s=s.replace("applyFreeSeparation(u);resolveCastleBodies(u);animateUnit(u,dt,moving,rawTx);","applyFreeSeparation(u);resolveCastleBodies(u);if(u.kind==='paladin')setFacingState(u,u.dir8||u.faceDir||u.palDir||'w','w');animateUnit(u,dt,moving,rawTx);",1)

# Organized panel preview paths only.
s=s.replace("https://wallissonghost-code.github.io/1game/assets/mobs/red/frame_001.png","https://wallissonghost-code.github.io/1game/assets/mobs/regular/red/frame_001.png")
s=s.replace("https://wallissonghost-code.github.io/1game/assets/mobs/blue/frame_001%202.png","https://wallissonghost-code.github.io/1game/assets/mobs/regular/blue/frame_001.png")

marker='/* paladin-cardinal-state-v3 */'
if marker not in s:
    for old_marker in ['/* paladin-cardinal-facing-v2 */','/* paladin-4dir-8frames-v1 */','/* facing-combat-v2 */']:
        if old_marker in s:
            s=s.replace(old_marker,marker+old_marker,1)
            break

p.write_text(s,encoding='utf-8')
print('patched game.html: single cardinal state for dir8/faceDir/palDir; no diagonal state leakage')
