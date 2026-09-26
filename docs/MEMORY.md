# Household memory and token economy

What the family tells the bot about itself: how it is noticed, kept, chosen for each message and
forgotten, and the token-economy rules it keeps to. "About the family" on the Personality page is
separate: the family writes it, and it goes, as written, into the cached family context of every
chat request. The daily spending limit these rules ask for is `agent/spending.py`. What is not
built yet is at the end ("Still to come").

## Core principle

Paid inference is a limited resource. Use deterministic local code whenever it can perform the
task. Minimize total cost per successful task, including repeated input, generated output,
reasoning, cache creation/reads, external search charges, retries, and follow-up model calls.
Measure token usage; fewer characters do not necessarily mean fewer tokens.

Human replies are brief by default: the useful answer, essential caveats, and an action result
when needed. Machine-facing content contains only the fields necessary for the next operation.
Use compact, validated structured data, stable IDs and enums, bounded lists, and no redundant
prose or duplicated records. Omit unused/default fields when the provider schema permits it;
do not sacrifice schema correctness, essential constraints, or reliable execution to save tokens.

## Automatic memory without a separate AI pass

The model notices durable household facts and preferences during a conversation request that is
happening anyway, and emits only what changed, through one tool for every kind of memory,
`remember` (`tools/memory.py`): at most five changes, each an add, a replace by its m number, or
a forget. There is no background extraction call after each message, no paid polling, and no
model call just to summarize a conversation, retrieve memories, acknowledge a memory write or
maintain the store. A message with nothing to remember sends no memory payload: the tool is not
called, and its schema, the same on every turn, sits in the cached prefix with the other tools.

A tool call normally costs a second completion, for the model to read the result and reply.
`remember` needs none to say "noted": when remembering is all a message needs, the model puts its
whole reply in the tool's `reply`, and the turn ends with it (`ToolContext.offer_reply`, and
`closing_tools` in `agent/loop.py`). Beside any other tool call, or with anything not saved, the
turn carries on and the model answers once it has read the results, so a message that also saves
an idea takes no more calls than it would without memory. `tests/test_memory.py` holds this with
fakes, and the `remember_alone` eval against a real model.

A backlog import, or an unusual repair that needs new inference, is started by a person, bounded
and cost-estimated first; it is never a scheduled job.

## Local storage and selection

- Memories are kept in the SQLite database, in `memories` (migration 0020): no embedding service
  and no other database. A row holds who it is about (a member, or the family), one of six kinds
  (food, activities, places, health, routine, other), the fact in their words and its normal
  form, whether it is firm (a requirement: an allergy, a must, a never) or a taste, whether it is
  a guess or was said outright, an optional last day, the source message and who said it, and
  when. Code supplies the ids, times and provenance; the model is never asked to repeat them.
- Persistence, duplicate checks, expiry, indexing, retrieval and validation are local. A
  duplicate is the same normal form (casefolded, without punctuation) about the same person.
  Whether two differently worded facts mean the same thing is for the model, in the turn it is
  already having (a correction replaces by m number); code never takes a loose text match for
  the same meaning.
- `familydb/memory.py` chooses what goes with each message, in the uncached part of the request,
  so the cached prefix never moves when a memory does. Every firm one in force goes, whatever the
  message is about and however many there are: a requirement is never dropped for room. Then the
  rest, within 1,600 characters (about 400 tokens), those that bear on the message first:
  sharing a word with it, of a kind it touches on (food for a question about dinner), about
  whoever is asking or the whole family, then the newest. What has passed its last day is not
  sent. Each goes as one line with its m number, marked "must", "a guess" or "until"; never the
  whole store or its history. No model is asked which memories matter.

## Learning quality and user control

- Memories come from what the family says, never from the model's own suggestions or a fetched
  page. Each links to its source message without copying it.
- Said outright, a fact or a requirement stands; a guess only leans on a decision and never rules
  one out, so a guess is never a must. Each applies to the person it is about, or the family.
- Qualifiers and time limits are kept: one disappointing visit is feedback, not a dislike, and a
  temporary rule ends on its last day rather than becoming a permanent one.
- Said again, a memory is not kept twice, and said outright it stops being a guess. A correction
  replaces the old one, which points at what replaced it; nothing is deleted. Different members'
  preferences sit side by side. The model asks one short question only when the ambiguity
  changes a decision.
- The tool's rules are code, whatever the model asks: a name not on the family list is refused,
  a call carries at most five changes, a fact is at most 200 characters, and a whole call is
  saved or none of it. No SQL comes from the model. The same message handled twice (a retry)
  keeps nothing twice, and a change that breaks a rule goes back to the model within the turn's
  step limit, never into an unbounded repair loop.
- Forgetting keeps the words, marked forgotten, and the tool will not save the same thing about
  the same person again from a conversation, whichever message it seems to come from, so neither
  old messages nor the history in the prompt bring it back as a memory. A person typing it on
  the memory page can.
- The memory page (`/memory`, "What Vera remembers", in the bar for everybody signed in) lists
  what is remembered by whom it is about, where each came from (who, when, and the part of their
  message it came from, worded by code), and what was forgotten and when. Whoever may change
  things has a Forget button and a form to add one, both through `remember`.
- Stored locally does not mean processed locally: the memories chosen for a message go to the
  configured AI provider with it. People sign in to the page as themselves, but what they see is
  the household's: there are no private per-person records.

## Budgets and acceptance

Every kind of call has its limits (model calls per turn, a worker's searches, retries, output
tokens), and the daily spending limit is checked before every call. Every billable request is
accounted for before it is sent, cached input and hidden reasoning included. The least expensive
configured model that passes the quality checks answers, with no routine second model reviewing
it. Lookups and discovery are held to the same: capped, deduplicated and cached where it helps
(`docs/AI_CALLS.md`).

Memory adds no API call to an ordinary conversation and none while idle: nothing runs on a
schedule for it. The tests hold the rest of what it must keep: remembering alone costs one call,
every firm requirement goes however little room there is, a repeated message does not duplicate
a memory, and a change that cannot be kept goes back to the model rather than into a paid retry.

## Still to come

- Code applying firm requirements in the suggestion engine itself. Today the model weighs them,
  told never to offer what breaks one.
- Editing a memory's wording on the page; today it is forget and add again.
- A measured comparison of task cost and success before and after memory on live models (a
  normal reply, an idea capture, a recommendation, a correction, a retry and an idle scheduled
  tick), which `evals/` (the remembering cases) is ready to run.
