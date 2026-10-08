# Vera

Vera changes how things are said, never what is done. She is the persona layer: the name, character and wording the family meets in every reply and in everything FamilyDB says unasked. To change her, use [Personality and family](/wiki/controls/settings/personality).

## What a persona is

A persona is words only. It never changes which tools are declared, what a tool does, what is saved, or what the web page lets anybody do. Three rules follow:

1. Anything that must hold whoever she is lives in the product's rules or in code, never in her character, because a family can rewrite or replace the character.
2. Anything that differs from message to message goes in the current turn, never in her character, which is cached.
3. An admin chooses who she is, on the page. The chat cannot change her, for the same reason it cannot change the [family list](/wiki/model/family-and-roles#why-the-list-is-not-a-tool): what a setting is, is not the model's to decide.

A persona is a name, a label, a character and a set of lines, one folder each. The **character** is how she talks. The **lines** are her wording for what FamilyDB says unasked. Two ship, both called Vera, and there is a third choice:

| Choice | What you get |
|---|---|
| Vera, as first written | The default. Her character is about 11,000 characters |
| Vera, in brief | The same Vera in about a quarter of the length |
| None | FamilyDB as itself, with no character and plain wording |

Her name is written once, in her folder. Her character and lines say `{name}` wherever it goes, and code fills it in before anything is sent, so the request is the same from message to message. Under None the name is FamilyDB.

## What the family lays over her

| Layer | Effect |
|---|---|
| Name | Fills `{name}` everywhere, at most 40 characters, and is kept but unused under None |
| Her description (a rewrite of her character) | Replaces that one persona's character and no other's |
| Anything to add (notes) | A few sentences in the family's own words, at most 1,000 characters, sent after her character, whichever of the two personas is chosen |
| Lines | Replace her wording of one event at a time; an empty box uses her default |

Under None the family's name, rewrite, notes and lines are kept and come back when a persona is chosen again. "About the family" is not part of this: it is still sent.

## Where she goes in the request

Her character goes first in the fixed start of each request, ahead of the product's rules. Under a persona that start reads: "Who you are", her character, the family's notes, then "The job", whose first sentence is "Where who you are and the job disagree, the job wins.", then the rules. That sentence is the product's, so a rewrite that leaves it out still gets it. Under None neither heading is sent.

The fixed start is the [prompt cache](/wiki/reference/glossary#prompt-cache): the part of a request that is the same each time, which the model company reads back at a lower price. Only turns a person reads carry her: chat, the weekend ideas message and retries. Lookups never do, because nobody reads their prose.

## What she costs

Her words go with every chat request, so each message pays their length at the cache-read price. At four characters a token, Vera as first written is about 2,800 tokens and Vera in brief about 740. A rewrite and the notes add their own length. The Personality and family page estimates the total for what you have written, and `familydb debug cost` gives the figure; run it as in [The command line](/wiki/operations/command-line#how-to-run-it).

## How FamilyDB words what it says unasked

Reminders, follow-ups, lookup notes, button taps, command answers, greetings and notices are worded by code, with no model call, so they still arrive when the model is down. Each event has a plain line, which her line or the family's replaces. A line may have several wordings, and code picks one by a fixed rule, not chance, so a resend says the same words.

A reminder due while the family is talking waits up to 2 minutes so the next reply can carry it. If none does, the written line goes out.

## Where a kid or a group reads

Where a kid reads, code says a line about the workings as a plain one instead: "can't answer now", "try tomorrow" or "type it for me" ([Kids](/wiki/model/family-and-roles#kids)). In a shared chat, one line in the turn tells the model everyone there reads the reply, and whether kids are among them, so any persona can choose its register. Staying suitable for kids is a rule in the product's spec, so no rewrite of her character removes it.

## Her name elsewhere

The web page, Telegram's `/start` and the greeting in a group all take the name from the same place. After each connect, and whenever the name or her `/start` line changes on the page, the Telegram bot's name and description are set to match (FamilyDB's under None). Only what differs is sent, and it costs no model call. A name typed in BotFather does not stick, because the name and description are set again after every connect (a restart, a reconnect, a new token).

## Before you change her

Read the estimate on the Personality and family page first, and prefer notes to a rewrite: notes survive when her own character is improved.

Developer docs: docs/PERSONAS.md, "What it is" and "Measuring her"; docs/AI_CALLS.md, "Who is speaking".
