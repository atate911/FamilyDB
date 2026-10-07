# Household memory

Household memory is how FamilyDB keeps what the family tells it about itself ("Sam hates loud places", "no long drives until my back is better") without a model call of its own. This page explains how a memory is noticed, kept, chosen for each message and forgotten. To see and forget memories, use [What Vera knows](/wiki/controls/memory).

## Noticed during a call that happens anyway

Nothing runs in the background for memory. When somebody says something lasting, the model is already answering their message, and in that same call it uses one tool, `remember`, to say only what changed. The product's rules tell it to keep only what the family said, never its own suggestions or a web page. That is an instruction to the model. Code enforces the rest:

- A call holds at most five changes: add, replace by number, or forget.
- A fact is at most 200 characters.
- The person must be on the [family list](/wiki/reference/glossary#family-list) and switched on, or "family".
- A last day that has already passed is refused.
- A call that breaks one of these is saved by none of its changes. The error goes back to the model within the same turn, so it can fix it, and the turn's step limit still applies.

A tool call normally costs a second model call to read the result and reply. `remember` has a `reply` field to avoid that. When remembering is all a message needs, the model puts its whole reply there and the turn ends in one call. The turn carries on instead when `remember` runs beside other tools, a change failed, or a change came back "not saved".

The tool is declared on every chat turn, so its description sits in the [prompt cache](/wiki/reference/glossary#prompt-cache) with the other tools.

## The record

Each [memory](/wiki/reference/glossary#memory) is one row. Code fills in the ids, times and source; the model never repeats them.

| Part | What it holds |
|---|---|
| About whom | One family member, or the whole family |
| Kind | Food, activities, places, health, routine or other |
| The fact | In their words, up to 200 characters |
| Firm or not | Firm is a requirement: an allergy, a rule, a "never". Otherwise it is a taste |
| Said or guessed | A guess is the model's reading between the lines |
| Until | An optional last day, counted through that day |
| Source | The message it came from, who said it and when |
| Status | In force, replaced or forgotten |

A guess is never firm: code clears the flag if the model sets both. The page shows the source as a quote read from the stored message, not a copy.

## What each message is sent

Code chooses, and no model is asked which memories matter. It looks only at memories in force: not replaced, not forgotten, not past their last day.

1. **Every firm memory goes**, however many and whatever the message is about.
2. **The rest go while they fit** in what is left of 1,600 characters, about 400 tokens, with the firm ones counted first. Those that bear on the message come first: sharing a word with it, then of a kind it touches on (food for a question about dinner), then about the sender or the whole family, then newest. One too long to fit is skipped and a shorter one can still go.

Each goes as one line with its number, marked "must", "a guess" or "until <date>". If some were left out, one more line says how many. This block goes in the current turn, which is not cached, so adding or forgetting a memory never changes the cached prefix. The cost is input tokens on messages that carry memories: bounded by the budget, except that firm ones are not cut for room.

A firm memory reaching the model does not force it to obey. The spec tells the model never to offer what breaks one and to say when one ruled something out. The suggestion engine does not apply them itself yet.

Code does not look at who will read the reply, so a memory is sent in a shared chat too. Whether to say something personal there rests on the spec's rule to ask first. There are no private memories.

## Said again, corrected, forgotten

- **Same memory.** Two facts are the same when they are about the same person and match after lowercasing, dropping punctuation and collapsing spaces. "Vegetarian!" and "vegetarian" match. A reworded fact is new in code's eyes: whether two wordings mean the same is for the model, which corrects by replacing the old memory by number.
- **Said again.** The memory is not kept twice. Said outright after a guess, it stops being a guess, and a firm repeat makes it firm.
- **Corrected.** The old memory is marked replaced and points to its successor. Nothing is deleted.
- **Forgotten.** The words are kept, marked with who forgot them and when, and the memory is no longer sent. Because the words stay, the model cannot save the same fact about the same person again from a conversation: the call comes back "not saved", with the date it was forgotten, and the other changes in that call still go through. Only a person typing it on the page can add it back.

**Forgetting does not erase.** The words remain in the database and its backups, the chat message stays in the chat, and what was already sent to the model company cannot be recalled. See [Data and privacy](/wiki/security/data-and-privacy).

## When a person leaves the list

Switching somebody off deletes nothing. Their memories stay in force and still go with messages, but no new memory can be added about them while they are off.

Taking somebody off for good deletes every memory about them. A memory they said about somebody else stays, with their name removed from it, and so does a memory they forgot. See [The family and roles](/wiki/model/family-and-roles).

## Not the same as About the family

"About the family" on [Personality](/wiki/controls/settings/personality) is text an admin writes. It is sent as written in the cached family block with every chat request, so it costs its length on every message, and it changes only when somebody edits it. A memory is a row kept from conversation, chosen per message, in the uncached turn. Put what should always hold on Personality; let memory collect what comes up in passing.

## Why it is built this way

Paid calls are the running cost, so memory spends none of its own: no extraction pass, no retrieval call, none to say "noted", no scheduled job. Storage, duplicate checks, expiry and choosing run locally.

Developer docs: `docs/MEMORY.md`, `src/familydb/memory.py` (`choose`, `BUDGET`), `src/familydb/tools/memory.py`, `src/familydb/store/memories.py`, and `src/familydb/agent/render.py` (`render_memories`).
