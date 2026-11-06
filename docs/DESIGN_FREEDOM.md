# Design freedom: what is open, what is protected

The owner's decision, 5 November 2026. This governs every choice about how FamilyDB is presented
and how a person moves through it, on the page and in Telegram. Where another document (`CLAUDE.md`,
`docs/DESIGN.md`, `docs/INTERFACE.md`, `docs/STYLE.md`, `docs/CONCEPT.md`, the mockups, the guide)
reads as fixing a layout, a name, a look or an interaction, this document wins: that passage records
what was chosen and why, and does not bind the next design.

## Why

The family finds the app complicated and hard to learn, and the documents that describe today's
page had come to read as rules against changing it: "the box first, always", "the edges are
fixed", "Now is the model", a font named as required. Those were good choices for October 2026
and remain good reasons to weigh. They were never meant to stop the app from getting simpler or
better, and they must not. What has to hold is a short list of outcomes, below; everything else is
open.

## What is open

Decide these on their merits, for how the app looks and feels to the family, without asking
permission because an older document chose differently:

- **Navigation and structure.** How many destinations there are, what they are called, what each
  holds, what moves to a secondary menu, whether Now exists in its current form, the rail, the row,
  tabs, the board, the frames for phone, big screen and tablet. Old addresses should keep working
  or redirect, so links in messages and on home screens do not break.
- **The assistant's place.** Whether the box is on every page, where it sits, whether it is a
  composer or a button that opens a panel, the Chat page, the thread column, pins, the ways to
  start. Natural-language capture stays possible; how it is offered is open.
- **What leads a screen.** Its primary action, what is folded away, how many picks show, how
  questions are grouped, what an empty screen offers.
- **Flows.** Connecting steps that today take several pages ("make this tonight": the night, the
  servings, the list, an optional plan), as long as each step is a tool call (below) and the
  result says what was done.
- **Look.** Type, colour, the looks and how far a look may go beyond colour, spacing, marks, icons,
  motion, how Vera appears (today her screen of glyphs).
- **Words.** Names, labels, headings, confirmations, empty states, examples, her lines.
- **How it is built.** Templates, CSS, scripts within the content policy, view-models, which
  module draws what. The layering, `answers.answer` and `web/views.py` for shared wording are
  defaults (`CLAUDE.md`): follow them unless a better structure serves the change, and say why.

A design choice here is reversible and cheap to try. Prototype in the example household
(`uv run python -m examples`, static pages anybody can click through) before a large change, when
the change is large enough that seeing it first would help.

## What is protected

These are outcomes, not mechanisms: the code that keeps one may be redesigned as long as a test
still holds the outcome. Changing an outcome is proposed to the owner (an invariant) or asked of
the family (one of their decisions), as `CLAUDE.md` says, with what it costs and gains.

- **Privacy and what leaves the house.** What is sent to a model, a search, a push service or
  anyone outside, as decided (`docs/DESIGN.md` sections 10, 13 and 16). A push says "she has a
  message", never the words. Dictation goes browser to its maker, never through FamilyDB. A
  position is sent only while somebody ticks to send it.
- **Who may see and do what.** Roles and their permissions (`base/roles.py`, asked as
  `visitor().may`), kids never shown costs, models, setup or how the bot works (`voice.PLAIN`,
  `tests/test_kids_plain.py`), presents kept from whom they are for (`presents.py`), a kid's daily
  messages. A new layout reads the same permissions; moving a page never widens who reaches it.
- **Security.** The content policy (`script-src 'self'`, no inline script or style), escaping of
  anything from an idea, place or fetched page, CSRF and the Origin check on every form, once-only
  forms where a repeat would do harm, API keys write-only, sign-in as oneself.
- **A form is a tool call.** The page changes things only through the code that owns the change
  (`CLAUDE.md`, the web invariant held by `tests/test_web.py`). A new flow that does three things
  calls three tools; it never writes round them.
- **Accessibility.** Measured contrast in every look, labels a screen reader can use, keyboard
  reach, sizes a thumb can hit, and reading, every form and sending a message working with
  scripting off.
- **Cost.** No page view is a model call (`test_browsing_asks_nothing_of_a_model`); every model
  call goes through `gateway` and the day's limit; nothing volatile in the cached prompt. A design
  that would add model calls (a "help me choose" that asks the model) says what it costs.
- **Nothing lost or done twice.** A reply stored before it is sent, leases on messages, undo that
  takes back only what it names, a repeated click or a revisited flow making nothing twice.
- **Truthful status.** What the page says happened is what happened: a confirmation names what was
  saved, planned, put on the list or done, and what did not go through; a fact the app could not
  check (no calendar, no forecast, stale hours) is not shown as checked.
- **The family's decisions** (`docs/DESIGN.md` section 16, rows marked Family). The outcome each
  protects holds; where a row describes presentation ("a count on Chat"), the outcome (people who
  use only the page are told she replied) is what holds, and how it is shown is open.

`docs/STYLE.md` "What does not move" lists the page's share of these.

## Older documents

`docs/INTERFACE.md`, `docs/STYLE.md`, `docs/CONCEPT.md` and `docs/concept-mockups/` record what was
built and why. Read them for the reasons, and keep them true: after a redesign, change them to
describe what is built, in the same change. They are not a specification a new design must match.

The family's answers in `docs/INTERFACE.md` section 12 (phones first, Telegram for quick
instructions, admin on a computer, kids on a tablet and mostly asking for things, an improvised
daily plan, Vera as the front door for instructions) are evidence about this family. Weigh them
like any evidence; they describe how the family lives, not where a box goes.

The reviews of 5 November 2026 (four destinations, an "Ask Vera" button in place of the box, one
pick and two alternatives) are proposals too. Take what serves the family; none of it is the new
rulebook.

## Tests that hold presentation

Many tests pin today's markup: an element's order, a heading's words, a class. When a change means
to move what they pin, change them in the same change, with the reason in the commit. Keep, and
carry over to the new design, every test that holds a protected outcome: permissions, kids'
screens, presents, the content policy, CSRF and once-only forms, writes through tools, no model
call for a page view, truthful receipts. When it is unclear which a test is, read what it asserts:
if failing it would mean a person sees, pays for, loses or is told something they should not,
it holds an outcome.

## How to work

- Do the task asked: critique when asked to critique, prototype when asked for a prototype, build
  when asked to build. Within it, use judgement about layout, navigation, look, the assistant's
  place and the code behind them.
- Explain a material design decision in a sentence or two in the commit or the PR, and what it
  gave up. No special line or form is required.
- Check the journeys a change touches, end to end, in a real browser at phone and desktop width:
  deciding dinner, finding something to do and planning it, saving an idea, adding and finishing a
  to-do, seeing what is next and who acts. Rebuild the example household and look at it.
- Ask only when a protected outcome, or the scope of the task, would change, and the session has
  not already settled it.
