# Household memory and token economy

Design decision, September 21, 2026; first built September 25, 2026. The daily spending limit it
asks for is (`agent/spending.py`). "About the family" on the Personality page, which the family
writes and which goes, as they wrote it, into the cached family context of every chat request,
stays beside it. How it was built, and what is still to come, is at the end
("As built").

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

The AI extracts durable household facts and preferences during an already-required conversation
request and emits only changed memory records alongside its normal answer. There is no routine
background AI extraction call after each message, no paid polling, and no separate model call
just to summarize a conversation, retrieve memories, acknowledge a memory write, or perform
routine memory maintenance. No change means no memory payload beyond a required schema sentinel.

The eventual response contract must allow local validation and persistence without adding a
model round trip solely for memory. Do not quietly implement this as a tool call that forces
another paid completion just to say "saved." Measure the complete request flow with fakes and
usage instrumentation before choosing the cross-provider response format.

The previous proposal for an automatic background memory worker is superseded by this design.
An optional backlog import or unusual repair that requires new inference must be explicitly
initiated, bounded, and cost-estimated; it is not a default scheduled job.

## Local storage and selection

- Store memories in the existing SQLite database. No paid embedding service or new database
  service is required for the alpha.
- Keep subject (household or member), category, concise fact/value, requirement versus preference,
  explicit versus inferred status, source message references, timestamps, and optional expiry.
  Application code supplies IDs, timestamps and provenance when it already knows them; do not
  spend generated tokens asking the model to repeat them.
- Perform persistence, exact duplicate checks, expiration, indexing, retrieval, and validation
  locally. Semantic interpretations and corrections come from the already-required AI turn;
  local code must not pretend unrelated text matches establish semantic equivalence.
- Retrieve relevant memories locally by participants, category, and text search under a context
  budget. Include applicable firm requirements even when they do not match query keywords.
  If requirements exceed a budget, fail visibly or narrow the task rather than silently dropping
  them. Send values needed for the task, not the entire memory database or audit history.
- Preserve stable cached prefixes. Variable selections and timestamps belong in the uncached
  request context. Keep an intentionally small, stable tool schema rather than adding one tool
  for every memory category.

## Learning quality and user control

- Learn about the household from family messages, never from the AI's own suggestions or a
  fetched website. Link each change to its source message without duplicating that message.
- Explicit statements can establish facts or requirements. Inferences stay tentative and only
  softly influence ranking. Apply preferences at the appropriate person or household scope.
- Preserve qualifiers and time limits. A single disappointing visit is not a broad dislike;
  a temporary restriction must not become a permanent rule.
- Merge repeated evidence and supersede corrected facts instead of accumulating duplicates.
  Different members' preferences can coexist. Ask one short clarification only when ambiguity
  materially affects a decision.
- Validate all deltas in application code; no arbitrary SQL from the model. Make processing
  idempotent per source message, with bounded delta counts and lengths. A malformed delta must
  not trigger an unbounded AI repair loop.
- Provide a local "What FamilyDB remembers" page with edit/forget controls and locally rendered
  source explanations. Forgetting must prevent regeneration from old evidence. Related chat
  history must not silently reintroduce a forgotten fact into future requests.
- Stored locally does not mean processed locally: selected memories are sent to the configured
  AI provider. People sign in to the page as themselves, but what they see is the household's:
  there are no private per-person records.

## Budgets and evidence required before release

The implementation should enforce configurable request, tool-loop, worker, retry and output
budgets, plus an optional aggregate spending ceiling. Account for every billable request type
before dispatch; do not treat cached input or hidden reasoning as free. Use the least expensive
configured model that passes task-quality checks, without a routine second model reviewing it.

Compare representative task cost and success rate before and after memory: a normal reply,
an idea capture, a recommendation, a correction, a retry, and an idle scheduled tick. The memory
feature must add zero API calls to an ordinary completed conversation and zero calls while idle.
Regression checks must also show that relevant requirements survive context limits, repeated
messages do not duplicate memories, and errors do not cause paid retry storms.

Background lookups and discovery elsewhere in FamilyDB should also be bounded, deduplicated,
and cached where appropriate. The daily spending limit, per-kind accounting and worker budgets
exist; all of the memory behavior above remains implementation work.

## As built

What the first version does, against the design above.

- **One small tool, riding on the call that is already happening.** The chat model has one
  more tool, `remember` (`tools/memory.py`), taking at most five changes: add, replace by its m
  number, or forget. Its schema is the same on every turn. When remembering is all a message
  needs, the model puts its whole reply in the tool's `reply`, and the turn ends there
  (`ToolContext.offer_reply`, and `closing_tools` in `agent/loop.py`): "noted" costs no second
  call. Beside any other tool call, or with anything not saved, the turn carries on as usual,
  so a message that also saves an idea costs what it did. `evals/` holds it to one call.
- **Stored locally** in `memories` (migration 0020): who it is about (a member, or the family),
  one of six kinds (food, activities, places, health, routine, other), the fact in their words
  and its normal form, firm or not, a guess or said outright, an optional last day, the source
  message and who said it, and when. Code supplies the ids, times and provenance.
- **Rules in code**, whatever the model asks: a name not on the family list is refused; the same
  thing about the same person is not kept twice, and said outright it stops being a guess; a
  guess is never a must; a correction replaces and points at what replaced it; nothing is
  deleted; a whole call is saved or none of it.
- **Chosen locally for each message** (`familydb/memory.py`), in the uncached part of the
  request, so the cached prefix never moves when a memory does: every firm one in force, however
  long they run; then the rest under a budget (1,600 characters), those sharing a word with the
  message, of a kind it touches on or about whoever is asking first. What has passed its last
  day is not sent. Each is one line with its m number, marked "must", "a guess" or "until".
- **Forgetting** keeps the words, marked forgotten, and the tool will not save the same thing
  about the same person again from a conversation, whichever message it seems to come from;
  a person typing it on the memory page can. So old evidence and the history in the prompt
  cannot bring it back.
- **The memory page** (`/memory`, "What Vera remembers", in the bar for everybody signed in)
  lists what is remembered by whom it is about, where each came from (who, when, and the part
  of their message it came from), what was forgotten and when, with a Forget button and a form
  to add one, both through `remember`.

Still to come: code applying firm requirements in the suggestion engine itself (today the model
weighs them, told to never offer what breaks one); editing a memory's wording on the page (today
it is forget and add again); and a measured comparison of task cost before and after on live
models, which `evals/` (the remembering cases) is ready to run.
