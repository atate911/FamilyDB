# Household memory and token economy

Design decision, September 21, 2026. This specifies the next implementation; it does not claim
that automatic household memory is already implemented. The daily spending limit it asks for is
(`agent/spending.py`). What exists today is written by hand: "About the family" on the
Personality page, which the family edits and which goes, as they wrote it, into the cached family
context of every chat request.

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
