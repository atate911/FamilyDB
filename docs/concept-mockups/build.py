"""Builds the concept mockups (docs/CONCEPT.md) as static HTML. Run: python3 build.py"""
import pathlib, re

HERE = pathlib.Path(__file__).parent
ICONS = HERE.parent.parent / "src/familydb/web/static/icons.svg"
sprite = re.sub(r"^<svg ", '<svg style="display:none" ', ICONS.read_text(), count=1)

def i(n, c=""): return f'<svg class="i {c}"><use href="#i-{n}"/></svg>'
PEOPLE = {"Sam": (1, "S"), "Alex": (2, "A"), "Maya": (3, "M"), "Theo": (4, "T")}
def av(name, size=""): s, ch = PEOPLE[name]; return f'<span class="av p{s} {size}">{ch}</span>'
def avs(*names, size="sm"): return '<span class="avs">' + "".join(av(n, size) for n in names) + "</span>"
VS = '<span class="vs"></span>'
def tile(n, c=""): return f'<span class="tile {c}">{i(n)}</span>'
def page(name, body, cls="phone", wrap=""):
    (HERE / f"{name}.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>{name}</title><link rel="stylesheet" href="mock.css"></head>'
        f'<body>{sprite}<div class="{cls} {wrap}">{body}</div></body></html>')
def sec(title, inner, right=""):
    return f'<section class="sec"><h2 class="cap"><span>{title}</span>{right}</h2>{inner}</section>'

def top(who="Sam"):
    return f'<header class="top"><span class="word">FamilyDB<span class="cur"></span></span>{av(who)}</header>'
def tabs(on):
    items = [("home", "Home"), ("bulb", "Ideas"), ("cal", "Calendar"), ("list", "Lists")]
    return '<nav class="tabs">' + "".join(
        f'<a class="{"on" if k == on else ""}">{i(ic)}{lab}</a>' for k, (ic, lab) in zip(("home", "ideas", "cal", "lists"), items)) + "</nav>"
def bar(ph="Tell Vera, or find…", ctx=None, quick=(), note=""):
    c = f'<div class="ctx">about: {ctx}{i("x","sm")}</div>' if ctx else ""
    q = '<div class="quick">' + "".join(f'<span class="chip">{x}</span>' for x in quick) + "</div>" if quick else ""
    n = f'<div class="foot">{note}</div>' if note else ""
    return (f'<div class="barwrap">{c}{q}<div class="box"><span class="ph">{ph}</span><span class="mic">{i("mic")}</span>'
            f'<span class="go">{i("send")}</span></div>{n}</div>')
def phone(body, on, barhtml, who="Sam", wrap=""):
    return top(who) + f"<main>{body}</main>" + barhtml + tabs(on)

# ---------- shared pieces ----------
def setrow(tm, title, meta, trail=""):
    return f'<div class="set ink"><span class="tm">{tm}</span><div class="b"><div class="t">{title}</div><div class="m">{meta}</div></div>{trail}</div>'
def faces():
    return (f'<button class="btn sm">{i("smile","sm")}Loved it</button><button class="btn sm">{i("meh","sm")}OK</button>'
            f'<button class="btn sm">{i("frown","sm")}Not great</button>')
def idea_card(shape_btn="Yes"):
    return (
        '<div class="idea pencil"><div class="tags"><span class="tag pen">Could do</span><span class="tag">Sunday afternoon</span></div>'
        '<h3>Kites on Powell Butte</h3>'
        '<p class="glimpse">Sunday’s open after lunch and the wind is right. You carry the kites up the hill, Theo’s string tangles twice, '
        'and everyone is home by four with cold hands and hot chocolate.</p>'
        f'<div class="facts"><span>{i("car","sm")}25 min</span><span>{i("dollar","sm")}Free</span><span>{i("sun","sm")}Dry till 5</span></div>'
        '<div class="why">Vera found this · you loved the pumpkin patch · checked this morning</div>'
        f'<div class="acts"><button class="btn sm pri">{shape_btn}</button><button class="btn sm">Not this one</button>'
        '<button class="btn sm txt">Change something</button></div></div>')

# ---------- 1. Home, phone ----------
def home_body(desk=False):
    needs = (
        f'<div class="need pencil">{av("Maya","md")}<div class="b"><div class="t">Maya pitched Sky High Trampolines</div>'
        '<div class="m">Saturday morning, if it stays dry. It needs a time and who’s in.</div>'
        '<div class="acts"><button class="btn sm pri">Shape it</button><button class="btn sm">Not yet</button></div></div></div>'
        f'<div class="need plain" style="flex-wrap:wrap">{tile("leaf")}<div class="b"><div class="t">How was the pumpkin patch?</div>'
        f'<div class="m">Last Saturday, everyone. Vera uses it next time.</div></div><div class="acts" style="width:100%;margin-top:0">{faces()}</div></div>')
    return (
        '<div><div class="cap">Friday 16 October</div>'
        f'<div class="herline">{VS}<p>Dry Saturday ahead. Maya’s trampoline pitch is only waiting on a time.</p></div></div>'
        + sec("Today", '<div class="stack">'
              + setrow("4:30 pm", "Theo’s swim lesson", "Northeast pool · 20 min", avs("Theo"))
              + setrow(i("bell"), "Library books due Wednesday", "Alex is handling it", avs("Alex"))
              + "</div>")
        + sec("Needs you", f'<div class="stack">{needs}</div>', '<span class="m">2</span>')
        + sec("One idea", idea_card(), "")
        + f'<div class="caught">{i("check","sm")}<span>Filed since yesterday: <b>Kenji’s Ramen</b> under Eat out, and <b>Beck, Nov 18</b> on the calendar. <a>Look</a></span></div>'
        + '<p class="end">That’s all for today</p>')

page("1-home", phone(home_body(), "home", bar()), )

# ---------- 2. A plan taking shape ----------
plan = (
    f'<a class="back">{i("chevl","sm")}Home</a>'
    '<div class="phead"><div class="tags"><span class="tag pen">A plan taking shape</span></div>'
    '<h1>Saturday at Sky High</h1><div class="m">Maya’s idea · shaped by Vera · decide by tonight, 8 pm</div></div>'
    '<div class="steps"><span class="step done">' + i("check", "sm") + 'Saturday</span><span class="step done">' + i("check", "sm") +
    'Sky High</span><span class="step open">Time?</span><span class="step open">Who’s in?</span></div>'
    '<div class="pencil" style="padding:14px"><div class="cap" style="margin-bottom:4px">How the day could go</div>'
    '<p class="glimpse" style="margin:4px 0 0">You get there when it opens and have the foam pit to yourselves for an hour. '
    'Maya works up to the big jump, and Theo finds the tiny dodgeball court and refuses to leave.</p></div>'
    '<div class="qa pencil"><div><div class="q"><span>What time?</span><span class="m">open 10–8</span></div>'
    '<div class="pills"><span class="pill">9:30 am</span><span class="pill">10 am</span><span class="pill">Afternoon</span></div></div>'
    f'<div><div class="q"><span>Who’s in?</span><span class="m">a parent’s yes sets it</span></div><div class="who">'
    f'<div>{av("Maya","md")}Maya · in</div><div>{av("Sam","md")}Sam · in</div>'
    f'<div><span class="av md ask">?</span>Alex</div><div><span class="av md ask">?</span>Theo</div></div></div></div>'
    '<div class="plain" style="padding:12px 14px"><div class="cap" style="margin-bottom:6px">Checked this morning</div>'
    f'<div class="facts"><span>{i("clock","sm")}Open today 10–8</span><span>{i("car","sm")}20 min</span><span>{i("dollar","sm")}$$</span><span>{i("ticket","sm")}Waivers online, walk-ins fine</span></div></div>'
    f'<div class="chair">{i("star")}<div><div class="t">One chair left empty</div><div class="m">Lunch somewhere you find on the way. Theo picks the place.</div></div></div>'
    '<div class="stack" style="align-items:center"><div class="acts" style="margin:0"><button class="btn pri off">Set the plan</button><button class="btn txt">Not this one</button></div>'
    '<div class="decide">2 things still open. If nobody sets it by tonight it goes back to Ideas.</div></div>')
page("2-plan", phone(plan, "home", bar("Change something…", ctx="Saturday at Sky High", quick=("Make it afternoon", "Add lunch", "Just the kids"))))

# ---------- 3. Calendar, phone ----------
def day(w, d, marks, now=False):
    m = "".join(f'<span class="mk {x}"></span>' for x in marks)
    return f'<div class="day{" now" if now else ""}"><span class="w">{w}</span><span class="d">{d}</span><span class="marks">{m}</span></div>'
strip = '<div class="strip">' + "".join([
    day("M", 12, [""]), day("T", 13, [""]), day("W", 14, ["bell"]), day("T", 15, [""]), day("F", 16, ["", "bell"], True),
    day("S", 17, ["", "pen"]), day("S", 18, ["bell", "pen"])]) + "</div>"
def dayh(l, r=""): return f'<div class="dayh"><b>{l}</b><span class="cap">{r}</span></div>'
def free(label, size, extra="", link="Ideas for this ›"):
    return f'<div class="free {size}"><div class="lab"><span>{label}</span><a>{link}</a></div>{extra}</div>'
cal = (
    '<div class="pagehead"><h1>Calendar</h1><div class="seg"><a class="on">Week</a><a>Month</a></div></div>' + strip
    + '<div class="agenda">' + dayh("Friday 16", "Today")
    + setrow("4:30 pm", "Theo’s swim lesson", "Northeast pool", avs("Theo"))
    + setrow(i("bell"), "Library books due Wednesday", "Alex", avs("Alex"))
    + free("Free from 5:30 pm", "s", "", "") + "</div>"
    + '<div class="agenda">' + dayh("Saturday 17", "Tomorrow")
    + f'<div class="prow pencil"><span class="tm">10 am?</span><div class="b"><div class="t">Sky High Trampolines</div><div class="m">Maya’s pitch · time? · who?</div></div><a>Shape it ›</a></div>'
    + free("Free 12 to 4:30 · 4½ hours", "m")
    + setrow("5 pm", "Portland Night Market", "20 min · everyone", avs("Sam", "Alex", "Maya", "Theo"))
    + "</div>"
    + '<div class="agenda">' + dayh("Sunday 18")
    + setrow(i("bell"), "Call Grandma", "Alex", avs("Alex"))
    + free("Open all day", "l",
           '<div class="prow pencil" style="background-color:#FBF8F0"><span class="tm">1 pm?</span><div class="b"><div class="t">Kites on Powell Butte</div><div class="m">Vera’s idea · 25 min · dry till 5</div>'
           '<div class="acts" style="margin-top:8px"><button class="btn sm pri">Yes</button><button class="btn sm">Not this one</button></div></div></div>', "More ideas ›")
    + "</div>")
page("3-calendar", phone(cal, "cal", bar("Find, or ask for a day…")))

# ---------- 4. Ideas, phone ----------
def ic(ico, title, meta, org, cls="", pale=False, found=False):
    q = '<div class="paleq"><a>Keep</a><a>Let it go</a></div>' if pale else ""
    return (f'<div class="ic {cls}">{tile(ico, "found" if found else "")}<div class="t">{title}</div>'
            f'<div class="m">{meta}</div><div class="org">{org}</div>{q}</div>')
def entr(ico, name, n): return f'<a>{tile(ico)}<span><b>{name}</b><small>{n} kept</small></span></a>'
ideas = (
    '<div class="pagehead"><h1>Ideas</h1><span class="m">42 kept</span></div>'
    '<div class="entr">' + entr("utensils", "Eat", 14) + entr("mountain", "Go out", 18) + entr("home", "Stay in", 6) + entr("suitcase", "Trips", 4) + "</div>"
    f'<div class="sift"><span class="chip">{i("clock","sm")}Any time</span><span class="chip">{i("leaf","sm")}Any energy</span><span class="chip">{i("people","sm")}Everyone</span>'
    f'<span class="chip surprise">{i("dice","sm")}Surprise us</span></div>'
    + sec("Ends soon", '<div class="rail">'
          + ic("ticket", "Pumpkin carving, Tryon Creek", "Sat and Sun · free", "Vera found this", found=True)
          + ic("star", "Portland Night Market", "Last one this Saturday", "Sam’s idea") + "</div>")
    + sec("Good for a rainy day", '<div class="rail">'
          + ic("bulb", "OMSI", "Science museum · 18 min", "Maya’s idea")
          + ic("heart", "Pottery café", "Paint a mug · 15 min", "You liked somewhere like this") + "</div>")
    + sec("Been meaning to", '<div class="rail">'
          + ic("star", "Hopscotch", "Portland · 25 min", "Maya’s idea")
          + ic("pen", "Pottery class", "Beginner · Saturdays", "Saved in March · still want this?", cls="pale", pale=True) + "</div>"))
page("4-ideas", phone(ideas, "ideas", bar("Search ideas, or ask Vera…")))

# ---------- 5. Lists, phone ----------
def li(title, meta, rt="", extra=""):
    return f'<div class="li plain"><span class="tick"></span><div class="b"><div class="t">{title}</div><div class="m">{meta}</div>{extra}</div><div class="rt">{rt}</div></div>'
def cond(ico, t): return f'<span class="cond">{i(ico,"sm")}{t}</span>'
lists = (
    '<div class="pagehead"><h1>Lists</h1></div>'
    '<div class="lpills"><span class="chip">Shopping <b>6</b></span><span class="chip on">Reminders <b>5</b></span><span class="chip">Camping trip <b>8</b></span>'
    '<span class="chip">Maya <b>3</b></span><span class="chip">Theo <b>2</b></span></div>'
    + sec("Reminders", '<div class="stack">'
          + li("Library books back", "Wednesday", avs("Alex") + '<span class="m">on it</span>')
          + li("Book Theo’s dentist", "Next free moment", '<button class="btn sm">I’ll handle it</button>')
          + li("Field trip form, bring $5", "Due Monday · from Maya’s flyer", '<button class="btn sm pri">Accept</button>',
               cond("eye", "Vera read the photo; check the date"))
          + li("Rain jackets by the door", "", "", cond("sun", "Waits for rain"))
          + li("Sharpen the knives", "", "", cond("clock", "Some Saturday morning")) + "</div>")
    + sec("Maya’s list", '<div class="plain" style="padding:4px 14px">'
          f'<div class="wishrow"><span class="rank">1</span><div class="b t">Roller skates</div><span class="tag">Wanted</span></div>'
          f'<div class="wishrow"><span class="rank">2</span><div class="b t">Sketchbook, thick paper</div><span class="tag amber">Being considered</span></div>'
          f'<div class="wishrow"><span class="rank">3</span><div class="b t">Glow-in-the-dark stars</div><span class="tag set">Done</span></div></div>',
          '<a>All lists ›</a>'))
page("5-lists", phone(lists, "lists", bar("Add to a list, or ask Vera…")))

# ---------- 6. A kid's Home ----------
def opt(ico, title, voted):
    v = f'<div class="m" style="display:flex;gap:6px;align-items:center">{avs(*voted)} picked this</div>' if voted else '<div class="m">No picks yet</div>'
    return f'<div class="opt">{tile(ico)}<div class="t">{title}</div>{v}<button class="btn sm pri">I pick this</button></div>'
kid = (
    '<div><div class="cap">Friday 16 October</div>'
    f'<div class="herline">{VS}<p>Hi Maya! Sky High is almost set. Mom and Dad are picking a time.</p></div></div>'
    + sec("Today", '<div class="stack">' + setrow("4 pm", "Piano", "15 minutes", "") + "</div>")
    + sec("Your pitch", f'<div class="pencil" style="padding:14px"><div style="display:flex;gap:12px;align-items:center">{av("Maya","lg")}'
          '<div class="b"><div class="t" style="font-size:19px">Sky High Trampolines</div><div class="m">Being shaped</div></div></div>'
          f'<div class="journey"><span class="s on">{i("check","sm")}Pitched</span><i></i><span class="s on">{i("check","sm")}Shaped</span><i></i><span class="s">Mom and Dad’s yes</span></div></div>')
    + sec("Help choose", '<div class="m" style="margin:-2px 0 10px">Sunday afternoon: which one do you want most?</div><div class="choose">'
          + opt("sun", "Kites on the hill", ["Theo"]) + opt("leaf", "Pumpkin carving", []) + "</div>")
    + sec("My list", '<div class="plain" style="padding:4px 14px">'
          '<div class="wishrow"><span class="rank">1</span><div class="b t">Roller skates</div></div>'
          '<div class="wishrow"><span class="rank">2</span><div class="b t">Sketchbook, thick paper</div><span class="m">Parents are thinking</span></div>'
          '<div class="wishrow"><span class="rank">3</span><div class="b t">Glow-in-the-dark stars</div><span class="tag set">Yes!</span></div></div>')
    + '<p class="end">That’s all for today!</p>')
page("6-kid", phone(kid, "home", bar("Tell Vera anything", note=f'{i("eye","sm")}Mom and Dad can read this · 12 messages left today'), who="Maya"), wrap="kid")

# ---------- desktop helpers ----------
def nav(on):
    items = [("home", "Home"), ("bulb", "Ideas"), ("cal", "Calendar"), ("list", "Lists")]
    return ('<aside class="nav"><span class="word">FamilyDB<span class="cur"></span></span>' + "".join(
        f'<a class="{"on" if k == on else ""}">{i(ic)}{lab}</a>' for k, (ic, lab) in zip(("home", "ideas", "cal", "lists"), items))
        + f'<div class="me">{av("Sam")}<span>Sam<br>Parent</span></div></aside>')
def vcol(title, sub, thread, barhtml):
    return (f'<aside class="vcol"><div class="vh"><span class="vs lg"></span><div><b>{title}</b><span class="m">{sub}</span></div></div>'
            f'<div class="thread">{thread}</div>{barhtml}</aside>')
def hers(text, *cards): return f'<div class="hers">{VS}<div class="say"><div>{text}</div>{"".join(cards)}</div></div>'
def mine(text, who="Alex"): return f'<div class="msg{" sam" if who == "Sam" else ""}"><div class="bub">{text}</div></div>'

# ---------- 7. Desktop Calendar with a plan open ----------
H = 48
def pos(a, b): return f'style="top:{(a-8)*H}px;height:{(b-a)*H}px"'
def blk(kind, a, b, title, sub=""):
    s = f"<small>{sub}</small>" if sub else ""
    return f'<div class="blk {kind}" {pos(a, b)}><b>{title}</b>{s}</div>' if kind != "free" else f'<div class="blk free" {pos(a, b)}>{title}</div>'
days = [("MON", 12, False, [blk("set", 16, 17.5, "Soccer", "Maya")]),
        ("TUE", 13, False, [blk("set", 9, 10, "Dentist", "Alex")]),
        ("WED", 14, False, [blk("set", 16, 16.5, "Piano", "Maya")]),
        ("THU", 15, False, [blk("set", 16, 17.5, "Soccer", "Maya")]),
        ("FRI", 16, True, [blk("set", 16.5, 17.5, "Swim lesson", "Theo"), blk("free", 17.5, 21, "Free evening")]),
        ("SAT", 17, False, [blk("pen", 10, 12, "Sky High?", "Maya’s pitch · who?"), blk("free", 12, 16.5, "Free 4½ h"), blk("set", 17, 20, "Night Market", "everyone")]),
        ("SUN", 18, False, [blk("free", 8, 21, "Open all day"), blk("pen", 13, 16, "Kites on Powell Butte", "Vera’s idea")])]
heads = '<div class="hd"></div>' + "".join(f'<div class="hd{" now" if n else ""}"><div class="w">{w}</div><div class="d">{d}</div></div>' for w, d, n, _ in days)
axis = '<div class="ax">' + "".join(f'<span style="top:{k*H}px">{(8+k-1)%12+1} {"am" if 8+k<12 else "pm"}</span>' for k in range(1, 13)) + "</div>"
cols = "".join(f'<div class="col{" past" if d < 16 else ""}">{"".join(b)}</div>' for _, d, _, b in days)
allday = ('<div class="allday"><div></div><div></div><div></div><div>' + f'{i("bell","sm")} Library books</div><div></div><div></div><div></div><div>{i("bell","sm")} Call Grandma</div></div>')
calmain = (f'<div class="pagehead"><h1>Calendar</h1><div class="seg"><a class="on">Week</a><a>Month</a></div></div>'
           f'<div><div class="wk">{heads}</div>{allday}<div class="wk">{axis}{cols}</div></div>')
thread = (
    hers("Saturday could go like this: you get there when it opens, and the foam pit is yours for an hour. Maya works up to the big jump.",
         '<div class="pencil" style="padding:10px 12px"><div class="tags"><span class="tag pen">Could do</span></div>'
         '<div class="t" style="margin-top:6px">Saturday at Sky High</div><div class="m">time? · who’s in?</div></div>')
    + mine("Morning, all four of us")
    + hers("Done: Saturday 10 am, all four. That clears both dashes. Set it?",
           '<div class="ink" style="padding:10px 12px"><div class="t">Saturday at Sky High</div><div class="m">10 am · all four · 20 min</div>'
           '<div class="acts" style="margin-top:8px"><button class="btn sm pri">Set the plan</button><button class="btn sm txt">Change something</button></div></div>'))
page("7-desktop-calendar", nav("cal") + f'<section class="dmain">{calmain}</section>'
     + vcol("Vera", "talking about this plan", thread, bar("Change something…", ctx="Saturday at Sky High", quick=("Add lunch", "Just the kids"))), cls="desk")

# ---------- 8. Desktop Home ----------
coming = (sec("Tomorrow", '<div class="stack">'
              + f'<div class="prow pencil"><div class="b"><div class="t">Sky High</div><div class="m">10 am? · pencil</div></div></div>'
              + setrow("5 pm", "Night Market", "") + "</div>")
          + sec("Sunday", '<div class="stack">' + setrow(i("bell"), "Call Grandma", "") + free("Open", "s", "", "") + "</div>")
          + sec("Next week", '<div class="m">Dentist Tuesday · soccer Monday and Thursday · piano Wednesday</div>'))
homedesk = '<div class="two"><div>' + home_body(True) + "</div><div>" + coming + "</div></div>"
dthread = (
    hers("Maya pitched Sky High Trampolines. It’s open Saturday 10 to 8 and 20 minutes away. Want to shape it?",
         '<div class="pencil" style="padding:10px 12px"><div class="tags"><span class="tag pen">Could do</span></div><div class="t" style="margin-top:6px">Saturday at Sky High</div><div class="m">time? · who’s in?</div></div>')
    + mine("Kenji’s Ramen on Division is really good. Jess says get the spicy miso.", "Sam")
    + hers("Saved it under Eat out. I’ll find the hours.", f'<div class="plain" style="padding:10px 12px;display:flex;gap:10px">{tile("utensils")}<div><div class="t">Kenji’s Ramen</div><div class="m">Eat out · tip from Jess</div></div></div>')
    + hers("It’s filled in: open till 9, 12 minutes away, walk-ins only."))
page("8-desktop-home", nav("home") + f'<section class="dmain">{homedesk}</section>'
     + vcol("Vera", "the family chat · also in Telegram", dthread, bar()), cls="desk")
print("built")
