from pathlib import Path

p = Path('game.html')
s = p.read_text(encoding='utf-8')

old = ".unit.paladin .paladin-sprite{width:62px;height:72px;left:-21px;top:-33px;"
new = ".unit.paladin .paladin-sprite{width:50px;height:58px;left:-15px;top:-22px;"

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('paladin sprite size rule not found')

p.write_text(s, encoding='utf-8')
print('paladin visual size reduced from 62x72 to 50x58; gameplay untouched')
