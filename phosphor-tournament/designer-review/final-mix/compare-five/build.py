import html, json
D = [
 dict(k='midnight', name='Midnight', tag='Dark first', A='-dark', An='Night (the default)', B='', Bn='Day',
      voice='FamilyDB as a screen in a dark kitchen at night: a blue-black page, a darker panel, soft-white ink, each person’s colour lit like a window, and Vera’s green glass the one green light among them.',
      facts=[('People','Moon blue (Sam), iris (Alex), lagoon (Maya), apricot (Theo), then heather, sky, ochre and sage. They glow gently at night, with a soft halo on their stripes.'),('Signals','Today and Vera in phosphor green; set up in sodium-lamp amber; late a soft red. By day the panel stays midnight.'),('Weaker','At night the panel is barely darker than the page, held apart by a hairline. Making night the default on every device needs a theme setting the app doesn’t have yet.')], sw=['#0B1020','#04060D','#6DFF9C','#ECB489']),
 dict(k='aubergine', name='Aubergine & Brass', tag='Rich and grown-up', A='', An='Day', B='-dark', Bn='Night',
      voice='A well-kept house: warm stone walls, aubergine-black ink beside a deep aubergine panel, brushed brass on whatever you act on next, the family in jewel tones, and Vera’s green glass the one lit thing.',
      facts=[('People','Sapphire (Sam), amethyst (Alex), peacock (Maya), topaz (Theo), then peridot, cerulean, tiger’s eye and tanzanite.'),('Signals','Brass marks the page you’re on, Tomorrow, today and Leave by; the main button is aubergine with brass letters by day. Set up is copper with ⚠.'),('Weaker','Today’s brass stamp is faint against the stone page (its letters carry it), and today’s wash on the calendar comes close to cream.')], sw=['#E9E6E4','#2B1530','#CFA650','#0BAEAF']),
 dict(k='homecomputer', name='Home Computer', tag='Early-80s family machine', A='', An='Day', B='-dark', Bn='Night',
      voice='The family machine of the early 80s beside FamilyDB’s green screen: a putty case for the page, a brown-black keyboard for the panel, the striped badge colours for the family’s pens, one orange key for “this one”, and the green screen kept for Vera.',
      facts=[('People','Cobalt (Sam), violet (Alex), mustard (Maya), turquoise (Theo), then walnut, sky, petrol and aubergine.'),('Signals','One orange key for today, Tomorrow, the main button and the page you’re on; the panel’s edge carries a stripe of the family’s colours, like the old logo badges. Ticks are ink, so green is only Vera’s.'),('Weaker','Maya’s mustard sits close to the orange key for one kind of colour blindness at night. The most playful of the five, which may not suit every screen.')], sw=['#E3E1DC','#231C17','#F07C1E','#E0AE2E']),
 dict(k='ink', name='Ink', tag='Almost no colour', A='', An='Day', B='-dark', Bn='Night',
      voice='A white page, black ink, a black panel and untinted greys, so the only colours on screen are the family’s eight inks, late red and Vera’s green glass. When you see colour, it’s a person, it’s late, or it’s Vera.',
      facts=[('People','Ultramarine (Sam), cyan (Alex), violet (Maya), tangerine (Theo), then chrome yellow, cornflower, grape and umber: the most saturated of any palette.'),('Signals','Links, the main button, done and set up are all ink. Today stays Vera’s green; late is a pure red.'),('Weaker','Stark. At night only a hairline separates the black panel from the page. Chrome yellow’s stripe has to be olive-gold to show on white.')], sw=['#FFFFFF','#000000','#8A41FB','#FF8C33']),
 dict(k='dusk', name='Dusk', tag='Evening sky', A='', An='Day', B='-dark', Bn='Night',
      voice='The evening sky when the family gets home: a deep indigo-violet panel, a dusk-grey page, apricot (the last light) on whatever you do next, the family in sunset colours, and Vera’s window the one thing lit green.',
      facts=[('People','Evening blue (Sam), sea (Alex), heather (Maya), sun gold (Theo), then sky, olive, dusk cloud and sandstone, each with the same indigo letter.'),('Signals','Apricot for today, Tomorrow, the main button and the page you’re on; late is a cool crimson kept well away from it; set up is honey with ⚠. The panel deepens from indigo to violet at its foot.'),('Weaker','Some day stripes are very deep. At night the panel is close to the page in lightness and stands apart by its violet.')], sw=['#F4F0EE','#251754','#FEA660','#C29CF5']),
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
glance = ''.join(f'<a class="g" href="#{d["k"]}"><span class="gn">{d["name"]}</span>' + fig(d,'palette',d['A'],False,'Palette sheet',lazy=False) + fig(d,'home',d['A'],False,d['An'],lazy=False) + '</a>' for d in D)
secs=[]
for d in D:
    A,An,B,Bn=d['A'],d['An'],d['B'],d['Bn']
    sw=''.join(f'<i class="c{n}"></i>' for n in range(4))
    facts=''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in d['facts'])
    secs.append(f'''<section class="dir d-{d['k']}" id="{d['k']}" aria-labelledby="h-{d['k']}">
  <header class="dh"><p class="tag">{d['tag']}</p><h2 id="h-{d['k']}">{d['name']}</h2><div class="sw" aria-hidden="true">{sw}</div><p class="idea">{d['voice']}</p><dl class="facts">{facts}</dl></header>
  <h3>The palette sheet</h3>
  <div class="row two">{fig(d,'palette',A,False,An)}{fig(d,'palette',B,False,Bn)}</div>
  <h3>Desktop</h3>
  <div class="row two">{fig(d,'home',A,False,An)}{fig(d,'plans',A,False,An)}{fig(d,'todo',A,False,An)}{fig(d,'chat',A,False,An)}{fig(d,'home',B,False,Bn)}{fig(d,'plans',B,False,Bn)}</div>
  <h3>Phone</h3>
  <div class="row phones">{fig(d,'home',A,True,An)}{fig(d,'plans',A,True,An)}{fig(d,'home-kid',A,True,An)}{fig(d,'home',B,True,Bn)}</div>
  <h3>Maya’s pages</h3>
  <div class="row two">{fig(d,'home-kid',A,False,An)}{fig(d,'wishes-kid','',False,'Day')}</div>
</section>''')
swcss='\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
open('index.html','w').write(open('page.tpl.html').read().replace('<!--GLANCE-->',glance).replace('<!--SECTIONS-->','\n'.join(secs)).replace('/*SW*/',swcss))
json.dump({u:u for u in sorted(set(used))},open('files.json','w'))
print(len(set(used)))
