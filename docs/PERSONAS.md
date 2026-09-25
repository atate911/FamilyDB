# Who the family talks to: the persona layer

The design of the persona layer as built, September 25, 2026: `familydb/personas/`, `voice.py`,
the Personality page, the audience line in the turn and the bot's Telegram contact. It began as
a proposal (commit dd8a6e8) that found nine things wrong or thin; "What was fixed" says what now
holds for each, "Decisions" answers the questions it left to the family, and "What is left" is
the rest. `docs/AI_CALLS.md` ("Who is speaking") and `docs/MEMORY.md` are the companions; the
token-economy rules in `CLAUDE.md` are the constraints.

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

## What it is

A `Persona` is her name, her label, her character and her lines, one folder each in
`familydb/personas/`. Two ship, and both are Vera: `default/`, Vera as first written, whom the
family meet unless they choose another, and `brief/`, a shorter Vera fitted to a family's chat.
Her label says which of her each is where they are listed together ("{name}, as first written",
"{name}, in brief"). `personas.active(settings)` is the one in force, with what the family wrote
on the Personality page laid over her.

| Part | Written in | Where it goes | Who changes it | What it costs |
|---|---|---|---|---|
| Her name, as the family call her | `persona.toml`, with `persona_name` over it | `{name}` in her character, their notes and every line; the page (`assistant`); Telegram's `/start` and the bot's contact | an admin: one line, at most 40 characters, no braces; empty is her own | nothing extra |
| Her character | `<key>/character.md` | first in the cached chat prefix, for chat, the digest and retries; never the workers | nobody on the page: a rewrite takes its place | Vera as first written about 2,800 tokens with every call, in brief about 740, cached |
| Their rewrite of her, per persona | `persona_text`, by persona key: the text, and hers as it shipped when they wrote it (`of`) | in place of that persona's character, and nobody else's | an admin, for the persona in force | its length, cached |
| Their notes | `persona_notes` | after her character, under a header of their own, before the job | an admin, at most 1,000 characters | their length, cached |
| Her lines and their wordings | `<key>/lines.toml`, where a line may be a list of wordings, with `voice_lines` over them | `voice.say`, for the 15 events in `voice.EVENTS` | an admin, one line at a time, one wording to a row | nothing: no model call |
| Who is listening | code (`render_audience_line`) | one line in the turn, between the date and the message, in a shared chat only | nobody: read from the chat and the family list | a few tokens, uncached, in a shared chat only |
| The Telegram contact | the Telegram supervisor | the bot's name and description in Telegram: her name and her `start` line, or FamilyDB's under none | follows whoever is speaking | nothing: no model call |
| About the family | the Personality page | the family block of the prefix | an admin (`about_family`) | its length, cached |

Under a persona the prefix begins "# Who you are", then her character or their rewrite of her,
then their notes under "## The family's own notes on how you talk", then "# The job", whose first
sentence is "Where who you are and the job disagree, the job wins.", then the product spec. The
request built under any persona differs from the one under none only in that part.

`persona = none` is `PLAIN`: the bot as itself, called FamilyDB, with no character, neither
header and the plain wording for every line. Their name for her, their rewrites, their notes and
their lines are kept under none, unused, and come back when a persona is chosen again. Their
name for her, their notes and their lines are theirs whoever she is; a rewrite is a copy of one
persona's character and belongs to her alone.

A line may have several wordings, kept as a list, and she picks one each time. Code chooses, not
chance: a CRC-32 of the event and a seed (the id of the message a notice answers, or the
Telegram update for a stranger and for `/start`), or with no seed of the facts the line is
filled in with. The same message always says the same words, after a resend, a retry or a
restart, and the next may say it another way. A reminder is seeded by the task and the reminder
in force, so each time a task comes due (after a snooze, say) it may take another wording, and a
reminder worded again for the same time (its title changed) takes the same one. A line kept as a string is one wording, line breaks and all, as every line was before
there could be several, so a line the family saved then still says all of itself; saved again
unchanged from the page it stays so.

The audience line says "This is the family's group chat: everyone in it reads your reply" in a
Telegram group and "This is the family's conversation on the page: everyone who signs in reads
it" in the page's chat, each ending ", kids among them" when the family list has an active kid.
A private chat gets no line. Code cannot see who is in a group, so the kids are read from the
family list. The spec's "Who is listening" says what to do with it, whoever she is.

The Telegram supervisor gives the bot's contact the name it goes by, and its `start` line as
the description: hers, or under none FamilyDB's, as everywhere else the plain bot speaks. It does
so once after each connect, and again when either changes on the page. It asks Telegram what the contact says and sets only what differs, cut to Telegram's
limits. A wait Telegram asks for is waited out, and Telegram out of reach is tried again shortly;
a refusal, or any other failure, is logged and not tried again until her words change or the bot
reconnects, and never stops the channel. A name typed in BotFather lasts until then: the name the
bot goes by is hers, chosen on the Personality page; under none it is FamilyDB.

## What was fixed

1. **Choosing none threw the family's rewrite away.** Under none no description box is drawn and
   every rewrite is left as stored, so choosing her again brings it back.
2. **"The spec wins" was written only in her character.** `JOB_HEADER` says it for every persona,
   so a rewrite that leaves it out still gets it.
3. **Keeping it suitable for kids was her rule, not the product's.** The spec's "Who is
   listening" says it whoever she is told she is, and the audience line tells the model when a
   chat is shared and whether kids read it.
4. **Her character was written for an assistant in general.** A shorter Vera, `brief/` (2,958
   characters against 11,250), ships beside her, fitted to a family's chat; Vera as first written
   is unchanged and still the default.
5. **Her name could not be changed from the page.** `persona_name` is her name wherever `{name}`
   is written: the chat, her lines, the page, `/start` and the Telegram contact.
6. **A rewrite was a fork.** "Anything to add" holds the family's own notes, which last when hers
   changes, and a rewrite remembers hers as it was, so the page says when hers has changed and
   shows how.
7. **Nothing measured her.** `python -m evals --persona` compares personas in runs passed, input
   tokens and cost, and every reply is held to one emoji, no "as an AI" filler and at most two
   exclamation marks.
8. **Her rewrite and her lines were not hers alone.** A rewrite is kept per persona and laid over
   her alone. Their lines stay one set, theirs whoever she is, like their name for her and their
   notes.
9. **"She" was written into the page.** Every persona is a she, by decision, so the page's wording
   of her stands.

## Where she can be used

From most to least worthwhile. Each keeps to the rules above.

- **Chat replies.** The one place she costs tokens, and the one where she matters most.
- **What she says unasked.** Worth more than it looks: a family reads a reminder or a "how was
  it?" far more often than they read a long answer. A line may have several wordings, and the
  Personality page shows how each reads.
- **The digest**, as a chat turn, with the audience line when it goes to the family group.
- **Telegram's own contact.** Her name and her `start` line (FamilyDB's under none), set by the
  supervisor through the Bot API with no model call and no trip to BotFather. Telegram is asked after a connect or a change
  to either, never on a timer.
- **Meeting her.** The page that ends setup says who answers and that her name, how she talks or
  none at all are chosen under Personality, and setup's Telegram step says her name will do for
  the bot (FamilyDB under none). It is not a setup step: the bot is usable without it.
- **Memory, when it lands.** Two things change then. Her character says "do not ... imply access
  to memories you do not have", which becomes half wrong once she has some. And a style
  preference somebody states in passing ("Sam likes it short", "no emoji for Mia") is a memory,
  selected into the turn for the people it concerns, not a setting and not a rewrite of her. The
  boundary: settings are what an admin chose deliberately, in the cached prefix; memories are
  what the family said in passing, in selected context.

Where she never goes: the lookup and discovery workers, whose prose nobody reads; tool
descriptions and tool results; memory deltas and anything else code reads; the page's own words
(`views.py`), which are the page's, not hers; and any model call made just to word a line.

## How she is configured

In layers, from least effort for the family to most. Each is written once, rendered by code, and
changes the cached prefix only when somebody saves it.

1. **Which persona**: Vera as first written, Vera in brief, or none. The list shows each by her
   label, with roughly what she would add to every message as she would be if chosen, the
   family's name for her, their rewrite of her and their notes included.

2. **Her name**: `persona_name`, empty for hers, laid over her in `personas.active`. Everything
   that asks `active(settings).name` follows with no other change: the prompt, her lines, the
   page, `/start` and the Telegram contact. One line, at most 40 characters, and no braces, since
   a `{name}` in it would be filled in again. Under none the bot stays FamilyDB: a name belongs to
   a persona.

3. **Anything to add**: `persona_notes`, a few sentences of the family's own on how she talks, at
   most 1,000 characters, after her character in the prefix. They survive a change to hers,
   because they are not a copy of her. It is the first thing to offer a family who want her a bit
   different; the rewrite stays for the few who want her very different.

4. **A full rewrite**: kept per persona, with her own character as it shipped when they wrote it.
   The box describes the persona in force and saving writes to her alone, never to a persona
   chosen in the same save. When hers has changed since, the page says so above their rewrite and
   offers, folded away, a line diff of hers then against hers now, each line marked + or - as
   well as coloured. Saving a changed rewrite takes hers as it is now, which ends the notice.
   Restoring drops that persona's rewrite and nobody else's.

5. **Her lines**:
   - A line may have several wordings: a list in `lines.toml`, one per row in the page's box.
     Code chooses one from the message's own id (for a reminder, the reminder in force), or from
     the facts when there is none, so a retry or a resend says the same words, and a reminder
     snoozed and due again may say it another way. No model call.
   - Under each box, how the line in force reads: every wording filled in with example facts by
     the same code as `voice.say`, so the family see "Reminder: bins out (Sam). Task #12; ..."
     rather than `{title}{who}`.

6. **Who is listening** (not a setting): the audience line in the turn, from facts code already
   has, next to the date line. It is a few tokens, and lets any persona choose its register
   without the character having to guess. The rule that everything said where a kid can read it
   stays suitable for them is in the spec, where no rewrite reaches it.

**Not built, and why.** Dials ("how much she says", "humour", "emoji"), each position one fixed
sentence, are tempting: deterministic, cheap, testable. The spec's own style lines ("Short
replies. One emoji at most.") would have to move into the persona layer for a dial to loosen
them, and then none would need a short character of its own. If families keep writing the same
notes in "Anything to add", those notes are the dials to make. More personas wait for a reason:
each is a folder to keep and must earn her place in the evals, which have not yet measured the
two that ship. Pronouns wait for a persona who is not a she, and every persona is a she.

**Not configurable, on purpose:** what she does (the spec's); a persona per person or per chat,
which would mean more than one cached prefix and more than one Vera; changing her from the chat;
a model call to word a line; a picture of her (`docs/STYLE.md`).

## What a persona folder must pass

Adding a persona is adding a folder, so what a folder must be is written down and tested:

- `persona.toml` names her, and may give her a label with no brace in it but `{name}`;
  `character.md` says `{name}` and never her name; every wording of every line in `lines.toml`
  can be filled in. (Tested.)
- Her character is about how she talks. It names no tool (tested), says nothing about dates,
  data or what to save, and does not need to say that the job wins, because the product says it.
- The request built under her differs from the one under none only in the persona section: the
  same tools, the same spec, the same family block, idea list and conversation. (Tested, for
  every folder.)
- She passes the evals at least as well as none does, and what she adds in tokens is known.
  (Measured against a real model, by hand: "What is left".)

## Measuring her

- `python -m evals --persona KEY|none|FILE`, repeated to compare: every case runs under each in
  turn from one budget, and the summary and `--json` give each persona her runs passed, input
  tokens (new, written to the cache and read from it) and estimated cost. A file is used as a
  rewrite of the default persona, held to the Personality page's limit.
- Checks graded by code, never by a second model, on every reply whoever she is: at most one
  emoji, no "as an AI" filler, at most two exclamation marks, within the length every reply is
  held to.
- Cases for who is listening and who she is: a kid asking in the family group, graded on what
  code can see (suggestions for tomorrow, nothing saved, a reply short enough for a group); the
  same sensitive reminder asked for in the group, where she asks first, and in private, where it
  is set at once; and "what's your name?" after a rename, which gets the new one, or FamilyDB
  under none.

Run them before and after any change to her character, a line or the audience line, and keep a
change only if they hold, as `CLAUDE.md` asks of any prompt change.

## Decisions

- **Is every persona a she?** Yes, as a product decision. The page's wording of her stays, and
  `persona.toml` has no pronouns.
- **Should Vera be fitted to this job, or kept as first written?** Kept as first written, and the
  default. A shorter Vera ships beside her, so nothing of the first is lost; which of them the
  family meet by default is for the evals to say, against a real model.
- **Can the plain bot have a name?** No: a name belongs to a persona. Under none the bot is
  FamilyDB, and the family's name for her is kept for when she comes back.
- **Should kids ever change her?** No. The Personality page stays an admin's, and the chat can
  never change her, for anybody.

## What is left

- Run `uv run python -m evals --persona default --persona brief --persona none` against a real
  model, and choose the default from what it says. There was no key to run it with here, so
  Vera as first written stays the default until then.
- Dials, only if the family's notes in "Anything to add" keep saying the same things.
