You are an expert creative graphic and interface designer.

# The brief: design the web interface for FamilyDB

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

## The pages you are asked to design

Design these seven pages. Your design should also suggest how the rest would follow.

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

## The family and their data (use this as the content)

Today is **Saturday 3 October 2026**. The family lives in Vancouver, WA (times as America/
Vancouver; °C and kilometres).

- **People**: Sam (admin, a parent), Alex (parent), Maya (kid), Theo (kid).
- **Plans**: Pho Oregon, Tue 29 Sep 17:00 (past); Silver Falls hike, Thu 1 Oct 10:00 (past); Oaks
  Park roller rink, **Sun 4 Oct 13:00 (tomorrow, the next plan)**; Mount St. Helens day trip, Fri 9
  Oct 09:00; Nutcracker at the Keller, Sat 17 Oct 19:00; Cannon Beach weekend, Sat 24 Oct 08:00.
  Google Calendar is not connected yet, so these are the plans Vera made.
- **To do** (4 open, 3 overdue): Call the dentist about Theo (Alex, was due 27 Sep); Book the
  campsite at Silver Falls (Sam, was due 28 Sep); Buy Maya's birthday present (Alex, was due 1
  Oct); Renew library cards (household, no date). None has a reminder set.
- **Ideas** (12, about 10 looked up): with kind, who it's for, and drive time from home:
  1 Oaks Park roller rink (activity, Maya and Theo, 27 min S); 2 Pho Oregon (restaurant, anyone,
  21 min SE); 3 Silver Falls hike (outing, Sam and Alex, 2 h 10 min S); 4 Cannon Beach weekend
  (trip, anyone, 2 h 45 min W); 5 Mount St. Helens day trip (day trip, anyone, 2 h 5 min NNE);
  6 Nutcracker at the Keller (show, Maya, about 20 min S); 7 Pumpkin patch at Bi-Mart farm
  (seasonal, Theo, 18 min NW); 8 Science museum night (event, anyone, about 19 min S); 9 Lava tubes
  at Ape Cave (outing, anyone, about 1 h 50 min NE); 10 Ramen at Afuri (restaurant, anyone, about
  22 min S); 11 Board game night (activity, not looked up yet); 12 Lego set for Theo (other, not
  looked up yet).
- **The conversation**: Sam, 27 Sep 19:47: "What should we do this weekend?" Vera, 19:48:
  "Saturday looks dry: the Silver Falls hike fits the morning, and Pho Oregon is open for dinner.
  Sunday has rain after noon, so the roller rink works as a backup." Alex, 19:52: "Put the hike on
  Saturday at 10." Vera, 19:53: "Done: Silver Falls hike, Saturday 10:00 to 14:00."
- **Wishes**: Maya and Theo have no open wishes yet.
- **Setup**: 3 steps left: choose your own password so everybody signs in as themselves; add a
  Telegram bot so the family can message Vera from their phones; connect Google Calendar.
- **Status**: the AI is OpenAI's gpt-6-luna for chat, the weekend digest and web lookups; no
  fallback (only one company's key). Keys: OpenAI set; Claude (Anthropic) and Gemini (Google)
  not. Spent today about $0.00 of a $2.00 daily limit; a usual day about $0.04. Last 30 days: 6
  calls, $1.26, 0% from the cache. Telegram not set up; Google Calendar not connected.
- **Settings as they stand**: Sign-in and security: needs a look (still the password the
  installer made). General: Vancouver, WA; °C and kilometres. AI model: OpenAI, gpt-6-luna.
  Spending: up to $2.00 a day, about $0.00 spent today. Messages: no weekend ideas, since no chat
  is chosen for them; asks how a plan went at 10:00. Lookups: off. Personality and family: Vera,
  as first written; nothing about the family yet. Connections: Telegram not set up; Calendar not
  connected. What has changed: nothing yet.

## How the real page is built (facts, not taste)

It is a server-rendered web page: HTML and one stylesheet, an icon set, and very little
JavaScript. It loads no scripts from anywhere else and must work with scripting off, so design
with HTML and CSS. It must work at phone width as well as on a desktop, be readable, show keyboard
focus, and be usable by kids.

## What you have, and what to make

You start from nothing. You have not seen this app and there are no earlier designs to follow.
The name, the look, the type, the colour, the layout, the wording, what each page shows first and
how it is organised are all yours. If you think a page above should work differently, design it
your way and say why.

Work only inside your own folder (given below). Do not read or open anything outside it except
your own `_kit/` (the render script); in particular, do not look in /home/user or at any other folder in the
directory above yours.

Make, in your folder:

1. Seven standalone HTML files, one per page: `home.html`, `chat.html`, `ideas.html`,
   `plans.html`, `todo.html`, `status.html`, `settings.html`, all with the content above. Put
   the shared CSS in one `style.css` beside them. Each page should look real: navigation,
   headings, content, controls, and the page's actual data. You may draw pictures (inline SVG or
   CSS); no raster stock images. Fonts: any Google Fonts family (link
   `https://fonts.googleapis.com/css2?...`), with a fallback. No JavaScript.
2. Every page must work at 1280 px and at 390 px (a phone) without sideways scrolling.
3. Render with `./_kit/render.sh .` from your folder. It writes `shots/<page>.png` at 1280 wide and
   `shots/home-phone.png` and `shots/chat-phone.png` at 390 wide. **Look at every shot** and fix
   what's wrong. Aim for at least two rounds of looking and fixing. You are judged on the shots.
4. `DESIGN.md`, at most 400 words: a name for your design, its idea in one sentence, the look
   (type, colour, layout), what each page puts first, and why it suits this family and this app.

When you're done, reply with your design's name, its one-sentence idea, and anything you know
is unfinished.
