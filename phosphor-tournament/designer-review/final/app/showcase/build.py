import html, json, markdown, re
G = [
 ('everyday','Everyday',[('home','Home'),('chat','Chat with Vera'),('ideas','Ideas'),('idea','An idea'),('idea-new','New idea'),('idea-edit','Change an idea'),('plans','Plans · month'),('plans-list','Plans · list'),('restaurants','Restaurants'),('todo','To do'),('todo-edit','Change a to-do'),('wishes','Wish lists'),('wishes-maya','Maya’s wishes, for a parent'),('memory','What Vera knows'),('more','More (phone)')]),
 ('kids','A kid’s pages',[('home-kid','Maya’s Home'),('chat-kid','Maya’s chat'),('todo-kid','Maya’s to-dos'),('wishes-kid','Maya’s wishes'),('more-kid','More (phone)'),('you-kid','You')]),
 ('people','Signing in and people',[('signin','Sign in'),('you','You'),('you-first','First sign-in'),('password-shown','A starting password, shown once'),('family','Family'),('member','Add or change a person'),('grownups','For grown-ups (a kid opening Settings)')]),
 ('behind','Behind the scenes',[('status','Status'),('activity','One message’s history'),('settings','Settings'),('settings-general','General · and the family’s theme'),('settings-model','AI model'),('settings-spending','Spending'),('settings-messages','Messages'),('settings-lookups','Lookups'),('settings-personality','Personality and family'),('settings-connections','Connections'),('settings-security','Sign-in and security'),('settings-history','What has changed')]),
 ('setup','Setting up a new install',[('setup','Setting up'),('setup-you','1 · You'),('setup-password','2 · Password'),('setup-model','3 · AI model'),('setup-home','4 · Home'),('setup-telegram','5 · Telegram'),('setup-telegram-link','5 · Telegram, waiting for your phone'),('setup-family','6 · Family'),('setup-calendar','7 · Calendar'),('setup-done','Done'),('setup-told','A key that was refused')]),
 ('states','States, errors and type',[('states','States: Vera'),('states-actions','States: after an action'),('states-content','States: empty, busy, long'),('403','Not allowed'),('404','Not found'),('type','Type specimen')]),
]
used=[]
def fig(base,label,lazy=True,themes=False):
    pre='img/themes/' if themes else 'img/'
    for suf in ['','-dark','-phone','-dark-phone']: used.append(f'{pre}{base}{suf}.webp')
    lz=' loading="lazy"' if lazy else ''
    return (f'<figure class="shot" data-base="{pre}{base}"><div class="frame"><img src="{pre}{base}.webp" alt="{html.escape(label)}" width="1280" height="800"{lz}></div>'
            f'<figcaption><span>{html.escape(label)}</span><button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure>')
secs=[]
for i,(gid,gname,pages) in enumerate(G):
    figs=''.join(fig(p,l,lazy=(i>0)) for p,l in pages)
    secs.append(f'<section id="{gid}" class="grp" aria-labelledby="h-{gid}"><h2 id="h-{gid}">{gname} <span class="n">{len(pages)}</span></h2><div class="grid">{figs}</div></section>')
th=[('palette-kitchen-table','Kitchen Table · palette sheet'),('palette-rail','Rail yellow (test port) · palette sheet'),('palette-midnight','Midnight (test port) · palette sheet'),('home--rail','Home · Rail yellow'),('home--midnight','Home · Midnight'),('home-kid--midnight','Maya’s Home · Midnight'),('plans--rail','Plans · Rail yellow'),('plans--midnight','Plans · Midnight'),('home-kid--rail','Maya’s Home · Rail yellow')]
thfigs=''.join(fig(p,l,themes=True) for p,l in th)
secs.append(f'<section id="themes" class="grp" aria-labelledby="h-themes"><h2 id="h-themes">Built for themes <span class="n">proof</span></h2><p class="note">Every colour now lives in one theme file. Two earlier palettes were ported only to test that: their colours moved into the new names, not redesigned. Rail yellow fails the colour-blind check at night, which is the test doing its job.</p><div class="grid">{thfigs}</div></section>')
md=open('HANDOFF.md').read()
hand=markdown.markdown(md,extensions=['tables','fenced_code'])
hand=re.sub(r'<h1>.*?</h1>','',hand,count=1)
t=open('page.tpl.html').read().replace('<!--SECTIONS-->','\n'.join(secs)).replace('<!--HANDOFF-->',hand)
open('index.html','w').write(t)
import os
used=[u for u in dict.fromkeys(used) if os.path.exists(u)]
json.dump({u:u for u in used},open('files.json','w'))
print(len(used), sum(os.path.getsize(u) for u in used)//1024,'KB')
