import html, json, markdown, re, os
G = [
 ('everyday','Everyday',[('home','Home'),('chat','Chat with Vera'),('ideas','Ideas'),('idea','An idea'),('idea-new','New idea'),('idea-edit','Change an idea'),('plans','Plans · month'),('plans-list','Plans · list'),('restaurants','Restaurants'),('todo','To do'),('todo-edit','Change a to-do'),('wishes','Wish lists'),('wishes-maya','Maya’s wishes, for a parent'),('memory','What Vera knows'),('more','More (phone)')]),
 ('parent','A parent who isn’t an admin',[('home-parent','Alex’s Home'),('more-parent','More (phone)')]),
 ('kids','A kid’s pages',[('home-kid','Maya’s Home'),('chat-kid','Maya’s chat'),('todo-kid','Maya’s to-dos'),('wishes-kid','Maya’s wishes'),('more-kid','More (phone)'),('you-kid','Maya’s password'),('look-kid','Maya’s Look')]),
 ('people','Signing in, people and looks',[('signin','Sign in'),('look','Look: choose yours, it follows you'),('you','Your password'),('you-first','First sign-in'),('password-shown','A starting password, shown once'),('family','Family'),('member','Add or change a person'),('grownups','For grown-ups (a kid opening Settings)')]),
 ('behind','Behind the scenes',[('status','Status'),('activity','One message’s history'),('settings','Settings'),('settings-general','General'),('settings-model','AI model'),('settings-spending','Spending'),('settings-messages','Messages'),('settings-lookups','Lookups'),('settings-personality','Personality and family'),('settings-connections','Connections'),('settings-security','Sign-in and security'),('settings-history','What has changed')]),
 ('setup','Setting up a new install',[('setup','Setting up'),('setup-you','1 · You'),('setup-password','2 · Password'),('setup-model','3 · AI model'),('setup-home','4 · Home'),('setup-telegram','5 · Telegram'),('setup-telegram-link','5 · Telegram, waiting for your phone'),('setup-family','6 · Family'),('setup-calendar','7 · Calendar'),('setup-done','Done'),('setup-told','A key that was refused')]),
 ('states','States, errors and type',[('states','States: Vera'),('states-actions','States: after an action'),('states-content','States: empty, busy, long'),('403','Not allowed'),('404','Not found'),('type','Type specimen')]),
]
used=['img/motion-frames.webp']
def fig(base,label,lazy=True,fixed=False,pre='img/'):
    for suf in ['','-dark','-phone','-dark-phone']:
        for p in ([pre] if fixed else ['img/','img/ag/']):
            used.append(f'{p}{base}{suf}.webp')
    lz=' loading="lazy"' if lazy else ''
    fx=' data-fixed="1"' if fixed else ''
    return (f'<figure class="shot" data-base="{pre}{base}"{fx}><div class="frame"><img src="{pre}{base}.webp" alt="{html.escape(label)}" width="1280" height="800"{lz}></div>'
            f'<figcaption><span>{html.escape(label)}</span><button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure>')
secs=[]
for i,(gid,gname,pages) in enumerate(G):
    figs=''.join(fig(p,l,lazy=(i>0)) for p,l in pages)
    secs.append(f'<section id="{gid}" class="grp" aria-labelledby="h-{gid}"><h2 id="h-{gid}">{gname} <span class="n">{len(pages)}</span></h2><div class="grid">{figs}</div></section>')
secs.append(f'''<section id="motion" class="grp" aria-labelledby="h-motion"><h2 id="h-motion">Motion</h2><p class="note">Screenshots can’t move, so here is each motion in place, and Vera’s sign typing itself in, frame by frame, in Kitchen Table (top rows) and Afterglow (bottom rows). It types once as Home opens, then its cursor blinks and rests; it loops only while she is writing back. What you just did lights and fades over a second; where a link lands lights and fades; the wordmark’s cursor blinks for a few seconds, then stays lit. Everything stops for anyone who asks their device for less motion.</p><div class="grid">{fig('motion','The motion sheet')}<figure class="shot" data-base="img/motion-frames" data-fixed="1"><div class="frame"><img src="img/motion-frames.webp" alt="Vera’s sign typing itself in, frame by frame" width="1280" height="800" loading="lazy"></div><figcaption><span>Vera’s sign, frame by frame</span><button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure></div></section>''')
th=[('palette-kitchen','Kitchen Table · palette sheet'),('palette-afterglow','Afterglow · palette sheet'),('palette-rail','Rail yellow · palette sheet'),('palette-midnight','Midnight · palette sheet'),('home--phosphor','Home in Phosphor (today’s default look)'),('home--rail','Home in Rail yellow'),('home--midnight','Home in Midnight'),('home-kid--phosphor','Maya’s Home in Phosphor'),('home-kid--rail','Maya’s Home in Rail yellow'),('home-kid--midnight','Maya’s Home in Midnight')]
thfigs=''.join(fig(p,l,fixed=True,pre='img/looks/') for p,l in th)
secs.append(f'<section id="themes" class="grp" aria-labelledby="h-themes"><h2 id="h-themes">Your built looks, on Kitchen Table</h2><p class="note">Kitchen Table is written as one more look in your <code>themes.css</code>, and the looks already built (Phosphor, Rail yellow, Midnight and the rest) recolour it without changes. Each person’s choice will be stored with them and follow them to every device.</p><div class="grid">{thfigs}</div></section>')
md=open('HANDOFF.md').read()
hand=markdown.markdown(md,extensions=['tables','fenced_code'])
hand=re.sub(r'<h1>.*?</h1>','',hand,count=1)
open('index.html','w').write(open('page.tpl.html').read().replace('<!--SECTIONS-->','\n'.join(secs)).replace('<!--HANDOFF-->',hand))
used=[u for u in dict.fromkeys(used) if os.path.exists(u)]
kt=[u for u in used if not u.startswith('img/ag/') and not u.startswith('img/looks/')]
ag=[u for u in used if u.startswith('img/ag/')]
lk=[u for u in used if u.startswith('img/looks/')]
for n,l in [('fa',kt),('fb',ag),('fc',lk)]: open(n+'.json','w').write(json.dumps([{'path':k} for k in l]))
print(len(kt),len(ag),len(lk), sum(os.path.getsize(u) for u in used)//1024,'KB')
