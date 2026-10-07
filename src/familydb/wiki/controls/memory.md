# What Vera knows

This page lists what the family has told the assistant about itself, such as "the girls are vegetarian now"
or "Sam can't do long drives", so you can see it, add to it and forget any of it. Admins and parents see it; a
kid does not. With no persona chosen, the side bar says **What is remembered** and the page's heading says
"What FamilyDB knows". For what should always be true of the family, write it on
[Personality](/wiki/controls/settings/personality) instead: that text is yours and is not a
[memory](/wiki/reference/glossary#memory).

## What is on the page

1. A button, "Tell Vera something", that jumps to the form.
2. The memories, grouped by whom they are about: the family first, then each person in family-list order,
   then "Others" for somebody switched off. Newest first within a group.
3. Beside them (below, on a phone): the form, a key to the tags, and a folded "Forgotten" list.

Each memory shows the fact in bold with its tags, then its kind (food and drink, things to do, places,
health and needs, routines, or anything else), who said it and when, and a short quote of their message. A voice note says so,
and so does "Added on this page". A memory from a kid's chat shows the quote to grown-ups here.

| Tag | Means |
|---|---|
| Must | A requirement said outright: an allergy, a rule, a "never". The assistant is told never to offer anything that breaks one, and to say when one ruled something out. Nothing in code enforces it |
| A guess | The assistant's own reading between the lines. It only leans on a guess, and a guess is never a Must |
| Until a date | Temporary. After that day it shows as "Ended" and is no longer used |

Said again outright, a guess stops being one. Said again in the same words, a memory is not kept twice.
A correction replaces the old memory, which then leaves this page.

## How it is noticed

Nothing runs in the background and there is no separate model call. The assistant reads each message during the
chat call that is happening anyway. When somebody says something lasting, it calls one tool, `remember`, with
up to five changes: add, replace by number, or forget. Each fact is at most 200 characters and is about the
family or one person on the list. The assistant is told to keep only what the family said, never its own
suggestions or a web page. A call is saved whole or not at all, and a change that breaks a rule goes back to the
assistant to fix within the turn.

When remembering is all a message needs, the assistant puts its reply inside the tool and the turn ends, so
it is usually one call, not two. A message with nothing to remember adds only the tool's fixed description,
cached with the other tools. Any chat can add memories, a kid's own included, and the page names who said
each. There are no private memories.

## What is sent with a message

Code chooses, not a model. Each message goes with:

- **Every Must in force**, however many, whatever the message is about.
- **As many others as fit in what is left of about 400 tokens** (1,600 characters, Musts counted), those that bear on
  the message first: sharing a word with it, of a kind it touches on (food for dinner), about the sender or the
  whole family, then newest.
- Nothing past its last day, and nothing forgotten. A person who is switched off keeps their memories, and they
  still go with messages.

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

The form runs the same `remember` tool the assistant would, as you, and never makes a guess. A repeat says
"Already remembered".

## Forget something

Press **Forget** beside it, or tell the assistant "forget that". There is no confirmation. The words are kept,
marked with who forgot them and when, under "Forgotten", so the assistant cannot save the same thing about the
same person again from a conversation. A reworded fact is new: the match is on the same words, ignoring
capitals and punctuation. Only a person typing it on this page can add it back. The page cannot change a
memory's wording: forget it and add it again.

**Forgetting does not erase.** The words stay in the database and its safety backups, and the chat message
it came from stays in the chat. Nor does it undo what was already sent to the model company. Taking somebody
off the family list for good deletes every memory about them, though what they said about others stays with their
name removed; switching them off deletes nothing.

## Who may do what

Admins and parents see the page, add and forget. Anyone who chats can cause a memory. The roles table is on
[Security and trust](/wiki/security#who-may-do-what).

Developer docs: `docs/MEMORY.md`, `src/familydb/memory.py`, `src/familydb/tools/memory.py`, and `src/familydb/web/edits.py` (`add_memory`, `forget_memory`).
