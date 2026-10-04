# Brief: Today Line, with joy

You are an expert creative graphic and interface designer, known for software with personality:
products people describe as delightful, without them ever getting in the way.

This folder is **Today Line**: the finished FamilyDB design restyled as a calm calendar app (cool
gridded surface, one green meaning "now", events marked with a colour bar and tint, Inter for
headings, dates and times). `DIRECTION-calendar.md` says what it did and why; `STANDARD.md` is its
written standard (read it first); `reference/` has shots of it now. Keep what makes it a calendar.
Your job is to give it a soul.

## What the family said

They liked the move to a calendar look ("that's great"), then: "It still feels a little sterile,
like an AI-designed app. Functional, but plain, with no real soul. The typography is perfect,
fine, good, but uninspired. Can we make it a little more joyous to use?"

So: **keep it a home calendar and house organiser, and give it a soul.** It must not slide back
to what they rejected before (a recipe or gardening site: cream paper, soft serif, forest green
with sun yellow). And it must stop looking like the default every AI produces: cool grey page,
identical white cards, a safe grotesk, one green accent, nothing anybody would remember.

Think of the calendar and planning apps people genuinely love using, the ones with a personality
of their own, and of a real family's fridge and wall planner: the colours each person picked, the
stickers, the countdown to the trip, the satisfaction of crossing things off. Joy comes from
character and from moments, not from decoration. Some places to look (not a checklist; choose,
and do fewer things well):

- **Type with a voice.** Headings, big dates and numbers deserve a face with real character that
  still reads as modern software (not a soft bookish serif). Atkinson Hyperlegible stays for running
  text. A type pairing the family would recognise as FamilyDB's own.
- **Colour with conviction.** The eight people's colours are the family's palette: let them be
  loved, vivid and confident, while staying legible. A page colour and surfaces that feel chosen,
  not default grey.
- **Moments.** The states that deserve a small celebration (a to-do ticked, all done for today,
  a plan Loved, a wish added, nothing late), the countdown to the next plan, today feeling like
  today, the kids' pages feeling like theirs. Use what the pages already have; the states sheets
  (`states*.html`) show most of these.
- **Shape and detail.** Event and idea kinds with their own little marks, date tiles with
  personality, a considered corner and edge language, maybe a subtle texture. Small, CSS-only
  motion where it rewards an action, always off under `prefers-reduced-motion`.

## Rules

- **Keep the pages, their content, their structure and their words.** No new pages or features,
  and nothing a page says or does changes, except that a celebration state may get its look.
- **Keep the brand's facts:** FamilyDB's smiling-monitor mark (recolour it if you like), Vera is
  never drawn (her small screen, `.vs`, stays her sign), red means only late or broken, each
  person keeps their own colour slot, Vera's things stay hers.
- **Fonts:** open-licensed, self-hosted woff2 in `fonts/` (download from Google Fonts or the
  families' GitHub repos; fontTools is installed for subsetting); new font files under 200 KB in
  total. Update `type.html`.
- **Floors that don't move:** measured contrast in both themes (WCAG AA for text, 3:1 for
  controls), 44 px targets on kids' pages, the phone's first screens, no inline `style=""` and no
  scripts, everything readable with scripting off, `prefers-reduced-motion` honoured, emoji never
  used as decoration. Dark mode gets the same care.
- Work only in this folder.

## Deliver

1. The restyled pages, rendered with `DARK="<every page>" ./_kit/render-all.sh .` (every page
   light and dark, desktop and phone, into `shots/`). Look at every shot, fix, render again.
2. `DIRECTION.md` (under 400 words): its name, its idea in one sentence, what makes it joyful
   (type above all), the three moments you would show the family first, and where it is weaker.
3. Update `STANDARD.md`'s colour, type and brand sections to match.

Reply with the name, the one-sentence idea, and anything unfinished.
