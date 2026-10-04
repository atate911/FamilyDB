# Brief

You are a designer who specialises in products for children aged 8 to 13, writing as that age group would experience it.

The work: review the final design for the web page of a family planning app. Your lens: Judge it as Maya (11) or Theo (9) would: can they read it, find what is theirs, tell what they can and cannot do, feel it is for them and not only for the grown-ups, and use it without help? Note what is boring, confusing, babyish or off-putting for that age, and what they would like. The kids may sign in, chat, and keep their own wish list; they do not see Status or Settings.

## What it is

FamilyDB is a family planning assistant. One household runs it on its own small server. The
family talks to an assistant called **Vera** by text message (Telegram) or on this website, in
plain language: "what should we do this weekend?", "remind me to call the dentist on Tuesday",
"we should try that ramen place". Vera keeps track of things for them:

- **Ideas**: places to go and things to do that someone mentioned (outings, restaurants, trips,
  shows, seasonal things, gift ideas). Vera can look each one up (opening hours, drive time from
  home, price) and suggest what fits a free weekend, given the weather and the calendar.
- **Plans**: ideas that made it onto the family calendar (it can be linked to Google Calendar).
  After a plan, Vera asks how it went.
- **To do**: errands and things to arrange, with an owner, a due date and an optional reminder,
  which Vera sends by message when it's due.
- **Wishes**: each kid keeps a ranked wish list; the parents decide on the wishes.
- **Memory**: things Vera has learned about the family ("Theo is allergic to peanuts"), which
  anyone can review and make her forget.

Most of the talking happens in Telegram. The website is where the family:

1. talks to Vera when they're at a computer or don't use Telegram;
2. sees everything at a glance and browses it: what's coming up, what's overdue, what's on the
   idea list;
3. changes things by hand (edit an idea, move a plan, tick off a to-do);
4. checks that it's working and what it is costing (Vera runs on a paid AI model, with a daily
   spending limit the family sets);
5. changes settings, and sets the app up the first time.

## Who uses it

A family: two parents and two kids, on phones and on a laptop. Each person signs in as
themselves. The parents and the kids see slightly different things (a kid sees her own to-dos and
wish list, not the settings). Nobody is technical except perhaps one parent. The kids must be able
to use it.

## The pages

These seven pages are shown. The rest of the app would follow the same design.

1. **Home**: the first page after sign-in. It must let someone write to Vera straight away, and
   show what matters today: the next plan and what's coming up, to-dos (especially overdue ones),
   recently added ideas, the kids' wish lists, and, while setup is unfinished, what's left to set
   up.
2. **Chat**: the conversation with Vera on the web. The family's shared conversation, plus each
   kid's own conversation with Vera, which the parents can read. A box to write in, a choice of who
   is writing (on a shared computer), and an option to send where you are.
3. **Ideas**: the whole list, with search and filters (kind, status, who it's for), a separate view
   of restaurants, a quick way to "save a thought for later", and a button to add an idea. Each
   idea shows its kind, who it's for and how far it is from home.
4. **Plans**: the calendar view of plans for the month (there is also a list view).
5. **To do**: the to-dos, filterable as open, done, cancelled or all, with search, a quick add, a
   tick to mark one done, and an edit link. Each shows who owns it, when it's due and whether it
   has a reminder.
6. **Status**: is it working, and what is it costing? Spend today against the daily limit, calls
   and cost over 30 days, which AI model answers each kind of job (chat, the weekend digest, web
   lookups), whether there's a fallback, and the state of each connection (AI keys, Telegram,
   Google Calendar).
7. **Settings**: a list of the settings sections, each saying in a line how it stands now, with
   anything that needs attention made obvious. The sections: Sign-in and security; General;
   AI model; Spending; Messages; Lookups; Personality and family; Connections; What has changed.

Other pages exist (an idea's own page, add an idea, the plans list, wishes, family, memory, your
password, the first-time setup steps, sign in). You don't need to draw them.

## How the real page is built (facts, not taste)

It is a server-rendered web page: HTML and one stylesheet, an icon set, and very little
JavaScript. It loads no scripts from anywhere else and must work with scripting off, so design
with HTML and CSS. It must work at phone width as well as on a desktop, be readable, show keyboard
focus, and be usable by kids.

## What you have

A folder named `final/` in your folder (a link to shared files; read from it freely):
- `final/overview-desktop.jpg`: the seven main pages on a desktop (Home, Chat, Ideas, Plans, To do, Status, Settings) as an admin parent (Sam) sees them, top part of each, half size. Read this first.
- `final/overview-phone.jpg`: the same seven pages on a phone.
- `final/overview-more-pages.jpg`: the other thirteen pages: a kid's Home, Chat and To do (Maya, 11), Wishes for a kid and for a parent, the phone's More page, sign-in, the page a kid sees if they open a grown-ups' page, an idea's own page, the add-an-idea form, and three sheets of states (limits, outages, waiting, errors, empty, busy, long content).
- `final/overview-dark.jpg`: the seven main pages in dark mode.
- `final/desktop/<page>.jpg`, `final/phone/<page>.jpg` and `final/dark/<page>.jpg` (and `<page>-phone.jpg`): every page full length. Page names: home, chat, ideas, plans, todo, status, settings, home-kid, chat-kid, todo-kid, wishes, wishes-kid, more, signin, grownups, idea, idea-new, states, states-actions, states-content.
- `final/source/`: the HTML for every page, the one stylesheet `style.css`, the icon sprite, and `STANDARD.md`, the written design standard (tokens, components, words, phone rules, states, accessibility numbers, notes for the engineer). Read them where they help you judge.

These are standalone HTML and CSS pages drawn for an app that is server-rendered (Flask and Jinja templates, one stylesheet, an icon sprite, a content security policy with no inline styles or scripts, every form working with scripting off). In the app each person signs in as themselves; a kid may read ideas and plans, chat with Vera within a daily number of messages, and keep their own wish list, and changes nothing else; presents never show where a kid reads. This design has been chosen as the look for the app and is meant to be final. Your job is to say whether it is ready to build, and what, if anything, must still change.

Look at every overview, then open full-length pages wherever you want to check something, on desktop and phone (and dark mode if it matters to your lens). Do not judge from the overview alone where the full page shows something different. Be specific; do not invent anything you cannot see. Cite the page and the element.

## What to write

Write `review.md` in your folder with exactly these sections:

## Verdict
A mark out of 10 for the design as seen through your lens, and two sentences on why. Then one line: **Optimise before building?** Yes or No, and the one reason.

## Protect
The things that work and must not be lost. Up to six, each one line, naming the page and element.

## Fix, ranked
Up to ten items, most valuable first. For each:
**N. Short title** (page and element)
- Problem: what is wrong and who it hurts.
- Fix: what to change, specific enough to do.
- Severity: blocker, major or minor. Effort: S, M or L.

## Missing
What the pages do not show but the real app will need, from your lens. Up to eight lines.

## One sentence
If you could change one thing, what is it?

When you are done, reply with the verdict line and your top three fixes.
