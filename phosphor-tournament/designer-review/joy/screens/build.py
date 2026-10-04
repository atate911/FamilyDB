from PIL import Image
import json
T=[('wall','Kitchen Wall, Felt Tip','The family calendar on the kitchen wall, filled in by everyone with their own felt-tip pen: today circled in green, each person’s plans in their bright colour, and things crossed off with a satisfying line.'),
   ('app','Fridge Door','The calendar app made the family’s own: everything worth writing big in a font with a hand in it, people’s colours used like felt-tips, cards like stickers, and whoever is signed in wearing their own colour.')]
DESK=[('home','Home'),('plans','Plans'),('todo','To do'),('chat','Chat'),('ideas','Ideas'),('home-kid','Maya’s Home'),('wishes-kid','Maya’s wishes'),('home-dark','Home at night'),('plans-dark','Plans at night'),('states-actions','The moments: a to-do ticked off and a wish answered')]
PH=[('home-phone','Home'),('plans-phone','Plans'),('home-kid-phone','Maya’s Home'),('wishes-kid-phone','Maya’s wishes'),('home-phone-dark','Home at night')]
used=[]
def img(k,f,label,name,phone,lazy=True):
    p=f'img/{k}/{f}.webp'; used.append(p); w,h=Image.open(p).size
    lz=' loading="lazy"' if lazy else ''
    ph=', phone' if phone else ''
    cls='ph' if phone else 'dt'
    return f'<figure class="{cls}"><img src="{p}" alt="{name}, {label}{ph}" width="{w}" height="{h}"{lz}><figcaption>{label}</figcaption></figure>'
secs=[]
for i,(k,n,idea) in enumerate(T):
    d=''.join(img(k,f,l,n,False) for f,l in DESK)
    p=''.join(img(k,f,l,n,True,lazy=(i>0)) for f,l in PH)
    secs.append(f'<section id="{k}" aria-labelledby="h-{k}"><header class="sh"><h2 id="h-{k}">{n}</h2><p>{idea}</p></header><h3>Phone</h3><div class="phones">{p}</div><h3>Desktop</h3><div class="desk">{d}</div></section>')
t=open('page.tpl.html').read().replace('<!--SECTIONS-->','\n'.join(secs))
open('index.html','w').write(t)
json.dump({u:u for u in sorted(set(used))},open('files.json','w'))
