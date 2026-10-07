# Who the family talks to: the persona layer

The design of the persona layer: `familydb/personas/`, `voice.py`, the Personality page, the
audience line in the turn and the bot's Telegram contact. "Decisions" records what the family
decided, "What is left" what is open. Companions: `docs/AI_CALLS.md` ("Who is speaking") and
`docs/MEMORY.md`; the token-economy rules in `CLAUDE.md` are the constraints.

## The one idea

**She changes how things are said, never what is done.** A persona is words: the register the chat
model writes in, and the lines code fills in for what the bot says unasked. It never changes which
tools are declared, what a tool does, what the spec requires, what is saved, or what the page lets
anybody do. Three rules follow:

1. Anything that must hold whoever she is belongs to the product (`prompts/system.md`, or code),
   never to her character, because a family can rewrite or replace it.
2. Anything she is told that differs from message to message goes in the turn, never in her
   character, which sits in the cached prefix.
3. Who she is is chosen deliberately, by an admin, on the page. The chat can never change her, for
   the same reason it can never change the family list: what a setting is, is never the model's to
   decide.

## What it is

A `Persona` is her name, her label, her character and her lines, one folder each in
`familydb/personas/`. Two ship, both Vera: `default/`, Vera as first written, whom the family meet
unless they choose another, and `brief/`, a shorter Vera. The label tells them apart where listed
together ("{name}, as first written", "{name}, in brief"). `personas.active(settings)` is the one in
force, with what the family wrote on the Personality page laid over her.

| Part | Written in | Where it goes | Who changes it | What it costs |
|---|---|---|---|---|
| Her name, as the family call her | `persona.toml`, with `persona_name` over it | `{name}` in her character, their notes and every line; the page (`assistant`); Telegram's `/start` and the bot's contact | an admin: one line, at most 40 characters, no braces; empty is her own | nothing extra |
| Her character | `<key>/character.md` | first in the cached chat prefix, for chat, the digest and retries; never the workers | nobody on the page: a rewrite takes its place | Vera as first written about 2,800 tokens with every call, in brief about 740, cached |
| Their rewrite of her, per persona | `persona_text`, by persona key: the text, and hers as it shipped when they wrote it (`of`) | in place of that persona's character, nobody else's | an admin, for the persona in force | its length, cached |
| Their notes | `persona_notes` | after her character, under a header of their own, before the job | an admin, at most 1,000 characters | their length, cached |
| Her lines and their wordings | `<key>/lines.toml`, a line optionally a list of wordings, with `voice_lines` over them | `voice.say`, for every event in `voice.EVENTS` | an admin, one line at a time, one wording to a row | nothing: no model call |
| Who is listening | code (`render_audience_line`) | one line in the turn, between the date and the message, in a shared chat only | nobody: read from the chat and the family list | a few tokens, uncached, shared chat only |
| The Telegram contact | the Telegram supervisor | the bot's name and description in Telegram: her name and her `start` line, or FamilyDB's under none | follows whoever is speaking | nothing: no model call |
| About the family | the Personality page | the family block of the prefix | an admin (`about_family`) | its length, cached |

Under a persona the prefix begins "# Who you are", then her character or their rewrite, then their
notes under "## The family's own notes on how you talk", then "# The job", whose first sentence is
"Where who you are and the job disagree, the job wins.", then the product spec. That sentence is the
product's (`JOB_HEADER`), so a rewrite that leaves it out still gets it. The request under any
persona differs from the one under none only in that part.

`persona = none` is `PLAIN`: the bot as itself, called FamilyDB, with no character, neither header
and the plain wording for every line. Their name for her, rewrites, notes and lines are kept under
none, unused, and return when a persona is chosen again. Name, notes and lines are theirs whoever she
is; a rewrite is a copy of one persona's character and belongs to her alone.

**Wordings.** A line may have several, kept as a list, one per row in the page's box. Code chooses,
not chance: a CRC-32 of the event and a seed (the id of the message a notice answers, or the Telegram
update for a stranger and for `/start`), or with no seed of the facts the line is filled in with. The
same message always says the same words after a resend, retry or restart. A reminder is seeded by the
task and the reminder in force, so each time a task comes due (after a snooze, say) it may take
another wording, while a reminder worded again for the same time (its title changed) takes the same
one. A line kept as a string is one wording, line breaks and all, and saving it unchanged from the
page keeps it so.

**The audience line** says "This is the family's group chat: everyone in it reads your reply" in a
Telegram group and "This is the family's conversation on the page: everyone who signs in reads it"
in the page's chat, each ending ", kids among them" when the family list has an active kid. A private
chat gets none. Code cannot see who is in a group, so kids are read from the family list. The spec's
"Who is listening" says what to do with it, whoever she is; the rule that everything where a kid can
read stays suitable is there, where no rewrite reaches it.

**The Telegram contact.** The supervisor gives the bot the name it goes by and its `start` line as
the description (hers, or FamilyDB's under none), once after each connect and again when either
changes on the page, never on a timer. It asks Telegram what the contact says, sets only what
differs, cut to Telegram's limits. A wait Telegram asks for is waited out and Telegram out of reach
is tried again shortly; a refusal or other failure is logged and not retried until her words change
or the bot reconnects, and never stops the channel. A name typed in BotFather lasts until then.

## Where she can be used

From most to least worthwhile; each keeps to the rules above.

- **Chat replies.** The one place she costs tokens, and where she matters most.
- **What she says unasked.** Worth more than it looks: a family reads a reminder or "how was it?"
  far more often than a long answer. The Personality page shows how each line reads.
- **The digest**, as a chat turn, with the audience line when it goes to the family group.
- **Telegram's own contact**, with no model call and no trip to BotFather.
- **Meeting her.** The page that ends setup says who answers and that her name, how she talks or none
  at all are chosen under Personality; setup's Telegram step says her name will do for the bot
  (FamilyDB under none). Not a setup step: the bot is usable without it.
- **Memory.** A style preference stated in passing ("Sam likes it short", "no emoji for Mia") is a
  memory (`docs/MEMORY.md`), chosen by code to go with the messages it bears on, not a setting nor a
  rewrite. Settings are what an admin chose deliberately, in the cached prefix; memories are what the
  family said in passing, in selected context.

Never: the lookup and discovery workers, whose prose nobody reads; tool descriptions and results;
memory deltas and anything else code reads; the page's own words (`views.py`); any model call made
just to word a line.

## How she is configured

In layers, from least effort for the family to most. Each is written once, rendered by code, and
changes the cached prefix only when somebody saves it.

1. **Which persona**: Vera as first written, Vera in brief, or none. The list shows each by label,
   with roughly what she would add to every message if chosen, the family's name, rewrite and notes
   included.
2. **Her name**: `persona_name`, empty for hers, laid over her in `personas.active`. Everything that
   asks `active(settings).name` follows (prompt, lines, page, `/start`, Telegram contact). One line,
   at most 40 characters, no braces (a `{name}` in it would be filled in again). Under none the bot
   stays FamilyDB: a name belongs to a persona.
3. **Anything to add**: `persona_notes`, a few sentences of the family's own on how she talks, at
   most 1,000 characters, after her character. They survive a change to hers, being no copy of her.
   Offer this first to a family who want her a bit different; the rewrite is for the few who want her
   very different.
4. **A full rewrite**: kept per persona with her own character as it shipped when they wrote it. The
   box describes the persona in force and saving writes to her alone, never to a persona chosen in
   the same save. When hers has changed since, the page says so above their rewrite and offers,
   folded, a line diff of hers then against hers now, each line marked + or - as well as colored.
   Saving a changed rewrite takes hers as it is now, ending the notice. Restoring drops that
   persona's rewrite and nobody else's.
5. **Her lines**: wordings as above. Under each box, how the line in force reads, every wording
   filled in with example facts by the same code as `voice.say` ("Reminder: bins out (Sam). Task
   #12; ...", not `{title}{who}`).
6. **Who is listening** (not a setting): the audience line, a few tokens from facts code already has,
   which lets any persona choose its register without her character guessing.

**Not built, and why.** Dials ("how much she says", "humor", "emoji"), each position one fixed
sentence: deterministic, cheap, testable, but the spec's own style lines ("Short replies. One emoji
at most.") would have to move into the persona layer for a dial to loosen them, and then none would
need a short character of its own. If families keep writing the same notes in "Anything to add",
those notes are the dials to make. More personas wait for a reason: each is a folder to keep and
must earn her place in the evals, which have not yet measured the two that ship. Pronouns wait for a
persona who is not a she.

**Not configurable, on purpose:** what she does (the spec's); a persona per person or per chat (more
than one cached prefix, more than one Vera); changing her from the chat; a model call to word a line;
a picture of her (`docs/STYLE.md`).

## What a persona folder must pass

Adding a persona is adding a folder, so what a folder must be is written down and tested:

- `persona.toml` names her, and may give her a label with no brace in it but `{name}`; `character.md`
  says `{name}` and never her name; every wording of every line in `lines.toml` can be filled in.
  (Tested.)
- Her character is about how she talks. It names no tool (tested), says nothing about dates, data or
  what to save, and need not say the job wins, because the product says it.
- The request built under her differs from the one under none only in the persona section: same
  tools, spec, family block, idea list and conversation. (Tested, for every folder.)
- She passes the evals at least as well as none does, and what she adds in tokens is known. (Measured
  against a real model, by hand: "What is left".)

## Measuring her

- `python -m evals --persona KEY|none|FILE`, repeated to compare: every case runs under each in turn
  from one budget, and the summary and `--json` give each persona's runs passed, input tokens (new,
  written to the cache, read from it) and estimated cost. A file is used as a rewrite of the default
  persona, held to the Personality page's limit.
- Checks graded by code, never a second model, on every reply whoever she is: at most one emoji, no
  "as an AI" filler, at most two exclamation marks, within the length every reply is held to.
- Cases for who is listening and who she is: a kid asking in the family group, graded on what code
  can see (suggestions for tomorrow, nothing saved, a reply short enough for a group); the same
  sensitive reminder asked in the group, where she asks first, and in private, where it is set at
  once; and "what's your name?" after a rename, which gets the new one, or FamilyDB under none.

Run them before and after any change to her character, a line or the audience line, as `CLAUDE.md`
asks of any prompt change.

## Decisions

- **Is every persona a she?** Yes, as a product decision. The page's wording of her stays, and
  `persona.toml` has no pronouns.
- **Vera fitted to this job, or as first written?** As first written, the default. A shorter Vera
  ships beside her so nothing of the first is lost; which the family meet by default is for the evals
  to say, against a real model.
- **Can the plain bot have a name?** No: a name belongs to a persona. Under none the bot is FamilyDB,
  and the family's name for her is kept for when she comes back.
- **Should kids ever change her?** No. The Personality page stays an admin's, and the chat can never
  change her, for anybody.

## What is left

- Run `uv run python -m evals --persona default --persona brief --persona none` against a real model
  and choose the default from what it says; until then Vera as first written is the default.
- Vera as first written says "do not ... imply access to memories you do not have", while what the
  family have told her goes with every message it bears on (`docs/MEMORY.md`). Whether that line makes
  her shy of using it wants an eval case with a memory in place, which there is not yet.
- Dials, only if the family's notes in "Anything to add" keep saying the same things.
