# Brief

You are a parent in this family (Sam or Alex): not technical, tired, usually on a phone, short of time, who has to trust it with the household.

The work: review one design for the web page of a family planning app. Your lens: Judge it as that person. What do you understand at a glance and what do you not? What would you trust and what worries you (cost, kids reading it, who sees what)? What would you do first? What would make you stop using it? Write in the first person where it helps.

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

A folder named `a1/` in your folder (a link to shared files; read from it freely):
- `a1/overview-desktop.jpg`: the seven pages on a desktop (Home, Chat, Ideas, Plans, To do, Status, Settings), top part of each, half size. Read this first.
- `a1/overview-phone.jpg`: the same seven pages on a phone, top part, small.
- `a1/desktop/<page>.jpg`: each page full length at 1280 px wide (home, chat, ideas, plans, todo, status, settings).
- `a1/phone/<page>.jpg`: each page full length on a phone (390 px wide, drawn at 2x).
- `a1/source/`: the HTML for the seven pages and the one stylesheet, `style.css`. Read it where it helps you judge; you are not expected to read every line.

This is a mockup of seven pages drawn from a written description. It is a standalone set of HTML and CSS, not the app. The other pages of the app (an idea's own page, add an idea, wishes, family, memory, your password, first-time setup, sign in, the settings sections) were not drawn. The design in these pictures has been chosen as the look for the app. Your job is to say whether it should be optimised before it is built, and how.

Look at every overview, then open full-length pages wherever you want to check something: at least Home, and as many others as you need to judge fairly, on desktop and phone. Do not judge from the overview alone where the full page shows something different. Be specific; do not invent anything you cannot see. Cite the page and the element.

## What to write

Write `review.md` in your folder with exactly these sections:

## Verdict
A mark out of 10 for the design as seen through your lens, and two sentences on why. Then one line: **Optimise before building?** Yes or No, and the one reason.

## Protect
The things that work and must not be lost when it is changed. Up to six, each one line, naming the page and element.

## Fix, ranked
Up to ten items, most valuable first. For each:
**N. Short title** (page and element)
- Problem: what is wrong and who it hurts.
- Fix: what to change, specific enough that a designer or engineer can do it (give values, wording or a sketch in words where it helps).
- Severity: blocker, major or minor. Effort: S, M or L.

## Missing
What the seven pages do not show but the real app will need, from your lens: states, pages, edge cases. Up to eight lines.

## One sentence
If you could change one thing, what is it?

When you are done, reply with the verdict line and your top three fixes.
