# Personality and family

The Personality and family card sets who the assistant is, and who the family is, in the family's own words. The assistant is called Vera unless the family rename her. The persona changes how she speaks and never what she does: the rules for ideas, plans and reminders stay as they are, and win wherever they meet. What you write about the family is information she weighs when she suggests things.

Her description (her character) and your notes go at the front of every chat message, the weekend ideas and any retry, ahead of the product's rules. What you write about the family goes in the family block, after the rules. Both are cached between messages, so their cost is their length: Vera as first written is about 2,800 tokens and the shorter version about 740, and the card shows an estimate for yours. Lookups on the web see neither.

## Who she is

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Personality (`persona`) | Vera, as first written | Chooses Vera as first written, a shorter Vera ("in brief"), or **None: plain and brief**, where the answers come from the assistant itself, called FamilyDB, with no character. | The listed personas, or None |
| What she is called (`persona_name`) | empty, so her own name | What the family call her, used in her description, your notes and her lines, on the web page and in Telegram. Kept, unused, under None. | At most 40 characters, no braces |
| Her description (`persona_text`) | the persona's own | The family's rewrite of her character: how she speaks, not what she does. `{name}` stands for what she is called. | Up to 20,000 characters (Vera's own is about 11,000) |
| Anything to add (`persona_notes`) | empty | A few sentences of your own, such as "no emoji", "call Mia 'Captain'" or "less chat in the mornings". Kept, unused, under None. | At most 1,000 characters |

A rewrite belongs to one persona alone, so a rewrite of Vera never changes the shorter Vera. If a persona's own description is later improved, the card can show what changed and your rewrite stays as you wrote it. Your notes go after her description, so they last when it is improved or rewritten. Press **Restore her original description** (shown only while there is a rewrite; clearing the box does the same) to undo a rewrite.

Under None the name, description and notes boxes are hidden and what you wrote is kept for when a persona is chosen again, but what you wrote about the family is still sent. The name, your notes and your lines belong to the family whichever persona is chosen.

## About the family

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| In your own words (`about_family`) | empty | Ages, tastes, what to avoid, how far you will go ("Alex is vegetarian. We don't drive more than an hour with the kids."). It is sent as written with every chat message. | At most 4,000 characters |

[Family](/wiki/controls/family) says who may message the assistant; this says who they are. It is separate from what the assistant remembers from conversation, which is on the **What Vera knows** page (**What is remembered** when no persona is chosen), where each memory can be forgotten. Write here what should always be true.

## What she says unasked

Reminders, "how did it go?", notes after a lookup, and notices when she cannot answer are written from lines, not thought up by a model, so they cost nothing and still arrive when the model is down. Each box shows her line, and under it how it reads now, with made-up details filled in (`voice_lines`). Type over a line to use your own; `{name}` stands for what she is called.

- A line may have several wordings, one per row. Each message takes one of them, chosen from the message's id (or, for a reminder, from its details) and not by chance, so the same message reads the same after a resend or a restart.
- The boxes cover reminders, follow-ups, notes after a lookup, button taps, the answers to `/today` and the other commands, what a kid is told when a limit is reached, Telegram greetings and the notices sent to admins. Some are in folded groups.
- An empty box uses the default it shows.
- A reminder that falls due mid-conversation is mentioned in the reply instead.
- With no persona these are said plainly. Your own lines are kept for when a persona is chosen again.

The rules behind the personas are in [Vera](/wiki/model/vera).
