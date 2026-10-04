import html, json
D = [
 dict(k='merged', name='The merged layout', tag='House Log, with The Board’s panel and crispness', voice='House Log’s light, ruled page and date margin, with The Board’s navy panel down the left and its sign lettering for titles and figures. Ask Vera is shorter now, without the starter buttons.',
      facts=[('Type','Barlow Semi Condensed for titles and the greeting, Barlow Condensed for labels and big figures, Martian Mono for the date margin, Atkinson for every sentence.'),('Changed','The navy panel came in whole; the Log’s 01–10 page numbers went. Firmer 3 px section rules. Every “you are here” is an inverted plate. Without the starters, the whole Next up board now fits on the first desktop screen.'),('Colours','Still the working colours from earlier rounds, so this is the layout to judge, not the palette.')], sw=['#F3F4F0','#111A2B','#6DFF9C','#B884B0'], palette=False),
 dict(k='rail', name='Rail yellow', tag='Palette 1', voice='Like good station signage: a deep rail-blue panel, a crisp light page with blue-black ink, and one signal yellow, always a solid plate, marking what you act on next.',
      facts=[('People','Cobalt, violet, plum (Maya), tangerine, then petrol, sky, sand and chestnut. Each avatar letter is white or ink, whichever reads best.'),('Signals','Yellow only as a plate: today, the Leave by label, “you are here” in the panel. Setup and warnings move to copper so they can’t be mistaken for the yellow. Links and the main button are the panel’s blue.'),('Weaker','At night cobalt and violet stripes are the closest pair for red-green colour blindness. Sky, sand and tangerine avatars fade at the edges on white.')], sw=['#F5F6F8','#0B2C69','#FFC917','#935987'], palette=True),
 dict(k='metro', name='Metro lines', tag='Palette 2', voice='The family as a transit map: a white sheet, black ink, a deep navy key panel, and each person one flat line colour, the same on an avatar, a route stripe and a rule.',
      facts=[('People','Blue, teal, violet (Maya), amber (Theo), then sky, plum, bronze and petrol: flat, confident line colours.'),('Signals','Green stays today and Vera’s; red only late; set up is a dark amber. The cleanest and most graphic of the three.'),('Weaker','The closest colour-blind pair (teal and plum) is the tightest of the three. At night the panel is close to the page in lightness and is held apart by hue.')], sw=['#FFFFFF','#0F1B33','#3D5FF1','#5530B8'], palette=True),
 dict(k='enamel', name='Enamel', tag='Palette 3', voice='The colours of old enamel signs and good painted interiors: a warm grey plaster page, a deep petrol panel, earthy enamel colours for the people, and Vera’s green glass still the one lit thing.',
      facts=[('People','Slate blue, heather, plum (Maya), ochre (Theo), then teal, duck-egg, lichen and mustard, alternating light and dark round the wheel.'),('Signals','Late is a brick red; set up a deep honey; today and Vera green. The warmest of the three without going cream.'),('Weaker','Softer and less crisp than the other two. Theo’s stripe had to be a dark umber, not his ochre, to stay apart for colour-blind eyes.')], sw=['#ECE9E5','#0D2D40','#C1843C','#AB79A5'], palette=True),
]
P = {'home':'Home','plans':'Plans','todo':'To do','chat':'Chat','ideas':'Ideas','home-kid':'Maya’s Home','wishes-kid':'Maya’s wishes','palette':'Palette sheet'}
used=[]
def fig(d, page, suffix, phone, label, lazy=True):
    src = f"img/{d['k']}/{page}{suffix}{'-phone' if phone else ''}.webp"; used.append(src)
    w, h = (585, 1266) if phone else (1280, 800)
    alt = f"{d['name']}, {P[page]}, {'phone' if phone else 'desktop'}, {label}"
    lz = ' loading="lazy"' if lazy else ''
    return (f'<figure class="shot {"ph" if phone else "dt"}"><div class="frame"><img src="{src}" alt="{html.escape(alt)}" width="{w}" height="{h}"{lz}></div>'
            f'<figcaption><span>{P[page]} · {label}</span><button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure>')
glance = ''.join(f'<a class="g" href="#{d["k"]}"><span class="gn">{d["name"]}</span>' + fig(d,'home','',False,'Day',lazy=False) + '</a>' for d in D)
secs=[]
for d in D:
    sw=''.join(f'<i class="c{n}"></i>' for n in range(4))
    facts=''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in d['facts'])
    pal = (f"<h3>The palette sheet</h3><div class=\"row two\">{fig(d,'palette','',False,'Day')}{fig(d,'palette','-dark',False,'Night')}</div>" if d['palette'] else '')
    secs.append(f'''<section class="dir d-{d['k']}" id="{d['k']}" aria-labelledby="h-{d['k']}">
  <header class="dh"><p class="tag">{d['tag']}</p><h2 id="h-{d['k']}">{d['name']}</h2><div class="sw" aria-hidden="true">{sw}</div><p class="idea">{d['voice']}</p><dl class="facts">{facts}</dl></header>
  <h3>Desktop</h3>
  <div class="row two">{fig(d,'home','',False,'Day')}{fig(d,'plans','',False,'Day')}{fig(d,'todo','',False,'Day')}{fig(d,'chat','',False,'Day')}{fig(d,'home','-dark',False,'Night')}{fig(d,'plans','-dark',False,'Night')}</div>
  <h3>Phone</h3>
  <div class="row phones">{fig(d,'home','',True,'Day')}{fig(d,'plans','',True,'Day')}{fig(d,'home-kid','',True,'Day')}{fig(d,'home','-dark',True,'Night')}</div>
  <h3>Maya’s pages</h3>
  <div class="row two">{fig(d,'home-kid','',False,'Day')}{fig(d,'wishes-kid','',False,'Day')}</div>
  {pal}
</section>''')
swcss='\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
open('index.html','w').write(open('page.tpl.html').read().replace('<!--GLANCE-->',glance).replace('<!--SECTIONS-->','\n'.join(secs)).replace('/*SW*/',swcss))
json.dump({u:u for u in sorted(set(used))},open('files.json','w'))
print(len(set(used)))
