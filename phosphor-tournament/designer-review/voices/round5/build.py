import html, json
D = [
 dict(k='board', before='board1', name='The Board', tag='Departure board, with House Log’s ideas', voice='The family’s day set like a station departure board: what leaves next, when to go and whose it is, readable from across the kitchen.',
      type='Barlow Condensed for times, dates and figures; Barlow Semi Condensed for headings; Vera’s line in a typed mono; Atkinson for every sentence.',
      easier='One-line greeting, then Ask Vera full width on her own dark glass, then the board with “Leave by 12:30 pm”, then the late to-dos, all on the first desktop screen. Every list has its date down the left edge. Chat is a transcript. Ruled sections where boxes did nothing.',
      weaker='Navy panel heads beside Vera’s charcoal box: told apart by shape and her green glow. Wider weekend columns cut weekday titles shorter. Maya’s pink is unchanged until the colour round.', sw=['#F3F1EC','#111A2B','#6DFF9C','#E2457A']),
 dict(k='log', before='log1', name='House Log', tag='Logbook, with The Board’s ideas', voice='The family’s logbook: Vera keeps the ruling, with dates and times in a typed margin, and everybody writes the lines in plain words and their own colour.',
      type='Archivo condensed for titles, wide capitals for running heads; Martian Mono for the margin of dates and times; Atkinson for every sentence.',
      easier='One-line greeting, then Ask Vera as the only lit, rounded block on the page, then a departure-board Next up with “12:30 pm” at 72 px and route stripes. The due date and how late sit together in the margin. Darker rules for dim screens; on the phone the date sits above the title so titles get the full width.',
      weaker='Long directions wrap on the phone. The phone calendar still shows dots, not stripes. Maya’s plum is a stand-in until the colour round.', sw=['#F3F4F0','#111315','#6DFF9C','#B884B0']),
]
P = {'home':'Home','plans':'Plans','todo':'To do','chat':'Chat','ideas':'Ideas','home-kid':'Maya’s Home','wishes-kid':'Maya’s wishes','wishes':'Wishes'}
used=[]
def fig(d, page, suffix, phone, label, lazy=True):
    src = f"img/{d['k']}/{page}{suffix}{'-phone' if phone else ''}.webp"; used.append(src)
    w, h = (585, 1266) if phone else (1280, 800)
    alt = f"{d['name']}, {P[page]}, {'phone' if phone else 'desktop'}, {label}"
    lz = ' loading="lazy"' if lazy else ''
    cls = 'ph' if phone else 'dt'
    return (f'<figure class="shot {cls}"><div class="frame"><img src="{src}" alt="{html.escape(alt)}" width="{w}" height="{h}"{lz}></div>'
            f'<figcaption><span>{P[page]} · {label}</span><button type="button" class="more" aria-expanded="false">Whole page</button></figcaption></figure>')
glance = ''.join(f'<a class="g" href="#{d["k"]}"><span class="gn">{d["name"]}</span>' + fig(d,'home','',False,'Day',lazy=False) + '</a>' for d in D)
secs=[]
for d in D:
    sw = ''.join(f'<i class="c{n}"></i>' for n in range(4))
    secs.append(f'''<section class="dir d-{d['k']}" id="{d['k']}" aria-labelledby="h-{d['k']}">
  <header class="dh"><p class="tag">{d['tag']}</p><h2 id="h-{d['k']}">{d['name']}</h2><div class="sw" aria-hidden="true">{sw}</div><p class="idea">{d['voice']}</p>
  <dl class="facts"><dt>Type</dt><dd>{d['type']}</dd><dt>What it makes easier</dt><dd>{d['easier']}</dd><dt>Where it’s weaker</dt><dd>{d['weaker']}</dd></dl></header>
  <h3>Desktop</h3>
  <div class="row two">{fig(d,'home','',False,'Day')}{fig(d,'plans','',False,'Day')}{fig(d,'todo','',False,'Day')}{fig(d,'chat','',False,'Day')}{fig(d,'ideas','',False,'Day')}{fig(d,'home','-dark',False,'Night')}</div>
  <h3>Phone</h3>
  <div class="row phones">{fig(d,'home','',True,'Day')}{fig(d,'plans','',True,'Day')}{fig(d,'todo','',True,'Day')}{fig(d,'home','-dark',True,'Night')}</div>
  <h3>A kid’s pages</h3>
  <div class="row two">{fig(d,'home-kid','',False,'Day')}{fig(d,'wishes-kid','',False,'Day')}</div>
  <div class="row phones">{fig(d,'home-kid','',True,'Day')}{fig(d,'wishes-kid','',True,'Day')}</div>
  <h3>Before this round</h3>
  <div class="row two">{fig(dict(d,k=d['before']),'home','',False,'Round 4')}</div>
  <div class="row phones">{fig(dict(d,k=d['before']),'home','',True,'Round 4')}</div>
</section>''')
swcss='\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
open('index.html','w').write(open('page.tpl.html').read().replace('<!--GLANCE-->',glance).replace('<!--SECTIONS-->','\n'.join(secs)).replace('/*SW*/',swcss))
json.dump({u:u for u in sorted(set(used))},open('files.json','w'))
print(len(set(used)))
