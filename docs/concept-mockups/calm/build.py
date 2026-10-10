import pathlib, re
HERE = pathlib.Path(__file__).parent
ICONS = HERE.parent.parent.parent / "src/familydb/web/static/icons.svg"
sprite = re.sub(r"^<svg ", '<svg style="display:none" ', ICONS.read_text(), count=1)
def i(n): return f'<svg class="i"><use href="#i-{n}"/></svg>'
def page(name, body):
    (HERE / f"{name}.html").write_text(f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="calm.css"></head><body>{sprite}<div class="phone">{body}</div></body></html>')
def top(cls="p1", ch="S"): return f'<header class="top"><span class="word">FamilyDB<span class="cur"></span></span><span class="av {cls}">{ch}</span></header>'
def bar(ph="Tell Vera…"): return f'<div class="bar"><div class="box"><span>{ph}</span>{i("mic")}<span class="go">{i("send")}</span></div></div>'
def tabs(on="home"):
    return '<nav class="tabs">' + "".join(f'<a class="{"on" if k==on else ""}">{i(ic)}{lab}</a>' for k, ic, lab in
        [("home","home","Home"),("ideas","bulb","Ideas"),("cal","cal","Calendar"),("lists","list","Lists")]) + "</nav>"
def vera(text, action=""): return f'<section class="vera"><div class="who"><span class="vs"></span>Vera</div><p>{text}</p>{action}</section>'
def row(k, v, small="", could=False): return f'<div class="row{" could" if could else ""}"><span class="k">{k}</span><span class="v">{v}{f"<small>{small}</small>" if small else ""}</span></div>'

# Home, a normal Friday
home = (top() + '<main><h1 class="day">Friday</h1>'
  + vera("Theo’s swim lesson is at 4:30. Saturday’s dry, and Maya would like to try the trampoline park in the morning.",
         '<div class="act"><button class="btn">Plan Saturday</button><a class="link">Not now</a></div>')
  + '<hr>'
  + '<section class="rows"><h2>Coming up</h2>'
  + row("4:30", "Theo’s swim lesson")
  + row("Sat", "Trampoline park, morning", "could", True)
  + row("Sat", "Night Market", "5 pm, everyone")
  + row("Sun", "Open") + "</section>"
  + '<p class="end">That’s all.</p></main>' + bar() + tabs())
page("1-home", home)

# Home, the first day
first = (top() + '<main><h1 class="day">Friday</h1><div class="empty">'
  + vera("Hi, I’m Vera. Tell me one place your family would happily go back to, and I’ll start from there.")
  + '</div></main>' + bar("A place you like…") + tabs())
page("2-first-day", first)

# Home, a quiet Tuesday
quiet = (top() + '<main><h1 class="day">Tuesday</h1>'
  + vera("Nothing today. Dentist tomorrow at 9.")
  + '<hr><section class="rows"><h2>Coming up</h2>'
  + row("Wed", "Dentist", "9 am, Alex") + row("Sat", "Night Market", "5 pm, everyone") + "</section>"
  + '<p class="end">That’s all.</p></main>' + bar() + tabs())
page("3-quiet-day", quiet)

# A plan taking shape
plan = (top() + '<main style="gap:30px"><a class="back">‹ Home</a>'
  + '<div><h1 class="title">Saturday at the trampoline park</h1><p class="sub">Maya’s idea</p></div>'
  + '<p class="glimpse">You get there when it opens and have the foam pit to yourselves for an hour. Maya works up to the big jump, and Theo finds the dodgeball court and won’t leave.</p>'
  + '<div class="q"><h3>What time?</h3><div class="choices"><span class="choice on">10 am</span><span class="choice">Afternoon</span></div></div>'
  + '<div class="q"><h3>Who’s coming?</h3><div class="people">'
  + '<div class="one"><span class="av md p3">M</span>Maya</div><div class="one"><span class="av md p1">S</span>Sam</div>'
  + '<div class="one"><span class="av md ask">+</span>Alex</div><div class="one"><span class="av md ask">+</span>Theo</div></div></div>'
  + '<p class="facts">Open 10 to 8 · 20 minutes away · walk-ins are fine</p>'
  + '<div class="setwrap"><button class="btn big">Set the plan</button><div class="alt"><a class="link">Not this one</a><a class="link">Change something</a></div></div>'
  + '</main>' + bar("Change something…") + tabs())
page("4-plan", plan)
print("built")
