# How memory works

Remembering costs no extra model call when a message only needs remembering: the assistant puts its whole reply inside the `remember` step and the turn ends. It covers what the family says about itself ("Sam hates loud places", "no long drives until my back is better"). To see and forget memories, use [What Vera knows](/wiki/controls/memory).

## How a memory is noticed

Nothing runs in the background for memory. When somebody says something lasting, the model is already answering their message, and in that same call it uses one tool, `remember`, to say only what changed. The product's rules tell it to keep only what the family said, never its own suggestions or a web page. Code enforces the rest:

- A call holds at most five changes: add, replace by number, or forget.
- A fact is at most 200 characters.
- The person must be on the [family list](/wiki/reference/glossary#family-list) and switched on, or "family".
- A last day that has already passed is refused.
- A call that breaks one of these is saved by none of its changes. The error goes back to the model within the same turn, so it can fix it.

A tool call normally costs a second model call to read the result and reply. `remember` has a `reply` field to avoid that. The turn carries on instead when `remember` runs beside other tools, a change failed, or a change came back "not saved".

## What a memory holds

Each [memory](/wiki/reference/glossary#memory) is one row. Code fills in the ids, times and source; the model never repeats them.

| Part | What it holds |
|---|---|
| About whom | One family member, or the whole family |
| Kind | Food, activities, places, health, routine or other |
| The fact | In their words, up to 200 characters |
| Must or not | A **Must** is a requirement: an allergy, a rule, a "never". Otherwise it is a taste. The stored name for a Must is *firm* |
| Said or a guess | **A guess** is the model's reading between the lines |
| Until | An optional last day, counted through that day |
| Source | The message it came from, who said it and when |
| Status | In force, replaced or forgotten |

A guess is never a Must: code clears the flag if the model sets both. Memories belong to the household: each one sent to the model names whom it is about, not who said it, and the page shows who said it.

## What each message is sent

Code chooses, and no model is asked. It looks only at memories in force: not replaced, not forgotten, not past their last day.

1. **Every Must goes**, however many and whatever the message is about.
2. **The rest go while they fit** in what is left of 1,600 characters, about 400 [tokens](/wiki/reference/glossary#token), with the Musts counted first. Those that bear on the message come first: sharing a word with it, then of a kind it touches on (food for a question about dinner), then about the sender or the whole family, then newest. One too long to fit is skipped and a shorter one can still go.

Each goes as one line with its number, marked "must", "a guess" or "until <date>", and one more line says how many were left out. This block goes in the current turn, which is not cached, so adding or forgetting a memory never breaks the [prompt cache](/wiki/reference/glossary#prompt-cache). The cost is input tokens, bounded by the budget except that Musts are not cut for room.

A Must reaching the model does not force it to obey. The product's rules tell the assistant never to offer what breaks one and to say when one ruled something out, and code does not filter suggestions by Musts.

Code does not look at who is asking or who will read the reply. Memories reach every chat, a kid's included, so an adult's Must can reach a kid's chat. The only guard is the product's instruction to ask before putting a sensitive detail in a shared chat. There are no private memories.

## Said again, corrected, forgotten

- **Same memory.** Two facts are the same when they are about the same person and match after lowercasing, dropping punctuation and collapsing spaces. "Vegetarian!" and "vegetarian" match. A reworded fact is new in code's eyes; the model corrects by replacing the old memory by number.
- **Said again.** The memory is not kept twice. Said outright after a guess, it stops being a guess, and a repeated Must makes it a Must.
- **Corrected.** The old memory is marked replaced and points to its successor. Nothing is deleted.
- **Forgotten.** The words are kept, marked with who forgot them and when, and the memory is no longer sent. Because the words stay, the model cannot save the same words about the same person again from a conversation: the call comes back "not saved" and the other changes in it still go through. A differently worded version is a new memory. Only a person on the page can add the forgotten one back.

Forgetting does not erase. The words remain in the database and its backups, the chat message stays in the chat, and what was already sent to the model company cannot be recalled ([What is stored and for how long](/wiki/security/data-and-privacy)).

## When a person leaves the list

Switching somebody off keeps their memories in force, but no new memory can be added about them while they are off. Taking somebody off for good deletes every memory about them; a memory they said about somebody else stays, with their name removed. [Family](/wiki/controls/family#switch-off-or-take-off-for-good) has the full list.

## Not the same as About the family

"About the family" on [Personality and family](/wiki/controls/settings/personality) is text an admin writes. It is sent as written with every chat request, so it costs its length on every message and changes only when somebody edits it. A memory is a row kept from conversation and chosen per message. Put what should always hold on Personality; let memory collect what comes up in passing.

## Why it is built this way

Paid calls are the running cost, so memory spends none of its own: no extraction pass, no retrieval call, none to say "noted", no scheduled job. Storage, duplicate checks, expiry and choosing run locally.

Developer docs: docs/MEMORY.md, "Automatic memory without a separate AI pass" and "Local storage and selection".
