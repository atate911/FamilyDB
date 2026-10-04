import re, json, os, sys
S=os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.'
JUDGES=[('A','judge16','judge16-key.json'),('B','judge20a','judge20a-key.json'),('C','judge20b','judge20b-key.json')]
HEADS={'what it is':'what','what works':'works',"what doesn't":'doesnt',"what’s beautiful":'beautiful',"what's beautiful":'beautiful',"what's ugly":'ugly',"what’s ugly":'ugly','mark':'mark',"what doesn’t":'doesnt'}
def parse(path):
    t=open(path).read()
    t=t.split('## Part 2')[0]
    out={}
    for m in re.finditer(r'^###\s+(X\d\d)\s*$(.*?)(?=^###\s+X\d\d|\Z)',t,re.S|re.M):
        code,body=m.group(1),m.group(2)
        cur=None; d={}
        for line in body.split('\n'):
            h=re.match(r'^\*\*(.+?)\*\*\s*(.*)$',line.strip())
            if h and h.group(1).strip().lower().rstrip(':') in HEADS and (line.strip().startswith('**')):
                cur=HEADS[h.group(1).strip().lower().rstrip(':')]; d.setdefault(cur,''); rest=h.group(2).strip()
                if rest: d[cur]+=rest+'\n'
            elif cur: d[cur]+=line+'\n'
        for k in d: d[k]=d[k].strip()
        out[code]=d
    return out
R={}
for j,folder,keyf in JUDGES:
    rp=f'{folder}/review.md'
    if not os.path.exists(rp): print('missing',rp); continue
    key=json.load(open(keyf)); rv=parse(rp)
    for code,d in rv.items():
        did=key[code]
        mk=d.get('mark','')
        m=re.search(r'(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10',mk) or re.search(r'(\d+(?:\.\d+)?)',mk)
        mark=float(m.group(1)) if m else None
        text=re.sub(r'^\s*\d+(?:\.\d+)?\s*(?:/\s*10|out of 10)?[.,:;—-]*\s*','',mk).strip()
        e=R.setdefault(did,{'marks':{},'words':{}})
        e['marks'][j]=mark
        e['words'][j]={'what':d.get('what',''),'works':d.get('works',''),'doesnt':d.get('doesnt',''),'beautiful':d.get('beautiful',''),'ugly':d.get('ugly',''),'markText':text}
    print(j,len(rv),'designs parsed')
json.dump(R,open('reviews.json','w'),indent=1)
bad=[(k,j) for k,v in R.items() for j,m in v['marks'].items() if m is None]
print('designs',len(R),'unparsed marks',bad)
