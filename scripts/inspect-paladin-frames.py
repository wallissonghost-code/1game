from pathlib import Path
from PIL import Image

ROOT=Path('assets/mobs/special/paladin/blue')
# compact 18x22 symbolic preview per frame. Palette keeps the visually useful armor colors.
def sym(r,g,b,a):
    if a < 28: return ' '
    mx=max(r,g,b); mn=min(r,g,b)
    if b>r*1.18 and b>g*1.08 and b>80: return 'B'   # blue plume/cape/armor
    if r>150 and g>125 and b<120 and r> b*1.35: return 'G' # gold
    if r>185 and g>185 and b>175 and mx-mn<45: return 'W'  # white fur/highlight
    if mx<78: return 'D'                                  # dark body/shadow
    if b>105 and r<150: return 'b'
    return '.'

for i in range(1,33):
    p=ROOT/f'frame_{i:03d}.png'
    im=Image.open(p).convert('RGBA')
    # crop alpha content first so relative posture is readable
    alpha=im.getchannel('A')
    box=alpha.getbbox()
    if box: im=im.crop(box)
    im.thumbnail((18,22), Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(18,22),(0,0,0,0))
    x=(18-im.width)//2; y=22-im.height
    canvas.alpha_composite(im,(x,y))
    print(f'\n=== FRAME {i:03d} ===')
    for yy in range(22):
        row=''.join(sym(*canvas.getpixel((xx,yy))) for xx in range(18))
        print(row.rstrip())
