from pathlib import Path
import os,re
p=Path('game.html')
s=p.read_text(encoding='utf-8')
run=os.environ.get('GAME_BUILD_PATCH') or os.environ.get('GITHUB_RUN_NUMBER') or '0'
version=f'0.2.{int(run)}'
# HUD beta label
s=re.sub(r'content:\"BETA 0\.2\.\d+\"',f'content:\"BETA {version}\"',s,count=1)
# Keep the style id non-versioned so future builds can replace cleanly.
s=re.sub(r'id=\"beta-version-v\d+\"','id=\"beta-version-auto\"',s,count=1)
# Manifest reports the same approved build version.
s=re.sub(r"version:'[0-9]+\.[0-9]+\.[0-9]+'",f"version:'{version}'",s,count=1)
p.write_text(s,encoding='utf-8')
print(f'stamped approved build version: BETA {version}')
