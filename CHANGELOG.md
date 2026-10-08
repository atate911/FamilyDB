# Changelog

## v0.3.0 — in progress

Still being built. While this heading says "in progress", an install follows the
default branch rather than a release tag, and an upgrade never moves to anything
older than what is installed. It gets a date when it is released.

### New since v0.2.0

- **Troubleshooting**, for admins, on the settings page. What went wrong in one place: what needs
  an admin, messages that did not go through, lookups that failed, calls to a model that failed
  and why, and a problem log of the warnings and errors the server logged (the same trouble
  again is one line with a count). Beside it, the words of every call to a model, as sent and as
  answered, with the instructions and tools it started from, and a link to them from each model
  call on a message's history. Log levels are on the page too: what the server writes, how much
  of it is kept to read, and a different level for one part (models, Telegram, jobs, the web
  page...), so chasing one problem needs no flood from the rest. The models' words are kept for
  14 days unless the family says otherwise (0 keeps none), go sooner with the messages if those
  are set to be forgotten sooner, and go for good with a person taken off. They hold the
  family's own words, which an admin can read; a backup keeps what it held.
- **Looks.** Each browser can choose how the page looks on a new Look page, in
  the bar's menu for anybody signed in: Phosphor, as before, or Midnight, Home
  Computer, Ink, Enamel, Rail yellow or Fjord, each by day and by night, and
  whether to follow the device's day and night or hold to one. The choice is
  kept in the browser and touches nothing the family's data holds, and every
  look is tested for readable contrast by day and by night.
- **A new look, Kitchen Table.** FamilyDB has a new look: cream paper by day,
  charcoal at night, deep green for what you act on, and each of you in your
  own colour. It is what everybody sees now, except anybody who chose a look
  before, who keeps theirs. To change yours, open Look from the menu.
- **A new menu and a new Home**, the first pages of the new layout (the others
  follow, one at a time). A sidebar on a computer, a tab bar on a phone, Vera's
  state in a pill, and counts beside the pages that need somebody ("3 late",
  "1 to decide"). Home opens with a greeting and one line on what is coming and
  what is late, then Vera's box, what is next (with who it is for and how far
  it is), your to-dos, what was just added, the kids' lists, and, for
  grown-ups, "How did it go?" for a plan nobody has rated and what Vera cost
  today. A kid's Home is simpler: her box, what is next for her, her list and
  her own to-dos. The ways to start under the box are gone. Each of you has a
  colour, kept with your name.
- **A new Chat.** Each person's messages wear their own colour and letter, the
  day is said where it changes, and Vera is her screen beside her lines. A
  parent moves between the family's conversation and each kid's (the list
  shows when a kid last wrote, never what), a kid is told who can read hers,
  and "Earlier messages" goes further back. While Vera is writing back, the
  page looks again soon, then less often, then stops and leaves a link: "Check
  for her answer".
- **A new To do and a new Plans.** Each to-do has its own Edit page instead of
  a form that opens in the list, shows who it is for in their colour, and tells
  a kid who set it ("Set by Alex"). Plans open as a month, with each plan on its
  days in the colour of who it is for, and a list beside it; a plan that has
  happened asks how it went right there, with three faces. A kid sees one list
  of what is next.
- **A new Ideas, idea page, idea form and Restaurants.** Idea cards show whom each
  is for in their colours, how far away it is and whether it is a surprise; the map
  of how far each idea is from home now has each idea's name beside its dot, drawn
  to fit a phone as well as a desktop. A present is kept from every kid, always, and from the grown-up it is for (you can
  keep it from another grown-up too on the idea), and every page that shows it says
  whom: "Hidden from the kids and Alex". The to-dos about it are kept from the same
  people, and Vera still never tells a kid of one in the chat.
- **A new Kids' lists and What Vera knows.** Each kid's lists are one line to a
  wish that opens to its buttons, with a grip to drag it (where scripts run);
  a parent answers inside the line, sees what Vera turned away beside the list
  and what was answered lately, and a kid sees what to do next about what Vera
  could not put on her list. What Vera knows groups what the family has told her
  by person, in each person's colour.
- **A new Family, Your password and Look.** The family list, each person's page
  and the password pages are redone, with a starting password shown once in a
  box of its own. Each person's look is now kept with them, so it comes with
  them to every phone and computer they sign in on, and everybody else keeps
  their own. A new look, Afterglow, joins the others: charcoal glass with faint
  scanlines, always night.
- **A new Settings.** The list of settings is one row to a part, each saying
  how it stands now and tagged when it needs a look or is switched off, with
  the sections beside each other on every page. Every section is redone on the
  new look: the same settings and the same saving, with each one's help under
  it, and a bar at the foot of a form that says what an empty box does. The
  sign-in page now says "the one FamilyDB started with" for the first password.
- **A new Setup.** The list of steps, each step and the last page are on the
  new look: a row to a step tagged Done, Needed, Recommended or Optional, the
  steps along the top, Back and Next at the foot, and the Calendar step in three
  cards. What each step asks and does is as before. Where it said "the password
  the installer made up" it now says "the password FamilyDB started with".
- **A new Status, activity, sign-in and error pages.** Status opens with one
  line on whether she is ready and what is worth a look, then today's spending
  against the limit, how each part is doing (with a button beside the ones that
  need something), and the rest as before. It is for every grown-up, a parent
  included; a kid has no Status and no health pill. One message's full history,
  the sign-in page, "Page not found" and the pages that say "for an admin" or
  "for grown-ups" are on the new look too. A kid who opens Settings is told who
  to ask.
- **The old look's leftovers are gone.** Every page is on Kitchen Table now, so
  the old stylesheet, icon sheet, menu script and favicons are removed, and the
  home-screen icon and the page's tab icon are FamilyDB's own mark.
- **After the design review.** Times are 12-hour ("9 am", "1:30 pm") and the page
  is spelled the American way. Plans can be made, moved and canceled without Google
  Calendar (FamilyDB keeps them, and copies them across once a calendar is connected).
  The kids' card on Home counts what waits on the right kid, the phone's month draws a
  dot for each person on a plan, and a kid never sees the tools Vera ran under her
  replies (a grown-up reads what was done, in words). The chat is as high as the
  window on a computer, can be told to stop updating itself, and clock times no longer
  have a slashed zero. Ideas has one Search; on a phone Home puts the setup strip
  under the plans; the top bar stays put and keeps clear of a notch; a place's phone
  number can be tapped to call; an old browser that cannot do day-and-night colours
  gets plain ones. A ticked-off to-do has an Undo, and a kid's To do keeps this week's
  under "Done lately".
- **Reminders reach the person they are for.** A reminder set on the page, or
  set for somebody else ("remind Alex to..."), goes to that person's own
  Telegram chat with Vera, saying who asked, or to their conversation on the
  page until they open one. One for everyone goes to the family's chat, a new
  setting on Connections. Taking somebody off cancels the to-dos they owned
  outside the family group, which would otherwise have become everyone's.
- **Plans work without Google Calendar.** They are kept here, count as busy
  time for suggestions and nudges, and go onto Google once it is connected.
  A plan made on the page is checked the evening before and asked about after,
  like one made in a chat; a plan that moves is checked again for its new day;
  and the evening check runs every hour until ten, so a plan made late for
  tomorrow is still caught.
- **A reminder before a plan moves with it.** "Remind me a week before the
  concert" is tied to the concert: it moves when the concert does, by Vera or
  in Google, goes if it is canceled, says when the concert is, and is done
  once it is over.
- **Suggestions look at every idea.** Every saved idea is checked, not only the
  first eight, and asking again brings others up. "The kids" now finds an idea
  saved "with the girls", and an idea whose plan has passed can be suggested
  again.
- **To-dos do not get lost.** "Next time I have some free time" and "this
  weekend" are understood, so Vera brings them up then; when nothing will
  bring one up, she offers a reminder. /tasks shows a reminder already sent,
  and Tomorrow under a reminder is never the middle of the night.
- **A morning message.** At seven (Messages, Each morning), one message a chat
  with what is on today, a reminder from yesterday nobody acted on, what is due
  tomorrow, and on Sundays the to-dos nothing will bring up. An idea that ends
  this week, with a free day before then, is mentioned once. Nothing is sent on
  an empty day, and each part has its own switch.
- **Notices on phones and tablets for people who use only the page.** The Chat
  link says how many of Vera's messages are new, and each of you can turn on
  notices for your own device under Your password: "Vera has a message", never
  her words. On an iPhone or iPad the page must be added to the Home Screen
  first.
- **Undo.** "Undo that", /undo, an Undo beside the page's notice after a change,
  and a ↩ Undo button under her reply in your own Telegram chat take back your
  last change within a day: an idea added or changed, a to-do, a plan made or
  moved, something remembered, a list change. What cannot be taken back (how a
  plan went, a message already sent) is said so. An idea's page and a to-do say
  who changed them last, and from where.
- **Shopping lists.** "We're out of milk" goes on the shopping list, once however
  it is written; other lists by name ("the hardware list"). /list on Telegram
  shows it with a ✓ to tap for each thing, and a new Lists page (in the menu on
  a phone) adds, ticks and clears. For now a kid can read the lists and is told
  to ask a parent to add.
- **Buttons on the page.** A reminder in the page's chat has Done and the
  snoozes under it, as on Telegram, so a kid without Telegram can tick off her
  own. On Telegram, a tap takes away only the row it was on.
- **A clash is said.** A plan made or moved onto something already on the
  calendar says what it clashes with.
- **Getting things in.** Several ideas at once on the new-idea page, one a line;
  a photo from the page's chat, as from Telegram; and on Android, sharing a page
  or some words to the installed page opens the chat with them in the box.
- **Your favorites can win.** Ask for "our usual" or something you know you'd
  love, and what you loved comes first. A restaurant you went to is offered again
  after three weeks, an activity after a month, a day trip after six months. One
  disappointing visit no longer rules a place out for good: it is offered with
  the rating said, and only two low ratings in a row in the same year leave it
  out. "How was it?" now has Loved it, It was OK, Not again and Didn't go.
- **Firm rules are kept.** Tell Vera "no drives over 30 minutes until my back is
  better", or "nothing loud", and suggestions keep to it, saying why something
  was left out, including /now and the evening backup. What she remembers shows
  what each rule holds.
- **Ages.** An idea can say the ages it suits ("ages 6+"), and one a kid coming
  is too young or too old for is left out, with the reason.
- **Lookups fill in more.** When Vera looks an idea up, what it costs, indoors or
  out, how long a visit takes, whether to book, the ages it suits, and an
  event's dates go on the idea, where you had not said already. Asked for
  something cheap, an idea whose price nobody knows is said as such.
- **Now means now.** "Now" and "today" are judged by their own hours, so rain this
  morning does not rule out this afternoon, and the evening check looks at the
  hours of the plan itself.
- **What is over leaves the list.** An event a week past its last day is taken
  off overnight (Lookups page); its page can bring it back.
- **Places on the web, if you want them.** Asked for a kind of place nothing on
  your list fits ("Thai food, what's open now?"), Vera can look nearby and offer
  a few, said as found on the web. It costs a little each time, so it is off
  until you turn it on (Lookups, "Look for a place when nothing saved fits").
- **Your data, to take away.** Download the plans for another calendar, and the
  ideas and to-dos as spreadsheets, from the foot of those pages; an admin can
  download everything the family has kept, after typing their password again.
  `familydb export` does the same on the server. Never a key or a password.
- **How long messages are kept is yours to choose.** For good, as before, unless
  you set a number of days under Sign-in and security: older messages then keep
  their place in the conversation but not their words.
- **Backups that are checked.** Each night's backup is read back to make sure it
  could be restored, Status says when the last good one was, and admins are told
  when none has worked for a day and a half, or the disk is nearly full. A
  Telegram token that stopped working shows on Status.
- **A health check that means it.** `/healthz` and the new `familydb health` say
  whether the database answers and the scheduled jobs are running, and Docker
  uses it to mark the bot unhealthy.
- **What's new** at the bottom of the Status page: this list, for the version
  running.
- **What's going down?** What is on near home, found by the app: the calendars
  of the library, the city, parks and venues near you (it looks for them itself
  and offers them to tick), Ticketmaster's shows with a free key, and a weekly
  search. A third tab beside Plans' Month and List, for grown-ups, and offered
  in the suggestions. Reading calendars and Ticketmaster asks no model; the
  search and the calendar lookup are held to their own US$1 a month.
- **Vera's picks, chosen with everything she knows.** For "what should we do
  this weekend?" or "where should we eat tonight?", and the Thursday digest, a
  stronger model is given what the family has told her and done (ratings and
  notes, what she remembers, the weeks around, this chat) and chooses a
  favorite, something new and a wildcard, each with a reason; Vera says them.
  Within US$5 a month (AI model settings, "Choosing the suggestions"); never for
  a kid's question or one about right now.
- **Plainer words in the upgrade.** The upgrade no longer says migrations "never
  rewrite" what is there: they can, so it says the backup taken first covers it and
  that going back means restoring that backup.


## v0.2.0 — second alpha (2026-10-05)

The second alpha: everything the first did, and the kids, the persona, voice and
photos, and much more done by code with no model call. Everything below has been
running against the tests and a scripted install; most of it has not yet been
lived with for a month, which is what this alpha is for. An install follows the
newest release, and an upgrade never moves to anything older than what is
installed.
- **A guide for grown-ups.** A new Guide page (in the menu for parents and admins, never a
  kid's) explains how FamilyDB works and how to look after it, with search: using it,
  running the server, security and trust, the pieces, what it does on its own, the outside
  services, and a reference with a "How do I...?" index, a glossary, the known limits and a
  map to the developer documents. Its 69 pages are Markdown in `src/familydb/wiki/`. Status
  and each settings page also carry a Guide button to the matching page.

### New since v0.1.0

- **The kids have their own place.** Each kid signs in to her own simpler pages
  and her own conversation with Vera, keeps wish lists that only she and her
  parents see, ticks off her own things to do, and has a number of messages a
  day. She is never shown how the bot works, and presents are kept from her.
- **Vera is a persona the family can shape:** call her by another name, rewrite
  her character, add notes on how she talks, or choose a shorter Vera.
- **It hears and sees.** Voice notes and photos on Telegram, and a mic beside
  each box on the page.
- **More it does by itself, with no model call:** things to do that come round
  again, birthdays with their gift ideas, a task brought up when its kind of
  morning comes round free, buttons under a reminder, /today, /week, /tasks,
  /now and /lookup, and a check the evening before a plan.
- **It remembers what the family says about itself,** riding on the call that
  was happening anyway, and the page lists and forgets it.
- **It keeps costs down on its own:** GPT-6 Luna by default, each company's
  models by level, lookups gathered into one evening run, a burst of messages
  answered in one reply, a daily check of the companies' models and prices, and
  admins told on Telegram when something only they can fix goes wrong.
- **Everyone signs in as themselves,** with three roles, and setting up, the
  settings and the Family page are all on the page, in short parts.
- **Google Calendar connects with a service account,** a key pasted into the
  page, and stays in step with one request.
- **Installing is one block pasted into a server,** with HTTPS in front, the
  page's port movable, and an uninstall that starts from zero.

### What it does

- **Looks the page can wear.** Besides Phosphor, the green-screen look it was
  drawn in, each browser can choose Midnight, Home Computer, Ink, Enamel, Rail
  yellow or Fjord on the Look page (in the bar's menu, for anybody signed in),
  each with a day and a night, following the device or held to one. It is kept
  in the browser, so a phone and a wall tablet can differ. Vera's green screens
  stay green glass in all of them, and every look keeps the same contrast floors
  by day and by night.
- **Captures ideas from chat.** "We should try that ramen place sometime" becomes
  a stored idea, tagged with what the model can infer, through Telegram, the web
  page's chat or the console.
- **Hears voice notes.** A voice note on Telegram, as long and rambling as
  anyone likes, is written down by a speech model (OpenAI's, or Gemini's; Claude
  cannot hear) and answered as if it had been typed. The words are kept, marked
  as a voice note; the recording is not. Voice notes can be turned off, capped in
  length and pointed at either company on the settings page, and hearing them
  counts against the daily limit like any other call.
- **Acts on every part of a long message.** A rambling message or voice note
  that saves an idea, puts one thing on the calendar and cancels another is done
  in full, one line of reply per thing done. Whether it is a plan or an idea is
  decided by commitment; a swap puts the new plan on before taking the old one
  off. Ideas tied to dates (a festival, a show's run, a concert on the 18th) keep
  them, and are only suggested on those days. Events somebody put on the calendar
  by hand can be moved or taken off too, not only the bot's own.
- **Remembers what the family says about itself.** "The girls are vegetarian
  now", "Alex is allergic to shellfish", "no long drives until my back is
  better": kept, about the person it concerns, as a must or a taste, with its
  end date when it has one, and weighed whenever it bears on a question. It
  rides on the call that was happening anyway, and "noted" costs no second one.
  A page, "What Vera remembers", lists all of it with where each came from, and
  forgets anything for good: what was forgotten is not brought back from what
  was said before.
- **Fills them in.** A background worker turn looks each new idea up on the web:
  address, opening hours, booking link, price notes, a geocoded travel estimate.
  The lookups wait for the evening (21:00 unless changed) and run together, with
  one note to each chat for what was found; "look it up now", or /lookup on
  Telegram, has them looked up within a couple of minutes. Looking each up as it
  comes is a setting.
- **Keeps the calendar.** Confirmed plans are created, moved and cancelled on the
  shared Google Calendar from chat, and free time is read back live.
- **Keeps the things to do.** "Remind me on Tuesday that we need paper towels"
  is a task with a reminder, sent in the chat it was asked in; "one of these
  Saturday mornings" is a task with no invented date. A page lists them, and
  a reminder sent late after the bot was off says when it was due. A task can
  come round again: "bins out every Sunday at 7pm", or "the dentist six months
  after the last visit"; ticking it off records it and keeps it coming, the
  hour holds when the clocks change, and a stretch with the bot off sends one
  late reminder rather than a pile. The tasks page sets and shows it too. A
  birthday or anniversary is a yearly task whose reminder lists the gift ideas
  saved for whoever's it is ("Grandma would love a gardening apron" is kept as
  one), or asks for some when there are none. A task kept for "one of these
  Saturday mornings" is brought up when such a morning comes round and the
  calendar is free for the hour ahead, with a reminder's buttons: each task
  once a week at most, one a day in each chat, and only when its words name
  days or a part of the day plainly ("before Christmas" is left alone). The
  tasks page says when each comes up, and the settings page turns it off. On
  Telegram a reminder comes with ✓ Done, In an hour and Tomorrow buttons, and
  "how was it?" with Yes, again, Not again and Didn't go: a tap is done by code
  with no model call, so it answers at once and works when the model does not,
  and the message then says who did what, for everyone in the chat.
- **Answers /today, /week, /tasks, /now and /lookup on Telegram by itself.** What
  is on today and for the next seven days, the open tasks kept in that chat, and
  what on the list could start right now are answered from the calendar, the
  task list and the suggestion engine at once, with no model call, so they work
  when the model is down or the day's limit is spent; /lookup has the ideas
  waiting looked up now rather than in the evening. They are in Telegram's "/"
  menu, only the family may ask, and each answer is kept in the conversation.
- **Answers "what should we do?" for the time asked about:** right now, tonight,
  Saturday morning or this weekend. A staged engine checks every idea against
  the free time in minutes, the forecast, the opening hours and the travel
  time, says when each option could actually start, searches for what is on,
  and logs every verdict. An outdoor idea is held to the daylight: one that
  only fits after dark is offered as possible, with the reason, and asked about
  today, the reply is told when dark comes.
- **Reads photos.** A poster, a menu, a ticket or a screenshot sent to the bot
  on Telegram is read by the model that looks things up, which writes down
  what it is and every name, date, time, place, price and link in it; that is
  answered as if it had been typed, with the caption after it. The words are
  kept, marked as a photo; the picture is not. An album is one question, up to
  four of its photos read. In a group only a photo sent to the bot is read. About a tenth of a cent a photo, within the daily limit, and
  it can be turned off on the settings page.
- **Feels at home on Telegram.** "typing…" stays up for as long as an answer
  takes, not five seconds. Bold, italics, code and links in a reply are drawn
  as formatting instead of showing as asterisks, and a command's answer has its
  heading in bold. A sticker, a file or a video is answered with the words sent
  with it, or a plain line saying it cannot be read, rather than silence.
  Somebody in the family group who is not on the list is answered only when they
  address the bot, not on every message. Added to a family group, she says hello
  and how to talk to her there. "Answer only when mentioned" is on the settings
  page, which also says whether Telegram lets the bot read a whole group, and
  what to change in BotFather when it does not. Several messages sent one after
  another are answered together, in one reply. What is only for one person (their
  reminder, the note on their idea, how their plan went) goes to their own chat
  with the bot when it began in a group.
- **Knows where the family is when a phone says so.** A location shared on
  Telegram, or the position the web page's chat sends with a message (only
  while "Send where I am" is ticked), is used for three hours: travel is measured from there
  and discovery searches near it. A live location shared on Telegram follows the phone as it
  moves.
- **Speaks as Vera.** A personality, and a description of the family, both
  editable on the settings page. Everything said unasked (reminders, "how was
  it?", notices) is written in her words by code, and is carried by her reply
  instead when the family is already talking to her. Her name is written once
  and said as `{name}` everywhere else, and the chat page shows her replies
  under it. On the Personality page the family can call her by a name of their
  own, rewrite her character, add notes on how she talks, reword any line she
  sends unasked, or choose a shorter Vera that costs fewer tokens a message; she
  changes how things are said, never what is done.
- **Speaks first.** A Thursday digest of the weekend's options, and a "how was
  it?" the morning after a plan. The evening before a plan it checks the forecast
  and the place's hours again, with no model call, and speaks only when one is
  off: rain for an outdoor plan, or the place listed as closed then, with another
  idea for the same time when one fits. The hour, or not at all, is a setting.
- **Runs on OpenAI's GPT-6 Luna by default,** the cheapest capable model of the
  three companies, for chat and lookups alike. Claude and Gemini can be chosen
  per surface on the settings page, with another as a spare when the first is
  rate limited or down, and a mistyped model name is refused when it is saved.
- **Knows each company's models by level,** everyday, better and best: GPT-6
  Luna, Sol and Astra; Claude Haiku 4.5, Sonnet 5 and Opus 5; Gemini 3.1
  Flash-Lite, 3.8 Flash and 3.1 Pro, with what each costs. Every company answers
  with its cheapest unless the family chooses otherwise, and the chat, the
  weekend digest and the lookups each have a level of their own on the settings
  page, which says what each level means and costs on the company answering. A
  message the spare company takes is answered at the same level, a level up
  never answers with a cheaper model than everyday, and a weekend digest that
  fails is retried as the digest: at its level, and quiet if it gives up. A
  model named in `.env` is kept.
- **Stops at a daily spending limit.** Every model call records an estimated
  cost; once the day's limit ($2 unless changed) is used up, nothing more is
  asked of a model until midnight, and the chat says why.
- **Keeps up with the companies' models and prices.** Once a day, with no model
  call, it asks each company with a key which models it may use and reads two
  public price lists, puts a price in force only when the lists bear it out, and
  tells admins what matters: a model in use going away, with the nearest at
  about its price (put in with one press on the Status page, or by itself once
  the old one has gone if it costs no more than twice as much), a price that
  moved, or new models. A company that stops taking part of a request is sent it
  again without that part, and admins are told. Weighing such a change with a
  stronger model, within a monthly budget, is there to switch on and is off
  unless chosen.
- **Tells admins what only they can fix,** on Telegram: a company out of credit
  or refusing its key, the day's limit reached, Google shutting the bot out.
  Each is said again at most every twelve hours while it lasts, forgotten once
  it works again, listed on the Status page, and lights the Status icon amber or
  red. Any message or lookup can be opened from there to see every call it made
  and what each cost.
- **Wish lists for the kids.** Each kid keeps her own lists, everyday and for
  Christmas and her birthday, ranked by her (dragged into order on the page),
  and a parent answers when they choose; "not this time" puts a wish away for
  longer each time it is asked again. Vera sorts what is said into a wish, a
  family idea or both, answers at once at the kid's age, guides how often she
  asks, and sends the parents only what they decided they want: a request a kid
  asks to put to them, and one that is out of line. A kid's birthday wishes come
  with her birthday's reminder. Kids never see each other's lists, and
  presents are never shown to whoever they are for.
- **Pages for the kids.** A kid's Home, things to do, plans and ideas are
  simpler, her conversation with Vera is her own (her parents can read it), and
  the family can set how many messages a day she may send (no limit unless they
  do); a command or a button costs none. Where a kid reads, what the bot says of
  its own workings is said plainly instead: the kids never see how it works or
  why it does not.
- **The whole bot in a browser:** a home page that asks what is on your mind and
  says what is coming up and what is left to set up, the conversation with Vera,
  the ideas and restaurants, the plans as a list or a month read live from
  Google, forms that add and change ideas, record how things went and put plans
  on the calendar (through the same tools the bot uses), the Family page, a
  status page with what is connected and what it has cost, and a settings page.
- **On a phone's home screen.** Added from Safari's Share button, or Chrome's
  menu on Android, the page opens full-screen as an app, with the mark for its
  icon and the page's name under it.
- **Everyone signs in as themselves.** Each person has a password of their own,
  stored hashed, and one of three roles: admin, parent and kid. What each role
  may do is one table, `familydb/roles.py`: a kid signs in, reads the ideas and
  plans, talks to Vera, keeps her wish lists and ticks off her own things to do,
  and changes nothing else. An admin can take somebody off the list for good,
  and the page says what goes with them. An admin gives each person a starting
  password, shown once, which they replace as soon as they sign in with it. The chat speaks
  as whoever is signed in, the settings history says who changed what, and only
  an admin reaches Settings, setup and the Family page. A new starting password
  signs somebody out everywhere, for a lost phone. The shared family password is
  only the way in until the first admin has their own, which ends it.
- **A look of its own.** A modern dark page lit the way an old green screen was:
  phosphor green glows only where attention belongs (the button to press, the box
  being typed in, what is next, what is live), each part of the site and each kind
  of idea has its own colour, a tab bar sits under the thumb on a phone, and a month
  prints as green-bar paper, tractor-feed holes and all. The colours are tuned so
  no two that share a page are easily confused, colour-blind eyes included. Its few
  pictures are 1980s green-screen monitors: what is next on the home page, beside a
  radar of everything coming; the sign-in; the day's spend, which turns amber near
  the limit; the page that is not there; and, on the Ideas page, a radar that is a
  map of where the listed places are from home, following the filters, while each
  card says its own drive and direction. `docs/STYLE.md` says what each choice is
  for.
- **Vera at the centre of the page.** Home opens on the box to answer her
  question, "What’s on your mind?", which is its label: the chat's own box, so a
  question or an instruction typed there lands in the conversation, which the
  page moves into while she answers. The conversation goes by her name, and everything she says,
  a long answer, a reminder or a plain "Done.", is drawn the one way; while she
  thinks, the thread's last line says so and the box waits closed rather than
  lose anything typed. She is never drawn as a person: where she appears there is
  only a small screen full of glyphs nobody can read, between an 80s terminal
  and the Matrix, falling while she thinks. What is coming, what is left to do
  (each ticked off where it stands) and what was added lately sit around the box,
  and opening any page asks nothing of a model. What is being typed is kept
  across a refresh, a change of page or signing in again, until it has been sent.
  A mic beside each box fills it from the browser's own speech recognition: no
  model call, and nothing is sent until the box's own button is pressed.
- **Says what it sends unasked.** The Messages settings page lists each kind of
  message she sends by herself, whether it is on, when it goes, what it costs
  and how often it went, with the latest in full.
- **Set up from that page.** The keys, the models, Telegram (taken up within
  seconds, no restart), Google Calendar (connected from the page, with no laptop
  needed), where home is (found on the map), the timezone and the spending
  limit. The time zone is chosen from a list of the standard zones, each by its
  city and its offset that day. The page can also sign everyone out on every
  device. Somebody new who messages the bot on Telegram, or only presses Start
  on its link, is listed on the Family page with a button to add them, and the
  digest chat is chosen from the chats the bot has seen, so nobody copies an id
  by hand. For somebody already on the list, an admin can make a link instead:
  opened on their phone, pressing Start links their Telegram to them. It works
  once, for a day, and whoever opens it first is taken for that person.
- **Settings in parts.** `/settings` is a card to each part, saying how it
  stands and marking what needs a look: General, AI model, Spending, Messages,
  Lookups, Personality and family, Connections, Sign-in and security, and what
  has changed. Each part is a short page with one Save, a line of help under
  every box, the default each empty box falls back to (in words: "Default
  (Thursday)", an hour as "18:00"), a mark on what was changed here, and the
  fine-tuning folded away. The AI model page chooses the company the way setup
  does, with its key checked for free before it is kept.

### Installing it

[docs/INSTALL.md](docs/INSTALL.md) is three steps, and needs no Linux
knowledge:

1. **Paste one block into the server's terminal.** It makes a key that can
   read this private repository and nothing else, and shows the link and the
   line to give GitHub. It waits, checks that GitHub took the key, and explains
   what to check when it did not. Then it runs `scripts/bootstrap.sh`, which
   lists what it will change on the machine and why, asks once, and installs
   everything. The installer asks only whether there is a domain name.
2. **Open the link it prints**, with the password it prints. Without a domain
   the page is on HTTPS at the server's own address: a real certificate from
   Let's Encrypt where it can get one, which Caddy renews itself, or Caddy's own
   one, which each browser warns about once. The installer opens ports 80 and
   443 in `ufw`, and says plainly when a provider's own firewall is in the way.
3. **Follow the setup on the page.** Seven short steps, each saying why it
   matters and what to do: yourself, a password of your own, an AI model (the
   key is checked with the company, for free, before it is kept), where home
   is, Telegram (the bot recognises your phone from your first message to it),
   the rest of the family, and Google Calendar. Any step can be skipped; the
   home page keeps a list of what is left.

When something fails, the script says what went wrong and what to do, and
that pasting the block again carries on from where it stopped. Nobody edits a
file on the server: each person's password is chosen and changed on the page,
and `maintain.sh password` makes the admin a new one if it is forgotten.

`scripts/uninstall.sh --from-zero` removes everything the install put on a
server, after asking twice, so the install can be tried again from the start.

The code goes in `/opt/familydb`, not a home directory. The service runs as its
own account, which cannot enter a home directory, so a service started from one
would stop at once. The installer checks this and refuses rather than leaving a
unit that will never start.

### Looking after it

- `familydb doctor` checks the whole install and says what is wrong and what to
  do about it. `--online` also tests the keys against the APIs, `--json` is for
  scripts, and `--fix` puts right the few things that can be put right without a
  decision.
- `scripts/maintain.sh` does status, check, backup, restore, upgrade, logs,
  restart and nightly backups. A restore backs up the database it is about to
  replace, so it can itself be undone.
- **The page on a port scans rarely try.** `maintain.sh https --port random`
  (or `WEB_PUBLIC_PORT=random` at install, or in `.env` with Docker) serves the
  page on a port from 20000 to 29999 that none of nmap's thousand usual ports
  and nothing on the machine uses, instead of 443. Port 80 answers only a
  certificate authority's check, with no redirect to give the port away, and
  the firewall rule follows the port. It keeps the page out of the sweeps of the
  usual ports; it is not a lock, and the RUNBOOK says so.
- **FamilyDB's own port moves with one command.** `maintain.sh port 9090` (or
  `random`) moves the port FamilyDB listens on, 8080 unless moved, when
  something else needs it: in `.env`, in Caddy's configuration where it passes
  the page on, and in Docker's mapping, then restarts. With Docker,
  `maintain.sh https --port` moves the Caddy container's port as well. The
  General settings page shows both ports and the commands; neither is a form,
  so a sign-in in the wrong hands cannot move the page.
- `scripts/uninstall.sh` removes the service and the installed files but keeps
  `.env`, `data/` and the backups, which is what a reinstall wants. `--purge`
  removes those too, after taking a backup and asking you to type a
  confirmation.

Every one of these explains a failure rather than printing one: which step, the
command, its exit code, what it said, what that usually means, and what to try.
`RUNBOOK.md` covers running it day to day; `docs/INSTALL.md` has a section on
each failure.

### What has been checked

Every push runs the test suite on Python 3.11 and 3.12, lints and shellchecks
every script, and then, on a real machine: a bootstrap install into `/opt`, the
bot running as the service account it created, `doctor` and its `--fix`, a
backup, a restore over the database, an uninstall that keeps the data followed
by a reinstall that picks it back up, and a purge that backs up first and leaves
nothing. It also starts the service under its systemd sandboxing and fetches
the page, refuses an install from a home directory, and builds the Docker image,
migrates inside the container, serves the page and stops it with a signal.

Signing in through Caddy and through nginx over HTTPS was checked in a real
browser.

What no test covers is a real conversation with a real model, a real Telegram
bot or a real Google account: those need keys, and they are what this alpha is
for. `uv run python -m evals` runs the family's own requests against a real
model and grades what it did, for a few cents; it has not yet been run.
Connecting Google (a service account's key and the calendar's id, pasted into the
page) has not yet been tried against Google itself; `familydb google connect` on the
server does the same and prints Google's answer.

### Known limits

- The suggestion engine has been exercised against fixtures and by hand, not yet
  across a real season of weekends.
- Travel time is a straight-line estimate times a road factor, not real routing,
  and the forecast is per day, not per hour.
- The location a phone shares is named with OpenStreetMap's free reverse lookup,
  which has not yet been reached from a real install.
- One process at a time writes the database. Run one `familydb run`.
- The daily spending limit is an estimate from a price table, not the bill. Set a
  limit on the API key with the company as well.
- The page's site-wide lockout stops distributed password guessing. A browser
  that has signed in before is spared it; a new phone may have to wait fifteen
  minutes while someone is guessing.
- Upgrading on a private repository needs the credential the install used. With
  a deploy key the bootstrap wires it up; with a token there is nothing stored,
  and `maintain.sh upgrade` says so and what to do.
- There is no LICENSE file: all rights reserved by default.

## v0.1.0 — first alpha (2026-09-21)

The first version meant to be installed on a real machine and used by a family.
Everything below has been running against the tests and a scripted install; none
of it has yet been lived with for a month, which is what this alpha is for.

### What it does

- **Captures ideas from chat.** "We should try that ramen place sometime" becomes
  a stored idea, tagged with what the model can infer, through Telegram or the
  console.
- **Fills them in.** A background worker turn looks each new idea up on the web:
  address, opening hours, booking link, price notes, a geocoded travel estimate.
- **Keeps the calendar.** Confirmed plans are created, moved and cancelled on the
  shared Google Calendar from chat, and free time is read back live.
- **Answers "what should we do this weekend?"** A staged engine checks every idea
  against the free time, the forecast, the opening hours and the travel time,
  searches for what is on that weekend, and logs every verdict.
- **Speaks first.** A Thursday digest of the weekend's options, and a "how was
  it?" the morning after a plan.
- **Runs on Claude, OpenAI or Gemini,** chosen per surface, with another as a
  spare when the first is rate limited or down.
- **A web page** behind one shared family password: the ideas, the restaurants,
  the plans, a status page saying what is connected and what the month has cost,
  and a settings page that changes any setting or key without a restart.

### Installing it

Start at [docs/INSTALL.md](docs/INSTALL.md), which goes from a fresh VPS to a
running bot. On the server:

```bash
sudo bash scripts/bootstrap.sh
```

That is the only script that assumes nothing. It installs the system packages,
puts the code in `/opt/familydb`, creates the service account, hands over to
`scripts/install.sh` for the questions, starts the service and checks the
result. Before it touches anything it prints what it will change on the machine
and why, and what it will not touch, and asks.

Getting the code onto a bare server is a step of its own, because the
repository is private: a deploy key, a token in the environment, or a copy you
put there yourself. All three are in the install guide.

Clone into `/opt/familydb` and not a home directory. A home directory is closed
to other users, so a service running as its own account cannot start from one.
The installer checks this and refuses rather than leaving a unit that will
never start.

### Looking after it

- `familydb doctor` checks the whole install and says what is wrong and what to
  do about it. `--online` also tests the keys against the APIs, `--json` is for
  scripts, and `--fix` puts right the few things that can be put right without a
  decision.
- `scripts/maintain.sh` does status, check, backup, restore, upgrade, logs,
  restart and nightly backups. A restore backs up the database it is about to
  replace, so it can itself be undone.
- `scripts/uninstall.sh` removes the service and the installed files but keeps
  `.env`, `data/` and the backups, which is what a reinstall wants. `--purge`
  removes those too, after taking a backup and asking you to type a
  confirmation.

Every one of these explains a failure rather than printing one: which step, the
command, its exit code, what it said, what that usually means, and what to try.
`RUNBOOK.md` covers running it day to day; `docs/INSTALL.md` has a section on
each failure.

### What has been checked

Every push runs the test suite on Python 3.11 and 3.12, lints and shellchecks
every script, and then, on a real machine: a bootstrap install into `/opt`, the
bot running as the service account it created, `doctor` and its `--fix`, a
backup, a restore over the database, an uninstall that keeps the data followed
by a reinstall that picks it back up, and a purge that backs up first and leaves
nothing. It also refuses an install from a home directory, and builds the Docker
image, migrates inside the container, serves the page and stops it with a
signal.

What no test covers is a real conversation with a real model: that needs a key,
and it is what this alpha is for.

### Known limits

- The suggestion engine has been exercised against fixtures and by hand, not yet
  across a real season of weekends.
- Travel time is a straight-line estimate times a road factor, not real routing.
- Ideas and plans can only be changed by messaging the bot; the web page reads.
- One process at a time writes the database. Run one `familydb run`.
- The page's site-wide lockout, which stops distributed password guessing, also
  means a determined stranger can keep the family off the page for fifteen
  minutes at a time. On a public server, that is the trade being made.
- Upgrading on a private repository needs the credential the install used. With
  a deploy key the bootstrap wires it up; with a token there is nothing stored,
  and `maintain.sh upgrade` says so and what to do.
- There is no LICENSE file: all rights reserved by default.
