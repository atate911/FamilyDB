# What Vera knows

This page lists what the family has told the assistant about itself, such as "the girls are vegetarian now"
or "Sam can't do long drives", so you can see it, add to it and forget any of it. The name follows the
assistant's: the side bar says **What is remembered** when no persona is chosen. Admins and parents see it; a kid
does not. For what should always be true of the family, write it on
[Personality](/wiki/controls/settings/personality) instead: that text is yours, and it is not
a [memory](/wiki/reference/glossary#memory).

## What is on the page

1. A button, "Tell Vera something" (for those who may change things), that jumps to the form.
2. The memories, grouped by whom they are about: the family first, then each person in the order of the family
   list, then "Others" for somebody no longer active. Newest first within a group.
3. Beside them (below, on a phone): the form "Tell Vera something to remember", a key to the tags, and a
   folded "Forgotten" list.

Each memory shows the fact in bold, its tags, and under it its kind, who said it and when, and a
short quote of their message. A voice note says so. One added on this page says "Added on this page".
A kind is food and drink, things to do, places, health and needs, routines, or anything else.

| Tag | Means |
|---|---|
| Must | A requirement said outright: an allergy, a rule, a "never". The assistant is told never to offer anything that breaks one, and to say when one ruled something out. That is its judgment, not a filter in code |
| A guess | The assistant's own reading between the lines. It only leans on a guess, and a guess is never a Must |
| Until a date | Temporary. After that day it shows as "Ended" and is no longer used |

Said again outright, a guess stops being one. Said again in the same words, a memory is not kept twice.
A correction replaces the old memory, which then leaves this page.

## How it is noticed

Nothing runs in the background and there is no separate model call. The assistant reads each message during the
chat call that is happening anyway, and when somebody says something lasting, it calls one tool,
`remember`, with up to five changes: add, replace by number, or forget. Each fact is at most 200
characters and is about the family or one person on the list. The assistant is told to keep only what
the family said, never its own suggestions or a web page. A whole call is saved or none of it, and a
change that breaks a rule goes back to the assistant to fix within the turn.

When remembering is all a message needs, the assistant puts its reply inside the tool and the turn ends: one
call, not two. A message with nothing to remember adds no call and no payload beyond the tool's fixed description, which is cached with the other tools. Memories can come from any chat,
including a kid's own, and the page says who said each one. There are no private memories.

## What it costs and what is sent

Remembering costs no extra call. Choosing what to send is done by code, not a model. Each
message goes with:

- **Every Must in force**, however many, and whatever the message is about.
- **Then the rest, within about 400 tokens** (1,600 characters), those that bear on the message first: sharing a word with
  it, of a kind it touches on (food for dinner), about the sender or the whole family, then newest.
- Nothing past its last day, and no forgotten ones.

They ride in the part of the request that changes with each message, so adding or forgetting one never breaks the
[prompt cache](/wiki/reference/glossary#prompt-cache). They go to the model company with the message.
Viewing the page, adding and forgetting make no model call.

## Tell the assistant something

Say it in the chat ("Alex is allergic to shellfish"), or use the form:

1. Type what to remember, up to 200 characters, in the person's terms: "vegetarian". A mic, where the browser has one, fills it.
2. Choose whom it is about, and a kind.
3. Set Until if it is temporary. A date that has passed is refused.
4. Tick "A must or a never" only for a requirement.
5. Press **Remember it**.

A form on the page runs the same `remember` tool the assistant would, as you. It is never a guess. The page
says "Already remembered" when it is a repeat.

## Forget something

Press **Forget** beside it, or tell the assistant "forget that". There is no confirmation.
Forgetting keeps the words, marked with who forgot it and when, under "Forgotten", so the assistant cannot save
the same thing about the same person again from a conversation. Only a person typing it on this page can add it back. Only the same words count (ignoring capitals and punctuation); a reworded fact is new. The
page cannot change a memory's wording: forget it and add it again.

**Forgetting does not erase.** The words stay in the database and its safety backups, and the
chat message it came from stays in the chat. It also does not undo what was already sent to the model company. Taking
somebody off the family list for good deletes what is remembered about them; switching them off does not.

## Who may do what

Admins and parents see the page, add and forget. Anyone who chats can cause a memory. The roles table is on
[Security and trust](/wiki/security#who-may-do-what).

Developer docs: `docs/MEMORY.md`, `src/familydb/memory.py`, `src/familydb/tools/memory.py`, and `src/familydb/web/edits.py` (`add_memory`, `forget_memory`).
