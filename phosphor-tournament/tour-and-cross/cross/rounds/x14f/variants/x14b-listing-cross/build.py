# Builds variants/x14b-listing-cross/sheet.css: today's stylesheet themed with this palette's tokens
# (theme.py, so the kit's light is re-tinted as on a main palette), then palette.css (the parent's
# refinements, edited in place, and this cross's own), comments stripped and whitespace folded.
import json,re,subprocess,sys
from pathlib import Path
V=Path(__file__).resolve().parent
X=V.parent.parent
pal=X/'palettes'/'x14b-listing-cross.json'
d=json.loads(pal.read_text())
base={k:v for k,v in d.items() if k not in ('css','sheet')}
(V/'_base.json').write_text(json.dumps(base))
subprocess.run([sys.executable,str(X/'theme.py'),str(V/'_base.json'),str(V/'_base.css')],check=True,cwd=X)
def fold(s):
    s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
    s=re.sub(r'\s+',' ',s)
    s=re.sub(r'\s*([{};,>])\s*',r'\1',s)
    s=s.replace(';}','}')
    return s.strip()
b=(V/'_base.css').read_text()
b=re.sub(r'@font-face\s*\{.*?\}','',b,flags=re.S)
own=fold((V/'palette.css').read_text())
sheet=fold(b)+'\n'+own+'\n'
(V/'sheet.css').write_text(sheet)
d.pop('css',None); d['sheet']='variants/x14b-listing-cross/sheet.css'
pal.write_text(json.dumps(d,indent=1,ensure_ascii=False))
print('base',len(fold(b)),'own',len(own),'sheet',len(sheet))
