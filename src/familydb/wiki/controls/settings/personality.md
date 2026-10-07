# Personality and family settings

Who the assistant is, and who the family is, in the family's own words. The assistant is called
Vera unless the family rename her. This page changes how things are said and what the assistant
knows about the family, and never what she does: the rules for ideas, plans and reminders stay as
they are, and win wherever a persona and a rule meet.

Both the persona and the family's own words go at the front of every chat message, before anything
else the model is told, so they shape every reply. They are cached between messages, so their cost
is in their length: Vera as first written is about 2,800 tokens, and her shorter version about 740.
The page shows what yours come to now. Lookups on the web never see either.

## Who she is

| Setting | Default | What it does |
|---|---|---|
| Personality (`persona`) | Vera, as first written | Vera as first written, a shorter Vera ("in brief"), or **None: plain and brief**, where the answers come from the bot itself, called FamilyDB, with no character |
| What she is called (`persona_name`) | empty, so her own name | What the family call her, at most 40 characters and no braces. Shown wherever the page names her, in Telegram and in every message. Kept, unused, under None |
| Her description (`persona_text`) | the persona's own | The family's rewrite of her character. It describes how she speaks, not what she does. It is laid over that one persona alone, so a rewrite of Vera never changes the shorter Vera. If her own description is later improved, the page shows what changed and your rewrite is left as you wrote it |
| Anything to add (`persona_notes`) | empty | A few sentences of your own, such as "no emoji", "call Mia 'Captain'" or "less chat in the mornings". At most 1,000 characters, kept after her description, so they last when hers is improved or rewritten |

A rewrite can be undone with "Restore her original description". Her name, your notes and your lines
are the family's whichever persona is chosen; a rewrite belongs to one persona.

## About the family

| Setting | Default | What it does |
|---|---|---|
| In your own words (`about_family`) | empty | Ages, tastes, what to avoid, how far you will go ("Alex is vegetarian. We don't drive more than an hour with the girls."). At most 4,000 characters, sent as written with every chat message. The Family page says who may message the assistant; this says who they are |

This is separate from what the assistant remembers on its own from conversation. Those memories are
on [What she knows](/wiki/controls) and each can be forgotten. Write here what should always be true.

## What she says unasked

Reminders, "how did it go?", notes after a lookup, and notices when she cannot answer are written from
lines, not thought up by a model, so they cost nothing and still arrive when the model is down. Each
box shows her line, and under it how it reads now, with made-up details filled in (`voice_lines`).
Type over a line to use your own, and `{name}` stands for what she is called.

- A line may have several wordings, one per row. Each message takes one of them, chosen by the message itself and not by chance, so the same message always reads the same after a resend or a restart.
- An empty box uses the default it shows.
- With no persona these are said plainly. Your own lines are kept for when a persona is chosen again.

Developer docs: `docs/PERSONAS.md`.
