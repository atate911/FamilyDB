# Who the family talks to: the persona layer

Design proposal, September 25, 2026. It looks at the persona layer as built (`familydb/personas/`,
`voice.py`, the Personality page), says what is wrong or thin in it, and proposes how it should
be used and configured from here. "Today" is what the code does now; the rest is proposal, and
the open questions at the end are the family's to decide. `docs/AI_CALLS.md` ("Who is speaking")
and `docs/MEMORY.md` are the companions; the token-economy rules in `CLAUDE.md` are the
constraints.

## The one idea

**She changes how things are said, never what is done.** A persona is words: the register the
chat model writes in, and the lines code fills in for what the bot says unasked. It never changes
which tools are declared, what a tool does, what the product spec requires, what is saved, or what
the page lets anybody do. Three rules follow from it:

1. Anything that must hold whoever she is belongs to the product (`prompts/system.md`, or code),
   never to her character, because a family can rewrite or replace her character.
2. Anything she is told that differs from one message to the next goes in the turn, never in her
   character, which sits in the cached prefix.
3. Who she is is chosen deliberately, by an admin, on the page. The chat can never change her,
   for the same reason it can never change the family list: what a setting is, is never the
   model's to decide.

## What it is today

A `Persona` has three parts, and the Personality page holds a fourth thing that is not hers.

| Part | Written in | Where it goes | Who changes it | What it costs |
|---|---|---|---|---|
| Her name | `default/persona.toml` | `{name}` in her character and lines, the page (`assistant`), Telegram's `/start` | nobody, short of a new folder | nothing extra |
| Her character | `default/character.md` | first in the cached chat prefix, for chat, the digest and retries; never the workers | an admin, as a whole rewrite (`persona_text`) | about 2,800 tokens with every call, cached |
| Her lines | `default/lines.toml` | `voice.say`, for the 15 events in `voice.EVENTS` | an admin, one line at a time (`voice_lines`) | nothing: no model call |
| About the family | the Personality page | the family block of the prefix | an admin (`about_family`) | its length, cached |

`persona = none` is `PLAIN`: the bot as itself, called FamilyDB, with no character and the plain
wording for every line. The family's rewrites are meant to be kept under none and come back when
she is chosen again (the module docstring and `ALPHA_READINESS.md` step 12 both say so).

## What is wrong or thin today

1. **Choosing "None" throws the family's rewrite of her away.** Saving the Personality page with
   none chosen writes `persona_text` as empty (`save_personality` only keeps a rewrite when a
   shipped persona is chosen), and under none the page draws the description box empty, so
   choosing her again saves nothing either. Rewrite her, choose none, save, choose Vera, save:
   the stored settings go from `{persona_text: ...}` to `{persona: none}` to `{}`, and she is
   back as she shipped. Her lines survive only because their boxes carry the stored values. This
   is a bug against what the docs promise, and the smallest fix is its own change: under none,
   leave `persona_text` as stored.

2. **"The spec wins" is written only in her character.** `prompt.py` says the spec wins where the
   two meet, "her character says so itself", and it does, in her own last paragraphs ("Your
   personality governs how you communicate; it does not override ... application rules, tool
   permissions, or safety requirements"). `PERSONA_HEADER` and `JOB_HEADER` say nothing of it.
   A family's rewrite that leaves that sentence out leaves the precedence out with it. One
   sentence in `JOB_HEADER` makes it the product's, for every persona, shipped or rewritten, and
   costs a dozen cached tokens.

3. **Keeping it suitable for the kids is her rule, not the product's.** Her character invites
   cheek ("meet innuendo with a light, knowing response") and relies on the next sentence ("with
   children or mixed-age audiences, keep the interaction age-appropriate") to stop it. The spec
   says nothing about children, so a rewrite can keep the cheek and drop the guard. And the model
   is never told who is listening: Telegram's channel knows whether a chat is a group
   (`in_group`), and the page's chat is one thread the whole family shares, but neither fact
   reaches the turn. The family list shows who is a kid; it does not say who can read this chat.

4. **Her character is written for an assistant in general, not for this job.** It speaks of "the
   user", of artifacts, formal letters and reports, of verifying cultural facts; the family's
   chat is several people, kids among them, mostly capturing ideas, setting reminders and asking
   what to do. At 11,251 characters it is larger than the product spec it sits in front of
   (7,965). Some of it pulls against the spec: "Ask questions that move the conversation
   forward" and "follow an interesting tangent" against "Let people correct you rather than
   interrogating them" and "Short replies"; "Use lists, tables, and headings" against "No bullet
   walls". The spec wins, but the model reads both on every call.

   The case for shortening her is attention, not money, on the default model. At GPT-6 Luna's
   prices her 2,800 tokens cost about $0.00003 a call from the cache. On Claude Opus 5 they cost
   about $0.0014 a call from the cache and $0.028 each time the cache is written again, which is
   the first message after an hour's quiet (`ANTHROPIC_CACHE_TTL=1h`, the default). What a long,
   general character costs on a small model is adherence to the spec, and that is a number the
   evals can give (item 7).

5. **Her name cannot be changed from the page.** Naming the family's assistant is likely the
   first thing a family wants to make its own, the kids especially. Today it takes a new folder.
   Typing "You are Juno" into her description gives a bot that calls itself Juno in chat while
   the page, `/start` and every line still say Vera.

6. **A rewrite is a fork.** Once her description is rewritten, the family owns all 11,251
   characters of it and never gets a later improvement to hers, and nothing tells them hers has
   changed. Most families want to add a sentence ("no emoji", "Mia likes to be called Captain"),
   not to take over a page of prose to do it.

7. **Nothing measures her.** The evals run with Vera as she ships. Nothing compares her with
   none, in pass rate or in tokens, or catches a rewrite that breaks a behaviour the evals hold.

8. **Her rewrite and her lines are not hers alone.** `persona_text` and `voice_lines` are one
   value each, laid over whichever persona is chosen. With one persona that is harmless; with a
   second, a rewrite of Vera would be laid over somebody else.

9. **"She" is written into the page.** "Who she is", "Her description", "What she says unasked",
   "Restore her original description", and `docs/STYLE.md`'s "Her screen". A persona who is not
   a she would need the page's wording to follow the persona. That is a decision before it is a
   change (the open questions below).

## Where she can be used

From most to least worthwhile. Each keeps to the rules above.

- **Chat replies** (today). The one place she costs tokens, and the one where she matters most.
- **What she says unasked** (today). Worth more than it looks: a family reads a reminder or a
  "how was it?" far more often than they read a long answer. Two cheap improvements below:
  several wordings of one line, and a preview.
- **The digest** (today, as a chat turn).
- **Telegram's own contact.** The bot's name and description in Telegram are set by hand in
  BotFather; setup's Telegram step tells the admin to call it by her name, and after that
  nothing keeps the two together. Telegram's Bot API can set them (`setMyName`,
  `setMyDescription`, `setMyShortDescription`), so the supervisor could make the contact her
  name, and follow a rename, with no model call and no trip to BotFather. It would run when the
  persona or her name changes, never on a timer.
- **Meeting her.** Setup ends without saying who she is. A line on the last setup page ("She is
  called Vera; you can rename her, or choose none, under Personality") is enough. It is not a
  setup step: the bot is usable without it.
- **Memory, when it lands.** Two things change then. Her character says "do not ... imply access
  to memories you do not have", which becomes half wrong once she has some. And a style
  preference somebody states in passing ("Sam likes it short", "no emoji for Mia") is a memory,
  selected into the turn for the people it concerns, not a setting and not a rewrite of her. The
  boundary: settings are what an admin chose deliberately, in the cached prefix; memories are
  what the family said in passing, in selected context.

Where she never goes: the lookup and discovery workers, whose prose nobody reads; tool
descriptions and tool results; memory deltas and anything else code reads; the page's own words
(`views.py`), which are the page's, not hers; and any model call made just to word a line.

## How she should be configured

In layers, from least effort for the family to most. Each is written once, rendered by code, and
changes the cached prefix only when somebody saves it.

1. **Which persona** (today): a shipped folder, or none.

2. **Her name** (new): a short `persona_name` setting, empty for hers, laid over her in
   `personas.active` like the rest. Everything that already asks `active(settings).name` follows
   with no other change: the prompt, her lines, the page, `/start`, and the Telegram contact if
   it is synced. One line, a few words, no braces. Under none the bot stays FamilyDB: a name
   belongs to a persona.

3. **Anything to add** (new): a short box, a thousand characters or so, of the family's own
   notes on how she talks, put after her character in the prefix. It survives a change to hers,
   because it is not a copy of her. It is the first thing to offer a family who wants her a bit
   different, and the rewrite stays for the few who want her very different.

4. **A full rewrite** (today, improved): as now, but remembering which of her it was written
   from (a short digest of her character at the time), so the page can say "Vera's own
   description has changed since you rewrote her" and show the difference. Once a second persona
   ships, the rewrite and the lines are kept per persona, so each comes back with the one it was
   written for.

5. **Her lines** (today, improved):
   - A line may have several wordings: a list in `lines.toml`, one per row in the page's box.
     Code picks one from the message's own id, so a retry or a resend says the same words, and a
     daily reminder does not read the same every day. No model call.
   - Each box shows the line filled in with example facts, by the same `voice.say`, so the family
     sees "Reminder: bins out (for Sam). Task #12; ..." rather than `{title}{who}`.

6. **Who is listening** (new, and not a setting): one line in the turn, from facts code already
   has, such as "In the family group; kids can read it" or "A direct message with Sam". It goes
   next to the date line, is a few tokens, and lets any persona choose its register without the
   character having to guess. The product's rule that everything said where a kid can read it
   stays suitable for them goes in the spec, where no rewrite reaches it.

Dials ("how much she says", "humour", "emoji"), each position one fixed sentence, are tempting:
deterministic, cheap, testable. They are not proposed yet. The spec's own style lines ("Short
replies. One emoji at most.") would have to move into the persona layer for a dial to loosen
them, and then none would need a short character of its own. If families keep writing the same
notes in "Anything to add", those notes are the dials to make.

**Not configurable, on purpose:** what she does (the spec's); a persona per person or per chat,
which would mean more than one cached prefix and more than one Vera; changing her from the chat;
a model call to word a line; a picture of her (`docs/STYLE.md`).

## What a persona folder must pass

Adding a persona is adding a folder, so what a folder must be is written down and tested:

- `persona.toml` names her; `character.md` says `{name}` and never her name; every line in
  `lines.toml` can be filled in. (Tested today.)
- Her character is about how she talks. It says nothing about tools, dates, data or what to save,
  and does not need to say that the spec wins, because the product says it.
- The request built under her differs from the one under none only in the persona section: the
  same tools, the same spec, the same family block and idea list. (A new test.)
- She passes the evals at least as well as none does, and what she adds in tokens is known.

## Measuring her

- `python -m evals --persona default|none|<file>`, reporting pass rate and input tokens per case,
  so her cost and her effect are numbers rather than impressions.
- Checks graded by code, as the evals already are, never by a second model: at most one emoji;
  replies within each case's length; no "As an AI" filler; after a rename, "what's your name?"
  gets the new one.
- A case with a kid writing in the family group, graded on what code can see (length, no tool
  that was not wanted), so a change to her or to the audience line is held to it.

Run them before and after any change to her character, a line or the audience line, and keep a
change only if they hold, as `CLAUDE.md` asks of any prompt change.

## Suggested order

One concern per pull request, smallest first:

1. Choosing none keeps the family's rewrite (a bug, item 1).
2. The spec wins, and stays suitable for kids, as the product's rules; the audience line in the
   turn. With an eval case, run before and after.
3. `--persona` in the evals and the voice checks; measure Vera against none.
4. Her name on the Personality page.
5. "Anything to add", and a rewrite that remembers what it was written from.
6. Her character fitted to this job, only if step 3 says it is worth it: either Vera shortened,
   or a second, shorter persona shipped beside her so nothing of the first is lost.
7. Several wordings for a line, and previews on the page.
8. Telegram's contact following her name.

Later, and only with a reason: dials, pronouns, more personas.

## Open questions for the family

- **Is every persona a she?** If yes, it is a product decision and the page's wording stays. If
  not, `persona.toml` gains pronouns and the page's wording of her goes through the persona.
- **Should Vera be fitted to this job, or kept as first written?** Shortening her changes who she
  is; shipping a shorter persona beside her keeps both, and the evals can say which the family
  should meet by default.
- **Can the plain bot have a name?** Proposed: no, a name belongs to a persona.
- **Should kids ever change her?** The Personality page is an admin's today, and stays so under
  this proposal; renaming her is the one thing a kid is likely to ask for.
