import html
D = [
 dict(k='green', name='Kitchen Table', tag='As it is now', idea='Cream paper, beige lines, soft serif headings (Fraunces), forest green with a sun-yellow Send.', ev='The interface you said is nearly perfect, with the look that reads like a recipe or gardening site.', sw=['#F6F1E7','#1E5C4F','#F2C14E','#0E1312'], day='', night='-dark', dayname='Day', nightname='Night'),
 dict(k='wall', name='Kitchen Wall', tag='Take 1 · the family calendar on the wall', idea='A bright, ruled grid where dates and times are the main material: today is green, and every other colour is a person. One-person plans are solid blocks in that person’s colour.', ev='Headings, dates, times and money in Manrope, with bold wide figures you can read across the room. Date tiles are calendar pages with an ink weekday band.', sw=['#F3F5F8','#121A26','#0A7A55','#6DFF9C'], day='', night='-dark', dayname='Day', nightname='Night'),
 dict(k='app', name='Today Line', tag='Take 2 · a calendar app', idea='Kitchen Table’s pages set like the family’s calendar app: a cool, gridded surface, one green that means “now”, and events marked the calendar way with a colour bar and a light tint.', ev='Headings, dates, times and money in Inter, the open cousin of the fonts phone and desktop calendars use. Words are Atkinson, time is Inter.', sw=['#F3F4F6','#12161C','#04704A','#6DFF9C'], day='', night='-dark', dayname='Day', nightname='Night'),
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

glance = ''.join(f'<a class="g" href="#{d["k"]}"><span class="gn">{d["name"]}</span>' + fig(d,'plans',d['day'],False,d['dayname'],lazy=False) + '</a>' for d in D)
secs = []
for d in D:
    sw = ''.join(f'<i class="c{n}"></i>' for n in range(4))
    s = f'''<section class="dir d-{d['k']}" id="{d['k']}" aria-labelledby="h-{d['k']}">
  <header class="dh"><p class="tag">{d['tag']}</p><h2 id="h-{d['k']}">{d['name']}</h2><div class="sw" aria-hidden="true">{sw}</div><p class="idea">{d['idea']}</p><p class="ev">{d['ev']}</p></header>
  <h3>Desktop · {d['dayname']}</h3>
  <div class="row two">{fig(d,'home',d['day'],False,d['dayname'])}{fig(d,'plans',d['day'],False,d['dayname'])}{fig(d,'todo',d['day'],False,d['dayname'])}{fig(d,'chat',d['day'],False,d['dayname'])}</div>
  <h3>Desktop · {d['nightname']}</h3>
  <div class="row two">{fig(d,'home',d['night'],False,d['nightname'])}{fig(d,'plans',d['night'],False,d['nightname'])}</div>
  <h3>Phone</h3>
  <div class="row phones">{fig(d,'home',d['day'],True,d['dayname'])}{fig(d,'chat',d['day'],True,d['dayname'])}{fig(d,'plans',d['day'],True,d['dayname'])}{fig(d,'home',d['night'],True,d['nightname'])}</div>
  <h3>For a kid, and Ideas</h3>
  <div class="row two">{fig(d,'home-kid',d['day'],False,d['dayname'])}{fig(d,'ideas',d['day'],False,d['dayname'])}</div>
</section>'''
    secs.append(s)

swcss = '\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
out = open('page.tpl.html').read().replace('<!--GLANCE-->', glance).replace('<!--SECTIONS-->', '\n'.join(secs)).replace('/*SW*/', swcss)
open('index.html','w').write(out)
