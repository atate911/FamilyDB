import html
D = [
 dict(k='green', name='Kitchen Table, green', tag='The final · recommended', idea='Warm paper for the family, a deep green card for Vera with a sun-yellow Send, and small panes of phosphor glass for the FamilyDB mark and Vera’s sign.', ev='Chosen blind over the original A1 by 4 of 4 judges, and with its brand by 4 of 4.', sw=['#F6F1E7','#1E5C4F','#F2C14E','#0E1312'], day='', night='-dark', dayname='Day', nightname='Night'),
 dict(k='tomato', name='Tomato Table', tag='Warmest', idea='The same kitchen table in late summer: cream paper, brown ink, one tomato for everything the family does, and Vera as a small lit screen on warm charcoal.', ev='Its ancestor had the top blind score of twenty (8.5). Not yet judged in this form. Watch for two reds: the tomato button and a late to-do.', sw=['#F8F1E7','#2A201B','#C8461F','#8E2A16'], day='', night='-dark', dayname='Day', nightname='Night'),
 dict(k='afterglow', name='Afterglow', tag='Phosphor first', idea='FamilyDB as a calm green-phosphor screen day and night: Vera’s things glow, and the family’s things sit on the glass in their own colours.', ev='Its ancestors were the best-scored phosphor designs (7.3 to 7.7 blind). Not yet judged in this form. Dark by default, with a light theme.', sw=['#0A100E','#6DFF9C','#E9F1EC','#FFB35C'], day='', night='-light', dayname='Default (dark)', nightname='Light theme'),
]
P = dict(home='Home', chat='Chat', ideas='Ideas', plans='Plans', todo='To do', **{'home-kid':'Kid’s Home'}, signin='Sign in')

def fig(d, page, suffix, phone, label, lazy=True, cls=''):
    src = f"img/{d['k']}/{page}{suffix}{'-phone' if phone else ''}.webp"
    w, h = (585, 1266) if phone else (1280, 800)
    lz = ' loading="lazy"' if lazy else ''
    alt = f"{d['name']}, {P[page]}, {'phone' if phone else 'desktop'}, {label}"
    return (f'<figure class="shot {"ph" if phone else "dt"} {cls}"><div class="frame"><img src="{src}" alt="{html.escape(alt)}" width="{w}" height="{h}"'
            f'{lz}></div><figcaption><span>{P[page]} · {label}</span>'
            f'<button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure>')

glance = ''.join(f'<a class="g" href="#{d["k"]}"><span class="gn">{d["name"]}</span>' + fig(d,'home',d['day'],False,d['dayname'],lazy=False) + '</a>' for d in D)
secs = []
for d in D:
    sw = ''.join(f'<i class="c{n}"></i>' for n in range(4))
    s = f'''<section class="dir d-{d['k']}" id="{d['k']}" aria-labelledby="h-{d['k']}">
  <header class="dh"><p class="tag">{d['tag']}</p><h2 id="h-{d['k']}">{d['name']}</h2><div class="sw" aria-hidden="true">{sw}</div><p class="idea">{d['idea']}</p><p class="ev">{d['ev']}</p></header>
  <h3>Desktop · {d['dayname']}</h3>
  <div class="row two">{fig(d,'home',d['day'],False,d['dayname'])}{fig(d,'chat',d['day'],False,d['dayname'])}{fig(d,'plans',d['day'],False,d['dayname'])}{fig(d,'todo',d['day'],False,d['dayname'])}</div>
  <h3>Desktop · {d['nightname']}</h3>
  <div class="row two">{fig(d,'home',d['night'],False,d['nightname'])}{fig(d,'chat',d['night'],False,d['nightname'])}</div>
  <h3>Phone</h3>
  <div class="row phones">{fig(d,'home',d['day'],True,d['dayname'])}{fig(d,'chat',d['day'],True,d['dayname'])}{fig(d,'todo',d['day'],True,d['dayname'])}{fig(d,'home',d['night'],True,d['nightname'])}</div>
  <h3>For a kid, and signing in</h3>
  <div class="row two">{fig(d,'home-kid',d['day'],False,d['dayname'])}{fig(d,'signin',d['day'],False,d['dayname'])}</div>
</section>'''
    secs.append(s)

swcss = '\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
out = open('page.tpl.html').read().replace('<!--GLANCE-->', glance).replace('<!--SECTIONS-->', '\n'.join(secs)).replace('/*SW*/', swcss)
open('index.html','w').write(out)
