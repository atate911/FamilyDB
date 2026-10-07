# Household memory and token economy

What the family tells the bot about itself: how it is noticed, kept, chosen for each message and forgotten, and the token-economy rules it keeps to. "About the family" on the Personality page is separate: the family writes it, and it goes as written into the cached family context of every chat request. The daily spending limit is `agent/spending.py`.

## Core principle

Paid inference is limited. Use deterministic local code when it can do the task. Minimize total cost per successful task: repeated input, output, reasoning, cache creation/reads, search charges, retries and follow-up model calls. Measure tokens; fewer characters do not necessarily mean fewer tokens.

Human replies are brief: the useful answer, essential caveats, an action result when needed. Machine-facing content carries only the fields the next operation needs: compact validated structured data, stable IDs and enums, bounded lists, no redundant prose or duplicated records, unused/default fields omitted where the provider schema permits. Never sacrifice schema correctness, essential constraints or reliable execution to save tokens.

## Automatic memory without a separate AI pass

The model notices durable household facts and preferences during a conversation request that is happening anyway, and emits only what changed through one tool for every kind of memory, `remember` (`tools/memory.py`): at most five changes, each an add, a replace by m number, or a forget. There is no background extraction call after each message, no paid polling, and no model call just to summarize, retrieve, acknowledge a write or maintain the store. A message with nothing to remember sends no memory payload: the tool is not called, and its schema, the same every turn, sits in the cached prefix with the other tools.

A tool call normally costs a second completion for the model to read the result and reply. `remember` needs none to say "noted": when remembering is all a message needs, the model puts its whole reply in the tool's `reply` and the turn ends with it (`ToolContext.offer_reply`, `closing_tools` in `agent/loop.py`). Beside any other tool call, or with anything not saved, the turn carries on and the model answers after reading the results, so a message that also saves an idea takes no more calls than without memory. `tests/test_memory.py` holds this with fakes, the `remember_alone` eval against a real model.

A backlog import, or a repair needing new inference, is started by a person, bounded and cost-estimated first; never a scheduled job.

## Local storage and selection

- Memories are in SQLite, table `memories` (migration 0020): no embedding service, no other database. A row holds who it is about (a member, or the family), one of six kinds (food, activities, places, health, routine, other), the fact in their words and its normal form, whether it is firm (a requirement: an allergy, a must, a never) or a taste, whether it is a guess or said outright, an optional last day, the source message and who said it, and when, and for a must, the rule code holds suggestions to (`rule`, migration 0049). Code supplies ids, times and provenance; the model never repeats them.
- Persistence, duplicate checks, expiry, indexing, retrieval and validation are local. A duplicate is the same normal form (casefolded, without punctuation) about the same person. Whether differently worded facts mean the same is for the model, in the turn it is already having (a correction replaces by m number); code never takes a loose text match for the same meaning.
- `familydb/memory.py` chooses what goes with each message, in the uncached part of the request, so the cached prefix never moves when a memory does. Every firm one in force goes, whatever the message is about and however many: a requirement is never dropped for room. Then the rest, within 1,600 characters (about 400 tokens), those bearing on the message first: sharing a word with it, of a kind it touches on (food for a question about dinner), about the asker or the whole family, then the newest. Past its last day, nothing is sent. Each goes as one line with its m number, marked "must", "a guess" or "until"; never the whole store or its history. No model is asked which memories matter.

## Learning quality and user control

- Memories come from what the family says, never from the model's own suggestions or a fetched page. Each links to its source message without copying it.
- Said outright, a fact or requirement stands; a guess only leans on a decision and never rules one out, so a guess is never a must. Each applies to the person it is about, or the family.
- Qualifiers and time limits are kept: one disappointing visit is feedback, not a dislike; a temporary rule ends on its last day.
- A must that is a limit code can check is kept with a rule (`remember`'s `rule`): the longest drive, the dearest cost level, indoors or outdoors only, or idea tags to leave out ("Sam: no drives over 30 minutes until his back is better" is a drive of 30 minutes at most). The suggestion engine holds them (`suggest/rules.py`): before anything is checked, the rules of whoever is coming (as the question names them, with whoever asked; everybody's when it names nobody) and the family's tighten the question's own limits, the tightest winning, and each reason names the memory ("further than m4 allows", "outdoor only, and m6 says indoor"), so the reply can say why. An idea somewhere nobody has measured the drive to is offered as possible, with the limit said. `/now`, the evening-before backup and the discovery and lookup requests go through the same engine and keep the same rules. Only a must said outright holds: a taste or a guess with a rule keeps the words and not the rule, and the answer says so. The memory page shows what each holds ("held to: a 30 min drive at most"). A must code cannot check (an allergy, "never on a school night") goes with every message, as before, for the model to weigh.
- Said again, a memory is not kept twice, and said outright it stops being a guess. A correction replaces the old one, which points at its successor; nothing is deleted. Different members' preferences sit side by side. The model asks one short question only when the ambiguity changes a decision.
- The tool's rules are code, whatever the model asks: a name not on the family list is refused, a call carries at most five changes, a fact is at most 200 characters, a whole call is saved or none of it. No SQL comes from the model. The same message handled twice (a retry) keeps nothing twice, and a change that breaks a rule goes back to the model within the turn's step limit, never into an unbounded repair loop.
- Forgetting keeps the words, marked forgotten, and the tool will not save the same thing about the same person again from a conversation, whichever message it seems to come from, so neither old messages nor prompt history bring it back. A person typing it on the memory page can.
- The memory page (`/memory`, "What Vera remembers", in the bar for everybody signed in) lists what is remembered by whom it is about, where each came from (who, when, the part of their message, worded by code), and what was forgotten and when. Whoever may change things has a Forget button and a form to add one, both through `remember`.
- Stored locally does not mean processed locally: the memories chosen for a message go to the configured AI provider with it. People sign in as themselves, but what they see is the household's: there are no private per-person records.

## Budgets and acceptance

Every kind of call has limits (model calls per turn, a worker's searches, retries, output tokens) and the daily spending limit is checked before every call. Every billable request is accounted for before it is sent, cached input and hidden reasoning included. The least expensive configured model that passes the quality checks answers, with no routine second model reviewing it. Lookups and discovery are capped, deduplicated and cached where it helps (`docs/AI_CALLS.md`).

Memory adds no API call to an ordinary conversation and none while idle: nothing runs on a schedule for it. Tests hold the acceptance criteria: remembering alone costs one call, every firm requirement goes however little room there is, a repeated message does not duplicate a memory, and a change that cannot be kept goes back to the model rather than into a paid retry.

## Still to come

- Rules for more of what code could check (a day of the week, an hour by which to be home), when the family asks for them.
- Editing a memory's wording on the page (today: forget and add again).
- A measured comparison of task cost and success before and after memory on live models (a normal reply, an idea capture, a recommendation, a correction, a retry, an idle scheduled tick), which the remembering cases in `evals/` are ready to run.
