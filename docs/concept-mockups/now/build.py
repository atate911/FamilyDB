"""The Now layout (docs/INTERFACE.md) as static screens. Run: python3 build.py, then shoot."""
import pathlib, re
HERE = pathlib.Path(__file__).parent
ICONS = HERE.parent.parent.parent / "src/familydb/web/static/icons.svg"
sprite = re.sub(r"^<svg ", '<svg style="display:none" ', ICONS.read_text(), count=1)
def i(n, c=""): return f'<svg class="i {c}"><use href="#i-{n}"/></svg>'
P = {"Sam": (1, "S"), "Alex": (2, "A"), "Maya": (3, "M"), "Theo": (4, "T")}
def av(n, s=""): k, c = P[n]; return f'<span class="av p{k} {s}">{c}</span>'
def avs(*ns): return '<span class="avs">' + "".join(av(n, "sm") for n in ns) + "</span>"
def page(name, body, cls="phone"):
    (HERE / f"{name}.html").write_text(f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="now.css"></head><body>{sprite}<div class="{cls}">{body}</div></body></html>')
def top(who="Sam"): return f'<header class="top"><span class="wm">FamilyDB<span class="cur"></span></span>{av(who)}</header>'
def box(ph="Tell Vera, or ask her…", scope=None, receipt=None):
    s = f'<div class="scope">about: {scope}<span class="x">{i("x","sm")}</span></div>' if scope else ""
    r = f'<div class="receipt">{receipt}</div>' if receipt else ""
    return f'<div class="bar">{s}<div class="box"><span class="ph">{ph}</span><span class="mic">{i("mic")}</span><span class="send">{i("send")}</span></div>{r}</div>'
def ctx(t): return f'<p class="ctx">{t}</p>'
ROW = [("Now", "now"), ("Eat", "eat"), ("Do", "do"), ("Week", "week"), ("Kids", "kids"), ("Soon", "soon"), ("Lists", "lists"), ("Did", "did")]
def row(on="now", items=ROW): return '<nav class="row">' + "".join(f'<a class="{"on" if k == on else ""}">{l}</a>' for l, k in items) + "</nav>"
def sec(label, inner, small=""): return f'<section class="sec"><div class="label"><span>{label}</span>{f"<small>{small}</small>" if small else ""}</div>{inner}</section>'
def ask(text, org, *btns):
    return f'<div class="ask"><span class="vs"></span><div class="body"><p>{text}</p><p class="org">{org}</p><div class="acts">{"".join(btns)}</div></div></div>'
def pick(kind, when, name, why): return f'<div class="pick"><span class="label">{kind} · {when}</span><span class="t">{name}</span><span class="why">{why}</span></div>'
def setrow(tm, t, m): return f'<div class="set"><span class="num">{tm}</span><div><div class="t">{t}</div><div class="m">{m}</div></div></div>'
B = lambda t, c="": f'<button class="btn {c}">{t}</button>'
L = lambda t: f'<a class="lnk">{t}</a>'

# 1. Now, Friday 5 pm
now1 = (top() + box() + ctx("Friday 5 pm · dry through Sunday")
  + "<main>"
  + ask("Maya asked for the trampoline park. Saturday morning is free.", "Maya, Tuesday", B("Plan it"), L("Later"))
  + sec("What about…", '<div class="picks">'
      + pick("Eat", "tonight", "Kenji’s Ramen", "Open till 9, 12 min. You haven’t been.")
      + pick("Go out", "Saturday", "Sky High Trampolines", "Maya’s pitch, and it’s dry.")
      + pick("Day trip", "Sunday", "Kites on Powell Butte", "Wind’s right. You loved the patch.")
      + pick("New", "weekend", "Pumpkin carving, Tryon Creek", "Free. Vera found it.")
      + "</div>", "chosen 4 pm")
  + '<div class="todays"><p class="today"><b>Today</b><span>Swim lesson 4:30, then free.</span></p><p class="today"><b>Sat</b><span>Night Market 5 pm.</span></p></div>'
  + "</main>" + row())
page("1-now-friday", now1)

# 2. Now, Tuesday 8 am
now2 = (top() + box() + ctx("Tuesday 8 am · rain till noon")
  + '<main><p class="quiet">Nothing needs you.</p>'
  + '<p class="today"><b>Today</b><span>Dentist at 9, Alex. Then free.</span></p>'
  + "</main>" + row())
page("2-now-tuesday", now2)

# 3. Now, an hour before a plan, with a receipt
now3 = (top() + box(receipt=f'{i("check","sm")}<span>Added <b>socks</b> to the <span class="kind">packing list</span>.</span><a>Undo</a>') + ctx("Saturday 9:05 am · dry, 54°")
  + "<main>"
  + '<div class="set big"><span class="label">In an hour</span><div class="t">Sky High Trampolines, 10 am</div>'
  + f'<div class="m">Leave by 9:35 · 20 min · waivers done · bring socks</div><div class="acts" style="margin-top:4px">{avs("Sam","Alex","Maya","Theo")}{B("Directions","quiet")}</div></div>'
  + '<p class="today"><b>Then</b><span>Free till the Night Market at 5. Lunch somewhere on the way: Theo picks.</span></p>'
  + "</main>" + row())
page("3-now-before-plan", now3)

# 4. Eat out
def r(t, m, tr=""): return f'<div class="r"><div class="t">{t}</div><div class="m">{m}</div>{f"<div class=tr>{tr}</div>" if tr else ""}</div>'
eat = (top() + box("Narrow it, or ask…", scope="Eat out") 
  + '<main style="gap:16px"><div class="pagehead"><h1 class="display">Where should we eat?</h1></div>'
  + '<div class="chips"><span class="chip on">Tonight</span><span class="chip">Open now</span><span class="chip">Close</span><span class="chip">Just us</span><span class="chip">New</span><span class="chip">Thai</span><span class="chip">Pizza</span></div>'
  + '<div class="rows">'
  + '<div class="r top"><span class="label">Tonight</span><div class="t">Kenji’s Ramen</div><div class="m">Open till 9 · 12 min · $$ · you haven’t been · Jess says spicy miso</div></div>'
  + r("Matt’s BBQ", "Food cart · till 8 · 15 min · $ · Alex’s idea")
  + r("Ava Gene’s", "Italian · till 10 · 18 min · $$$ · book ahead · just us")
  + r("Pok Pok", "Thai · till 9 · 14 min · $$ · been twice, loved it")
  + r("Pine State Biscuits", "Breakfast · closed now · 10 min · $")
  + r("Lardo", "Sandwiches · till 9 · 9 min · $")
  + "</div></main>" + row("eat"))
page("4-eat-out", eat)

# 5. A place
place = (top() + box("Plan it, ask, or change it…", scope="Kenji’s Ramen")
  + '<main style="gap:18px"><a class="back">‹ Eat out</a>'
  + '<div class="pagehead"><span class="label">Eat out · an idea</span><h1 class="display">Kenji’s Ramen</h1></div>'
  + '<div class="facts"><div><div class="k">Today</div><div class="v ok">Open till 9 pm</div></div><div><div class="k">From home</div><div class="v">12 min</div></div>'
  + '<div><div class="k">Cost</div><div class="v">$$ · about $16 a bowl</div></div><div><div class="k">Booking</div><div class="v">Walk-ins only</div></div></div>'
  + f'<div class="said">“Kenji’s Ramen on Division is really good. Jess says get the spicy miso.”<div class="by">{av("Sam","sm")}Sam, Tuesday</div></div>'
  + '<div class="found"><div>Lines past 6 on Fridays, but they move. A kids’ bowl and a mild broth. Vegetarian miso.</div><div class="by">Vera checked this morning</div></div>'
  + f'<div class="acts">{B("Plan it","pri")}{L("Drop it")}</div>'
  + '<p><a class="byhand">Edit by hand</a></p>'
  + "</main>" + row("eat"))
page("5-place", place)

# 6. Her reply over Eat out
reply = (eat.replace('<div class="phone">', '') if False else eat)
sheet = ('<div class="dim"></div><div class="sheet"><div class="grip"></div>'
  + '<div class="you">A new Thai place we haven’t tried, open now, within 15 miles</div>'
  + '<div class="her"><span class="vs"></span><div class="body"><p>Two you haven’t been to, both open now. Pok Pok is out since you’ve been twice.</p>'
  + '<div class="rows">' + r("Eem", "Thai · till 10 · 11 min · $$ · Alex saved it in May") + r("Hat Yai", "Thai · till 9 · 13 min · $ · Vera found it") + "</div>"
  + '<p class="org" style="color:var(--ink-2)">Both are on Eat out under Thai.</p></div></div>'
  + '<div class="foot"><a>Earlier</a><a>Show on Eat out ›</a></div></div>')
page("6-reply-over-eat", eat + sheet)

# 7. A kid's Now
kid = (top("Maya") + box("I want… or We should…") + ctx("Friday · Mom and Dad can read this")
  + '<main>'
  + ask("Sunday afternoon: which do you want most?", "Vera", B("Kites on the hill"), B("Pumpkin carving"))
  + sec("Your pitch", '<div class="set"><div><div class="t">Sky High Trampolines</div><div class="m">Mom and Dad are picking a time.</div>'
      + f'<div class="journey" style="margin-top:6px"><span class="on">{i("check","sm")} Pitched</span><i></i><span class="on">{i("check","sm")} Shaped</span><i></i><span>Their yes</span></div></div></div>')
  + sec("My list", '<div class="rows">'
      + '<div class="wish"><span class="rank">1</span>Roller skates</div>'
      + '<div class="wish"><span class="rank">2</span>Sketchbook, thick paper<span class="m">Parents are thinking</span></div>'
      + '<div class="wish"><span class="rank">3</span>Glow-in-the-dark stars<span class="tag ok" style="margin-left:auto">Yes!</span></div></div>')
  + '<p class="quiet">12 messages left today.</p>'
  + "</main>" + row("now", [("Now", "now"), ("My week", "week"), ("My list", "list"), ("Do", "do")]))
page("7-kid-now", kid, cls="phone kid")

# 8. Desktop
rail = ('<aside class="rail"><span class="wm">FamilyDB<span class="cur"></span></span>' + "".join(
  f'<a class="{"on" if k=="now" else ""}"><b>{l}</b><small>{h}</small></a>' for l, k, h in [
    ("Now", "now", "Nothing needs you"), ("Where should we eat?", "eat", "Kenji’s tonight"), ("What could we do?", "do", "3 fit Saturday"),
    ("This week", "week", "Free Sat afternoon"), ("The kids", "kids", "1 waiting"), ("Happening soon", "soon", "4 this weekend"),
    ("Lists", "lists", "Shopping · 6"), ("What we did", "did", "Pumpkin patch")])
  + f'<div class="me">{av("Sam")}<span>Sam<br>Parent</span></div></aside>')
center = ('<section class="center">' + box() + ctx("Friday 5 pm · dry through Sunday")
  + ask("Maya asked for the trampoline park. Saturday morning is free.", "Maya, Tuesday", B("Plan it"), L("Later"))
  + sec("What about…", '<div class="picks">'
      + pick("Eat", "tonight", "Kenji’s Ramen", "Open till 9, 12 min. You haven’t been.")
      + pick("Go out", "Saturday", "Sky High Trampolines", "Maya’s pitch, and it’s dry.")
      + pick("Day trip", "Sunday", "Kites on Powell Butte", "Wind’s right. You loved the patch.")
      + pick("New", "weekend", "Pumpkin carving, Tryon Creek", "Free. Vera found it.")
      + pick("Just you two", "Friday", "Ava Gene’s", "Theo’s at Grandma’s. Book ahead.")
      + pick("Stay in", "Sunday eve", "Pottery kit", "Rain by 6. It’s on the list.")
      + "</div>", "chosen 4 pm")
  + '<div class="todays"><p class="today"><b>Today</b><span>Swim lesson 4:30, then free.</span></p><p class="today"><b>Sat</b><span>Night Market 5 pm.</span></p></div></section>')
vcol = ('<aside class="vcol"><div class="vh"><span class="vs lg"></span><div><b>Vera</b><span class="quiet">your thread · also in Telegram</span></div></div><div class="thread">'
  + '<div class="you">Kenji’s Ramen on Division is really good. Jess says get the spicy miso</div>'
  + '<div class="her"><span class="vs sm"></span><div class="body"><p>Saved it under Eat out, from Jess. I’ll find the hours.</p></div></div>'
  + '<div class="her"><span class="vs sm"></span><div class="body"><p>Filled in: open till 9 tonight, 12 minutes, walk-ins only.</p></div></div>'
  + '<div class="you">What’s Saturday look like?</div>'
  + '<div class="her"><span class="vs sm"></span><div class="body"><p>Free from noon till the Night Market at 5. Morning’s open too, and Maya’s asked for Sky High. Dry all day.</p><p class="quiet"><a>See the week ›</a></p></div></div>'
  + '</div>' + box() + '</aside>')
page("8-desktop", rail + center + vcol, cls="desk")

# 9. Kitchen tablet board
def card(cls, x, y, w, h, inner): return f'<div class="card {cls}" style="left:{x}px;top:{y}px;width:{w}px;min-height:{h}px">{inner}</div>'
board = ('<div class="tbar"><div class="box"><span class="ph">Ask Vera anything, or tell her something</span><span class="mic">' + i("mic") + '</span><span class="send">' + i("send") + '</span></div>'
  + f'<div class="faces">{av("Sam")}{av("Alex")}<span class="av p3 chosen">M</span>{av("Theo")}</div></div><div class="board">'
  + card("ink big", 380, 20, 400, 180, '<span class="label">Saturday · tomorrow</span><div class="t">Night Market, 5 pm</div><div class="m">Everyone · 20 min · free from noon before it</div>')
  + card("pen mid", 800, 40, 300, 120, '<span class="label">Sat morning · Maya’s pitch</span><div class="t">Sky High Trampolines</div><div class="m">Waiting on a parent · dry</div>')
  + card("pen mid", 60, 60, 280, 120, '<span class="label">Tonight · eat</span><div class="t">Kenji’s Ramen</div><div class="m">Open till 9 · 12 min · not been</div>')
  + card("pen", 420, 230, 300, 100, '<span class="label">Sunday · day trip</span><div class="t">Kites on Powell Butte</div><div class="m">Wind’s right</div>')
  + card("plain", 60, 230, 300, 100, '<span class="label">Wednesday</span><div class="t">Library books back</div><div class="m">Alex has it</div>')
  + card("plain", 800, 200, 300, 150, '<span class="label">Shopping · 6</span><div class="m">Milk · eggs · socks · rice · lemons · tape</div>')
  + card("pen", 760, 390, 280, 90, '<span class="label">New · ends Sunday</span><div class="t">Pumpkin carving, Tryon Creek</div>')
  + card("fade", 80, 400, 220, 70, '<div class="t">Oregon Coast Aquarium</div><div class="m">someday</div>')
  + card("fade", 400, 420, 200, 70, '<div class="t">Pottery class</div><div class="m">saved in March</div>')
  + card("fade", 1020, 540, 120, 60, '<div class="t">Hopscotch</div>')
  + '</div><div class="trow"><span>Eat</span><span>Do</span><span>Week</span><span>Kids</span><span>Soon</span><span>Lists</span><span>Did</span></div>')
page("9-tablet-board", board, cls="tab")
print("built")
