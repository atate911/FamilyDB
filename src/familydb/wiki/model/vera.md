# Vera

Vera is the persona layer: the name, character and wording the family meets in every reply and in everything the bot says unasked. This page explains how she is built and where she goes in a request. For the settings, see [Personality](/wiki/controls/settings/personality).

## She changes how things are said, never what is done

A persona is words only. It never changes which tools are declared, what a tool does, what is saved, or what the page lets anybody do. Three rules follow from that:

1. Anything that must hold whoever she is lives in the product's rules or in code, never in her character, because a family can rewrite or replace the character.
2. Anything that differs from message to message goes in the current turn, never in her character, which is cached.
3. An admin chooses who she is, on the page. The chat cannot change her, for the same reason it cannot change the [family list](/wiki/model/family-and-roles): what a setting is, is not the model's to decide.

## What a persona is

A persona is a name, a label, a character and a set of lines, one folder each. The **character** is how she talks. The **lines** are her wording for what the bot says unasked. Two ship, both called Vera, and there is a third choice:

| Choice | What you get |
|---|---|
| Vera, as first written | The default. Her character is about 11,000 characters |
| Vera, in brief | The same Vera in about a quarter of the length |
| None | The bot as itself, called FamilyDB, with no character and plain wording |

Her name is written once, in her folder. Her character and lines say `{name}` wherever it goes, and code fills it in before anything is sent, so the request is the same from message to message.

## What the family lays over her

| Layer | Effect |
|---|---|
| Name | Fills `{name}` everywhere, and is kept under None, unused |
| Rewrite of her character | Replaces that one persona's character and no other's |
| Notes | A few sentences in the family's own words, sent after her character whichever persona is chosen |
| Lines | Replace her wording of one event at a time; an empty box uses her default |

Under None the family's name, rewrite, notes and lines are kept and come back when a persona is chosen again. "About the family" is not part of this: it is still sent.

## Where she goes in the request

Her character goes first in the cached prefix, ahead of the product's rules. Under a persona the prefix reads: "Who you are", her character, the family's notes under their own heading, then "The job", whose first sentence is "Where who you are and the job disagree, the job wins.", then the rules. That sentence is the product's, so a rewrite that leaves it out still gets it. Under None neither heading is sent.

Only turns a person reads carry her: chat, the weekend digest and retries. Lookup and discovery workers never do, because nobody reads their prose.

## What she costs

Her words go with every chat request, cached, so the cost is their length. At four characters a token, Vera as first written is about 2,800 tokens and Vera in brief about 740. A rewrite and the notes add their own length. The Personality page estimates the total for what you have written, and `familydb debug cost` on the server gives the figure. The audience line, a few tokens in the turn, is not cached.

## How the bot words what it says unasked

Reminders, follow-ups, lookup notes, button taps, command answers, greetings and notices are worded by code through `voice.say`, with no model call. They still arrive when the model is down. Each event has a plain line, which her line or the family's replaces. A line may have several wordings, and code picks one by a CRC-32 of the event and a seed, usually the id of the message it answers, or of the facts when there is no seed. No chance is involved, so a resend, retry or restart says the same words. A line that cannot be filled in falls back to its plain one.

A reminder due while the family is talking is held for a moment so the next reply can carry it. If none does, the written line goes out.

## Where a kid or a group reads

Where a kid reads, code says a line about the workings in a plain one instead (`voice.PLAIN`): can't answer now, try tomorrow, or type it for me. See [The family and roles](/wiki/model/family-and-roles#kids).

In a shared chat, one line in the turn tells the model everyone there reads the reply, and whether kids are among them, so any persona can choose its register. Staying suitable for kids is a rule in the product's spec, so no rewrite of her character removes it.

## Her name elsewhere

The page, Telegram's `/start` and the greeting in a group all use the name through one place, `personas.active`. After each connect and whenever the name or her `/start` line changes on the page, the bot's name and description in Telegram are set to match (FamilyDB's under None). Only what differs is sent, and it costs no model call. A name typed in BotFather lasts until the next such change.

## Before you change her

1. Read the estimate on the Personality page and compare it with what you have now.
2. Prefer notes to a rewrite. Notes survive when her own character is improved.
3. Run the evals before and after any change to her character, a line or the audience line:

```bash
uv run python -m evals --persona default --persona none
```

An eval is a set of the family's own requests run against a real model for a few cents, graded by code on what was called, saved and said. Compare runs passed and input tokens.

Developer docs: `docs/PERSONAS.md`, `src/familydb/personas/__init__.py`, `voice.py` (`EVENTS`, `say`, `PLAIN`), `agent/prompt.py` (`JOB_HEADER`), `agent/render.py` (`render_audience_line`), `audience.py`, `evals/`, and `docs/AI_CALLS.md`, "Who is speaking".
