from pathlib import Path
p=Path('game.html')
s=p.read_text(encoding='utf-8')
repls={
"const PALADIN_DIRS={s:[0,1,2,3],se:[4,5,6,7],e:[8,9,10,11],ne:[12,13,14,15],n:[16,17,18,19],nw:[20,21,22,23],w:[24,25,26,27],sw:[28,29,30,31]};":"const PALADIN_DIRS={s:[0,1,2,3],e:[4,5,6,7],n:[8,9,10,11],w:[12,13,14,15],se:[16,17,18,19],ne:[20,21,22,23],nw:[24,25,26,27],sw:[28,29,30,31]};",
"function castleFrontAtY(y){const cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54)return 96;if(dy<=78)return 80;return null}":"function castleFrontAtY(y){const cy=battle.clientHeight*.48,dy=Math.abs(y-cy);if(dy<=54)return 86;if(dy<=78)return 72;return null}",
"stopRadius=isCastle?(ur+4):(ur+tr+5)":"stopRadius=isCastle?(ur+1.5):(ur+tr+5)"
}
for old,new in repls.items():
    if old not in s:
        raise SystemExit('PATCH ANCHOR NOT FOUND: '+old[:90])
    s=s.replace(old,new,1)
marker='/* paladin-facing-contact-v3 */'
if marker not in s:
    s=s.replace('/* facing-combat-v2 */',marker+'/* facing-combat-v2 */',1)
p.write_text(s,encoding='utf-8')
print('patched game.html: paladin direction map + castle contact')
