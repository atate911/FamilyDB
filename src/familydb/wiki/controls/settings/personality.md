# Personality and family settings

Who the assistant is, and who the family is, in the family's own words. The assistant is called
Vera unless the family rename her. The persona changes how she speaks and never what she does: the
rules for ideas, plans and reminders stay as they are, and win wherever they meet. What you write about
the family is information she weighs when she suggests things.

Her description and your notes go at the front of every chat message, the weekend ideas and any
retry, ahead of the product's rules, which win wherever they disagree. What you write about the
family goes in the family block, after the rules. Both are cached between messages, so their cost is
their length: Vera as first written is about 2,800 tokens and her shorter version about 740 (the page
shows an estimate of yours; `familydb debug cost` gives the figure). Lookups on the web see neither.

## Who she is

| Setting | Default | What it does |
|---|---|---|
| Personality (`persona`) | Vera, as first written | Vera as first written, a shorter Vera ("in brief"), or **None: plain and brief**, where the answers come from the bot itself, called FamilyDB, with no character |
| What she is called (`persona_name`) | empty, so her own name | What the family call her, at most 40 characters and no braces. Used in her description, your notes and her lines, on the page, and in Telegram. Kept, unused, under None |
| Her description (`persona_text`) | the persona's own | The family's rewrite of her character, up to 20,000 characters (Vera's own is about 11,000). It describes how she speaks, not what she does, and `{name}` stands for what she is called. It is laid over that one persona alone, so a rewrite of Vera never changes the shorter Vera. If her own description is later improved, the page can show what changed and your rewrite is left as you wrote it |
| Anything to add (`persona_notes`) | empty | A few sentences of your own, such as "no emoji", "call Mia 'Captain'" or "less chat in the mornings". At most 1,000 characters, kept after her description, so they last when hers is improved or rewritten. Kept, unused, under None |

A rewrite can be undone with "Restore her original description" (shown only while there is one; clearing the
box does the same). Under None the name, description and notes boxes are hidden and what you wrote is kept for
when a persona is chosen again, but what you wrote about the family is still sent. Her name, your notes and
your lines are the family's whichever of the personas is chosen; a rewrite belongs to one persona.

## About the family

| Setting | Default | What it does |
|---|---|---|
| In your own words (`about_family`) | empty | Ages, tastes, what to avoid, how far you will go ("Alex is vegetarian. We don't drive more than an hour with the girls."). At most 4,000 characters, sent as written with every chat message. The Family page says who may message the assistant; this says who they are |

This is separate from what the assistant remembers on its own from conversation. Those memories are on the
**What Vera knows** page (called **What is remembered** when no persona is chosen), shown to parents and
admins, where each can be forgotten. Write here what should always be true.

## What she says unasked

Reminders, "how did it go?", notes after a lookup, and notices when she cannot answer are written from
lines, not thought up by a model, so they cost nothing and still arrive when the model is down. Each
box shows her line, and under it how it reads now, with made-up details filled in (`voice_lines`).
Type over a line to use your own, and `{name}` stands for what she is called.

- A line may have several wordings, one per row. Each message takes one of them, chosen from the message's id (or, for a reminder, from its details) and not by chance, so the same message always reads the same after a resend or a restart.
- The boxes cover reminders, follow-ups, notes after a lookup, button taps, the answers to `/today` and the other commands, what a kid is told when a limit is reached, Telegram greetings and the notices sent to admins; some are in folded groups. A reminder that falls due mid-conversation is mentioned in the reply instead.
- An empty box uses the default it shows.
- With no persona these are said plainly. Your own lines are kept for when a persona is chosen again.

Developer docs: `docs/PERSONAS.md`.
