# How FamilyDB uses a model

Design framework, September 23, 2026. It sets the questions every model call has to answer and
the direction the code should grow in. The gateway it describes is built (`agent/gateway.py`);
the rest is direction, and "today" below is what the code does now. `docs/MEMORY.md` is the
companion on what the bot remembers; the token-economy rules in `CLAUDE.md` are the constraints
both work in.

## The one idea

**Code knows; the model understands and words.** Anything that can be looked up, counted,
compared, dated or checked is done by code, and handed to the model as settled fact. The model is
paid for what code cannot do: reading what a person meant, choosing among options code has
already judged, and saying it briefly in the family's language. It proposes; code decides whether
the proposal stands.

The suggestion engine is the pattern to copy. Free time, weather, hours, travel and each idea's
verdict come from `suggest/`, are logged to `suggestions`, and reach the model as structured
results; the model frames the question and writes the reply. It never recomputes a verdict.

## Five questions every call answers

Every kind of call, present or future, answers these explicitly. A call that cannot answer one
of them is not ready to be added.

### 1. Should a model be asked at all?

- Ask only when the answer needs language understanding or judgment. A question code can answer
  exactly (what is on Saturday, is it open, what did we rate it) is better answered by code,
  cheaper and never wrong. The page already works this way; the chat does not yet have a
  model-free path.
- Every trigger has a gate, checked before anything is paid for: a key exists (`can_ask`), the
  daily limit is not spent (`spending`), there is work to do (the idle path returns without a
  call), the result is not already known (a cache or an earlier answer), and the same message has
  not been answered already (dedupe and leases).
- Scheduled work never calls a model to find out whether there is work.

### 2. What does it see?

Context is built in three layers, and every piece of information belongs to exactly one:

| Layer | What goes there | Rule |
|---|---|---|
| Stable prefix | the system prompt, the tool list, who the family is | Changes only when the family or the product changes. Cached. No dates, senders or ids. |
| Selected context | the ideas, plans, places and memories that bear on this message | Chosen by code for this message, under a token budget, always including firm requirements. |
| The turn | today's date, who is speaking, what they said, recent history | Volatile by nature. As short as it can be. |

- The model is given facts, not the means to rediscover them: an idea's hours and travel time,
  not a request to look them up; the verdicts, not the raw rules.
- Anything the model does not need for this message is not sent. The budget is in tokens,
  measured, not characters.
- Text from outside the family (fetched pages, place descriptions) is information, never
  instructions, and is marked as such where it enters a prompt.

### 3. What may it do?

- The tools declared to a kind of call never vary between turns (cache stability) and are the
  whole of its authority. Dispatch refuses anything undeclared, validates every input, and
  enforces scope (an enrichment turn writes only its own idea).
- Some things are never the model's to decide, however it is asked: who may talk to the bot, what
  a setting is, how much may be spent, which model answers.
- Web access happens only in worker turns, with their own prompt, tool subset and search limit.
  The chat never searches the web directly.
- A write the family would want to undo (deleting a plan, moving an event) is done by a tool
  whose result says exactly what changed, so the reply can say it and the family can reverse it.

### 4. What comes back, and what is trusted?

- Words for people are free text, short. Anything code will read is a validated structured
  field, through a strict tool or schema, never parsed out of prose.
- A hand-back ends the work. When a worker has made its one hand-back call, the turn is over;
  no further paid call is needed for the model to say it has finished.
- Durable facts the family states ride along on the call that is already happening (the memory
  deltas of `docs/MEMORY.md`), not on a second call.
- What the model claims that code can check, code checks: an idea id exists, a date is inside the
  window, a place is the one asked about. A failed check is reported, not silently corrected.
- Every call is recorded: which kind, which model, tokens, estimated cost, outcome. A reply is
  stored before it is sent.

### 5. What may it cost, and did it work?

- Each kind of call has explicit limits: model calls per turn, output tokens, searches,
  retries, and whether it may move to the other provider (only before any tool has run).
- The measure is **cost per successful task**, not cost per call: a cheap model that needs a
  retry, or a second turn from the family to get it right, is not cheap.
- Retries are for failures that a retry can fix (rate limits, outages), not for a model that ran
  out of iterations; running the same turn again with the same context costs the same and fails
  the same.

## The calls today

| Kind | Trigger | Model | Sees | May do | Returns |
|---|---|---|---|---|---|
| Chat | a family message (Telegram, page, console) | chat model | prompt, family, up to 150 ideas in the prefix; date, sender, up to 20 messages of the last 6 hours | 15 chat tools | a reply; tool writes |
| Digest | the weekly schedule, or catch-up after a restart | chat model | the chat context, with a fixed question | the chat tools | a reply to the digest chat |
| Retry | every 5 minutes, for a failed message, 3 times at most | chat model | the chat context, plus which writes already ran | the chat tools | a reply |
| Enrich | every 2 minutes, up to 3 pending ideas | worker model | worker prompt, home area, the idea and what was saved before | web search (3), `save_place`, `skip_place` | a place record |
| Discover | a `suggest` call, cached 12 hours | worker model | worker prompt, home area, the window and the question | web search (4), `report_finds` | up to 6 finds |

All of them go through one door, `agent/gateway.ask`, which runs the loop
(`agent/loop.run_turn`): the spending limit is checked before each call, and each call is
recorded in `llm_calls` with its kind. `model_exists` and token counting call a provider but
generate nothing.

## The gateway: one door, a declaration per kind of call

Everything that wants an answer from a model asks `gateway.ask` for a kind of call, and brings
only what is particular to this one: the conversation, and the context its tools run in. What
does not change from one call of that kind to the next is declared once, in `gateway.KINDS`:

```
kind            chat | digest | retry | enrich | discover
purpose         what it is for, in words, as the cost reports say it
surface         which model setting answers: the chat model or the lookup model
prompt          which prompt file ("system" also brings the family and the idea list)
tools           the fixed tool list (None: every chat tool)
hand_back       the tools whose success is a worker's result
web_searches    the cap on hosted search; none means no web at all
iterations      the setting that caps model calls in one turn
effort          the setting naming the reasoning effort
```

What it gives now:

- `llm_calls` records the kind (migration 0010), so `familydb debug cost` and `/status` say what
  answering the family, the digest, retries, lookups and discovery each cost.
- `familydb debug prompt` builds its request with the same function `ask` sends with, for chat
  and for a lookup (`--kind enrich --idea N`); a test checks the two are identical.
- A test fails if anything else in the package starts a turn or sends to a provider, and another
  checks each declaration is whole: its prompt exists, its tools exist, a worker's hand-back is
  among its tools, and only workers get the web.

Still to come in the declaration, each as its own measured change: an output limit and a
hand-back that ends the turn for workers, the gate each kind needs before it runs (callers
check a key and the spending limit themselves today), per-kind retry rules, and a model that a
kind may escalate to.

## Choosing models

The default is the cheapest model that meets measured quality, per kind, not one model for
everything. The direction:

- **Route by kind first.** A worker that fills in opening hours and a chat turn that plans a
  weekend need different things; each kind names its own model setting (chat and lookup already
  do).
- **Escalate on evidence, not on guesswork.** A cheaper model may hand a task up to a stronger one
  when code can see that it failed: a validation error, a hand-back that did not happen, an empty
  answer. Not because the question sounded hard.
- **Measure before switching.** A small set of recorded conversations with expected outcomes (run
  against fakes for the shape and occasionally against the live models for quality) is how a
  model is chosen or replaced. The settings page already offers the models the price table
  knows; this is what decides the default.

## What the first inventory found

Read from the code on September 23, 2026; each is a candidate change, roughly in order of value
for effort, and each should be measured before and after.

1. **A worker pays one more call after handing back.** The loop does not stop at a successful
   `save_place`, `skip_place` or `report_finds`, so every lookup costs a further call for the
   model to finish. Ending the turn at the hand-back saves one call per idea and per discovery.
2. **The idea list churns the chat cache.** Every idea line in the prefix ends in
   `details: pending|done|...` (`agent/render.render_idea_line`), so each finished lookup,
   and each outcome recorded, changes the prefix and the next message pays to write the cache
   again. Up to 150 lines go to every message whether they bear on it or not. Moving the list
   towards layer 2 (selected under a budget) or keeping only stable fields in the prefix is the
   largest structural saving, and it is where memory retrieval will sit too.
3. **Discovery's cache rarely hits.** Its key includes the question's wording
   (`suggest/discover.py`), so "what's on this weekend" and "anything fun Saturday" search twice.
   Keying on the window and the constraints would let the digest and the questions after it share
   one search, as the module's docstring intends.
4. **Some ideas need no lookup at all.** A home project or a vague idea still costs at least two
   worker calls to be skipped. The kind, and whether there is a location, can decide that in code.
5. **Workers inherit the chat's output limit** (16,000 tokens) though their only real output is
   one tool call. A small cap bounds a runaway turn.
6. **A turn that ran out of iterations is retried in full,** up to three times, at the same cost,
   with the same context. It should give up and say so.
7. **Accounting could not tell the kinds apart.** Now done: every call is recorded with its kind
   and reported by purpose. `debug cost` still estimates the prefix from characters; measuring
   it in real tokens is what is left.
8. **History is not budgeted.** Up to 20 messages of the last six hours are sent as they were
   written, however long. With Claude, only the system blocks are cached; history and earlier
   tool results in a turn are sent at full price each iteration.

## Open questions

- Which chat questions can be answered without a model, and how is a message routed to that path
  without a model call to decide it?
- How far can layer 2 go? If ideas, plans and memories are all selected, what is left in the
  prefix is small and very stable; the question is how selection copes with "anything for the
  girls on a rainy day" without a model reading the whole list.
- What is the quality bar per kind, written down so a cheaper model can be tested against it?
- When should the family be told what a question cost?
