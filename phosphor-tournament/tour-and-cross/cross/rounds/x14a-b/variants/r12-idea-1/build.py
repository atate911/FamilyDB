# Builds palettes/r12-idea-1.json's "css" from palette.css (comments stripped, whitespace folded).
import json,re,sys
from pathlib import Path
H=Path(__file__).resolve().parent
src=(H/'palette.css').read_text()
src=re.sub(r'/\*.*?\*/','',src,flags=re.S)
src=re.sub(r'\s+',' ',src)
src=re.sub(r'\s*([{};,>])\s*',r'\1',src)
src=src.replace(';}','}')
p=H.parent.parent/'palettes'/'r12-idea-1.json'
d=json.loads(p.read_text())
d['css']=src
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
print('css chars',len(src))
