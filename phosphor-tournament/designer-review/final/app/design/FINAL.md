# Make Kitchen Table final

Your Kitchen Table design has been chosen as the look for FamilyDB. Three blind judges compared it
with nineteen other designs and marked it 8, 8 and 9, the strongest of the set. Then thirteen
specialist reviewers looked at it alone, each through one lens, and all thirteen said it should be
optimised before it is built. Their reviews are in `reviews/` (one file per lens), and
`reviews/SYNTHESIS.md` merges them, lists what to protect, groups the fixes, and records the
decisions already taken. Read the synthesis first, then every review: they are specific (values,
wording, CSS), and most of what they ask for is right.

Your job now is to turn this into the final design: the one that gets built. It is still a set of
standalone HTML pages and one stylesheet, but it should be ready to hand to an engineer: every
page an engineer needs drawn, every state decided, the system written down. Keep what the reviews
say to protect. Where a review is wrong for the family or contradicts another, decide, and say why
in `CHANGES.md`.

## Facts about the real app that the design must fit

These came out after you drew the first version. They are how the app works, not taste.

- **Each person signs in as themselves**, with their own password, and the chat and every form act
  as whoever is signed in. Only on a brand-new install, before the first admin has chosen their own
  password, does the family share one password; then, and only then, the page must ask who is
  writing, with no default. So the normal composer says "Writing as Sam · Not you? Sign out", and a
  kid can never write as a parent.
- **Three roles.** An *admin* (Sam) can do everything, and only an admin sees Settings, setup and
  the Family page. A *parent* (Alex) chats, changes ideas, plans and to-dos, sees everyone's to-dos,
  and decides on the kids' wishes. A *kid* (Maya 11, Theo 9) signs in, chats with Vera, keeps their
  own ranked wish list, and sees only their own to-dos; the family sets how many messages a kid may
  send a day. Kids never see cost, models, setup, or how the app works or why it doesn't.
- **Presents are never shown where a kid reads.** Gift ideas and gift to-dos ("Buy Maya's birthday
  present", "Lego set for Theo") are left out of a kid's pages entirely: no greyed row, no count.
- **Vera is not drawn.** Her name comes from the persona in force, and the family may rename her or
  switch the persona off (then the page speaks as FamilyDB). The project has decided she is felt,
  not shown: no face, figure or picture. Her presence is her name, her words and a small mark (her
  initial in her green). Do not take up the style review's request for a character.
- **Reminders go by Telegram.** While Telegram isn't connected nobody receives one, so the design
  must not offer them as if they work.
- **Lookups** (hours, prices, drive times from the web) can be switched off in Settings; then new
  ideas are not looked up, and every page must say the same thing about it.
- **The daily spending limit**: when it is reached Vera stops until midnight and says so in the chat.
- **While Vera is answering**, the chat page refreshes itself (only while a reply is pending) and
  the box is closed until she has answered; with scripting on, it checks quietly instead.
- **How the page is built**: server-rendered HTML, one stylesheet, one SVG icon sprite (`<use>`),
  fonts served from the app itself, **no inline `style=""` attributes and no inline scripts** (a
  content security policy refuses both). Reading, every form and sending a message work with
  scripting off. A few small scripts from the page's own files may enhance: one keeps an unsent
  message and fills the box from the starters; one shares the phone's position with a message
  while "Send where I am" is ticked (so that box only appears when scripting is on).

## Decisions already taken (from the synthesis)

- Vera stays undrawn (above).
- Numbers (times, prices, counts, calendar day numbers) in Fraunces lining tabular figures, words in
  Atkinson Hyperlegible. Codes and keys may keep the slashed zero.
- Saturated colour is for people (and Vera's green). Kinds of idea go neutral, told apart by icon
  and word. Calendar events take the colour of who they are for; "Everyone" is neutral. Red only
  for late text and broken things.
- Twelve-hour clock in the mockup (a family in Washington State); the standard says times follow
  the family's clock setting.
- Settings stays admin-only; its line says who can change it and how to add another admin.

## Worth borrowing (named by the blind judges who saw all twenty designs)

Optional; take what fits Kitchen Table and leave the rest.

- On the next-plan card: when to leave ("Leave by 12:30") and a small "in 1 day" countdown.
- In the summary sentence under the greeting: link the key phrases (the plan, the late to-dos).
- A one-line "How did Silver Falls go?" with the three faces on Home while a plan waits to be rated.
- The person's colour on their chat bubbles as well as their avatar.
- Ideas sortable by "Nearest" as well as "Newest".
- A single key for the colour language, once, for the whole app.

## Three stages

Do **stage 1 now**, then stop and reply. Stages 2 and 3 will be asked for next, so build the
system with them in mind.

### Stage 1: the system and the seven pages

1. Rebuild `style.css` on real scales and named components, as the system, type and accessibility
   reviews describe: radius, spacing and type scales; a 14 px floor (13 px only for tab labels and
   one overline style); one item row, one to-do row (with a compact variant for Home), one banner
   with four tones, one composer, one state-tag vocabulary, two icon-tile sizes and three avatar
   sizes; the contrast fixes (`--ink-3` #596263, field and tick edges #8A806C); a visible skip
   link; no inline styles anywhere; fonts self-hosted as WOFF2 in `fonts/` (download them; Latin
   subset is enough) with `@font-face` and `font-display: swap`; icons in one `icons.svg` sprite.
   Add dark-mode tokens under `prefers-color-scheme: dark` (a warm night version of the same
   palette, not a different design) and `forced-colors` borders where selection is shown by
   background alone.
2. Redraw the seven pages as Sam (admin) signed in as themselves, desktop and phone, applying the
   fixes: the phone as its own layout (fixed bottom tab bar with Home, Chat, Plans, To do, More for
   a parent; the list people came for inside the first screen; tools and filters in `<details>`;
   Plans opening on the list on phones with the grid's day cells as labelled links; Settings rows
   and the Status table re-laid; ideas as compact rows; the chat box pinned with the latest 30
   messages and an "Earlier messages" link); the chips (only a complete question sends; stems fill
   the box through a link that works with scripting off); reminders truthful; Status leading with
   money in words and the model table folded away; one health state per area shown the same way on
   Status, Settings, Ideas and the header pill; one word per thing (use the copy review's table);
   the privacy line about the kids' chats on every width; gift items marked as surprises in the
   parents' views.
3. Render everything with `DARK="home chat todo" ./_kit/render-all.sh .` and look at every shot,
   desktop and phone, light and dark. Fix what's wrong and render again; at least two rounds.
   Nothing may scroll sideways at 390 px. Use real contrast numbers where you can.
4. Write `CHANGES.md`: each fix in the synthesis, what you did, and anything you declined and why.

### Stage 2 (later): the pages that were missing

The kid's Home, Chat and To do as Maya; Wishes for a kid (add, rank with up and down buttons that
are small forms, the parents' answers in words) and for a parent (deciding); the phone More page;
sign-in on a shared laptop (pick who you are, then a password; paste and show-password allowed);
the friendly "this part is for grown-ups" page a kid sees if they open Settings.

### Stage 3 (later): every state, and the standard

A states sheet (limit reached, Vera can't answer, a message pending and failed, after-action flash
with Undo, form errors, the first empty day, no results, a busy calendar day, long titles), dark
mode checked on every page, and `STANDARD.md`: the tokens, every component with its variants, the
word table, the phone rules, the states, and notes for the engineer.

## Rules for working

Work only in this folder. Do not read anything outside it. The original version is kept elsewhere,
so change these files in place. When stage 1 is done, reply with a short summary: what changed most,
what you declined, and anything unfinished.
