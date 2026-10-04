import html, json
D = [
 dict(k='board', name='The Board', tag='Departure board', voice='The family’s day set like a station departure board: what leaves next, when to go and whose it is, readable from across the kitchen.',
      type='Barlow Condensed for times, dates and figures, from California’s highway and rail signs; Barlow Semi Condensed for headings; Atkinson for every sentence.',
      easier='“Leave by 12:30 pm” is the biggest thing on Home. Each plan has a stripe in the colours of who’s going. Due dates sit in one right-hand column, and ideas show drive time as a big figure.',
      weaker='A lot of navy, so Ask Vera stands out less, and on Home it moves below the board. Chat changed least.', sw=['#F3F1EC','#111A2B','#0B8457','#E2457A']),
 dict(k='week', name='Week at a Glance', tag='The week on one page', voice='The family’s week, printed big: seven days across, today in solid ink, everyone in their own pen.',
      type='Archivo at three widths: squeezed narrow for big day numbers and money, heavy for headings, wide for small capitals. Atkinson for every sentence.',
      easier='Home leads with the next seven days, so free days show at a glance. A top masthead replaces the sidebar to give the week full width. On the phone the week turns into rows. To-dos lead with their date.',
      weaker='An empty day is a loud black column. Home rolls seven days from today while Plans keeps Monday to Sunday. Long titles wrap in narrow day columns.', sw=['#EFEEE9','#17161C','#0B8457','#E2457A']),
 dict(k='log', name='House Log', tag='The household logbook', voice='The family’s logbook: Vera keeps the ruling, with dates, times and numbers in a typed margin, and everybody writes the lines in plain words and their own colour.',
      type='Archivo condensed for titles and wide capitals for running heads; Martian Mono for the margin of dates and times; Atkinson for every sentence.',
      easier='Every list has a date margin, so “when” runs down one edge and “what” down the other. Sections are ruled instead of boxed, so more fits on a screen. Ideas become a table where drive times compare down one column.',
      weaker='Thin rules can fade on dim screens. On a phone the margin squeezes titles. The Ideas table needs a wide screen.', sw=['#F3F4F0','#111315','#0B8457','#E2457A']),
 dict(k='thread', name='Thread', tag='Talk first', voice='The household’s running conversation: one line down the page with the clock in its margin, Vera typing in a steady mono, and every plan, to-do and wish dropping in as its own object.',
      type='Familjen Grotesk for the names of things, with its italic for kids’ wishes; Atkinson Hyperlegible Mono for Vera and the clock; Atkinson for every sentence.',
      easier='Home is one timeline from “Now”. Chat is the middle tab on the phone, and there’s a “Write to Vera” box on every desktop page. Plans look like tickets, to-dos like ticked lines, and wishes like quotes.',
      weaker='The closest of the four to what you’ve seen. Your own messages no longer sit on the right. Some pages offer two places to write.', sw=['#F5F4F8','#1A1830','#0B8457','#E2457A']),
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
</section>''')
swcss='\n'.join(f'.d-{d["k"]} .c{n}{{background:{c}}}' for d in D for n,c in enumerate(d['sw']))
open('index.html','w').write(open('page.tpl.html').read().replace('<!--GLANCE-->',glance).replace('<!--SECTIONS-->','\n'.join(secs)).replace('/*SW*/',swcss))
json.dump({u:u for u in sorted(set(used))},open('files.json','w'))
print(len(set(used)))
