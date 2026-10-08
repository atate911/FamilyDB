# What Vera knows

This page lists what the family has told the assistant about itself, such as "we are vegetarian now" or "Sam can't do long drives", so you can see it, add to it and forget any of it. Admins and parents see it; a kid does not. With no persona chosen, the side bar says **What is remembered** and the page's heading says "What FamilyDB knows". For what should always be true of the family, write it on [Personality and family](/wiki/controls/settings/personality) instead: that text is yours and is not a [memory](/wiki/reference/glossary#memory).

## What is on the page

1. A button, **Tell Vera something**, that jumps to the form.
2. The memories, grouped by whom they are about: the family first, then each person in family-list order, then "Others" for somebody switched off. Newest first within a group.
3. Beside them (below, on a phone): the form, a key to the tags, and a folded **Forgotten** list.

Each memory shows the fact in bold with its tags, then its kind (food and drink, things to do, places, health and needs, routines, or anything else), who said it and when, and a short quote of their message. A voice note says so, and so does "Added on this page". A memory from a kid's chat shows its quote to grown-ups here.

| Tag | Means |
|---|---|
| Must | A requirement said outright: an allergy, a rule, a "never". The assistant is told never to offer anything that breaks one, and to say when one ruled something out. Nothing in code enforces it |
| A guess | The assistant's own reading between the lines. It only leans on a guess, and a guess is never a Must |
| Until a date | Temporary. After that day it shows as "Ended" and is no longer used |

Said again outright, a guess stops being one. Said again in the same words, a memory is not kept twice. A correction replaces the old memory, which then leaves this page.

## Tell the assistant something

Say it in the chat ("Alex is allergic to shellfish"), or use the form:

1. Type what to remember, up to 200 characters, in the person's terms: "vegetarian". A mic, where the browser has one, fills it.
2. Choose whom it is about, and a kind.
3. Set **Until** if it is temporary. A date that has passed is refused.
4. Tick **A must or a never** only for a requirement.
5. Press **Remember it**.

The form runs the same `remember` tool the assistant would, as you, and never makes a guess. A repeat says "Already remembered".

## Forget something

Press **Forget** beside it, or tell the assistant "forget that". There is no confirmation. The words are kept under **Forgotten**, marked with who forgot them and when, so the assistant cannot save the same words about the same person again from a conversation. Only a person typing it on this page can add it back. The page cannot change a memory's wording: forget it and add it again.

Forgetting does not erase. The words stay in the database and its safety backups, and the chat message it came from stays in the chat. Nor does it undo what was already sent to the model company. Taking somebody off the family list for good deletes every memory about them ([Family](/wiki/controls/family#switch-off-or-take-off-for-good)).

## How it is noticed and what is sent

The assistant notices something lasting during the chat call that is happening anyway, and there is no separate model call. Each message goes with every Must and as many other memories as fit in a small budget. [How memory works](/wiki/model/memory) has the rules. Viewing the page, adding and forgetting make no model call.

## Who may do what

Admins and parents open the page, add and forget: it needs the "browse" permission, and the forms need "change". Anyone who chats can cause a memory, a kid included, and there are no private memories. [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) has the table.
