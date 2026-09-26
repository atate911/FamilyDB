# How FamilyDB uses a model

The questions every model call has to answer, the calls there are, and the direction the code
grows in. What is built names the code it is in; what is not is marked "to come".
`docs/MEMORY.md` is the companion on what the bot remembers; the token-economy rules in
`CLAUDE.md` are the constraints both work in.

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

Every kind of call, present or future, answers these explicitly before it is on by default. An
experiment may answer "not known yet" to whether it worked, the second half of the fifth, so long
as it is off unless a setting turns it on, has its limits and goes through the gateway and the
spending limit like any other call, and is measured before it becomes a default.

### 1. Should a model be asked at all?

- Ask only when the answer needs language understanding or judgment. A question code can answer
  exactly (what is on Saturday, is it open, what did we rate it) is better answered by code,
  cheaper and never wrong. The page works this way, and so do Telegram's /today, /week, /tasks
  and /now (`commands.py`) and the buttons under a reminder or a follow-up (`buttons.py`); a
  question in the family's own words goes to the model.
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
  no further paid call is needed for the model to say it has finished. A hand-back that failed
  goes back to the model.
- Durable facts the family states ride along on the call that is already happening (the memory
  deltas of `docs/MEMORY.md`), not on a second call: one `remember` tool, and when remembering is
  all a message needs, the reply comes in that same call and ends the turn.
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
  the same. A turn that runs out of steps is given up at once, and code tells the family what
  was saved.

## The calls today

| Kind | Trigger | Model | Sees | May do | Returns |
|---|---|---|---|---|---|
| Chat | a family message (Telegram, page, console) | chat model, at the chat level | persona, prompt, family, up to 150 ideas in the prefix; date, who reads a shared chat, sender, a recently shared location, the memories chosen for the message, anything due to be carried, up to 20 messages of the last 6 hours, the newest within 6,000 characters | 19 chat tools | a reply; tool writes |
| Digest | the weekly schedule, or catch-up after a restart; after a failure, the retry job, still as the digest | chat model, at the digest level | the chat context, with a fixed question | the chat tools | a reply to the digest chat |
| Retry | every 5 minutes, for a failed message other than the digest, 3 times at most; never after running out of steps | chat model, at the chat level | the chat context, plus which writes already ran | the chat tools | a reply |
| Enrich | every 2 minutes, up to 3 pending ideas; a home idea with no place, link or location, and a gift that names no place, are skipped in code | worker model, at the lookup level | worker prompt, home area, the idea and what was saved before | web search (3), `save_place`, `skip_place` | a place record |
| Discover | a `suggest` call, cached 12 hours by window, constraints and topic | worker model, at the lookup level | worker prompt, home area and where they are, the window, its hours, the constraints and topic, never the question's wording | web search (4), `report_finds` | up to 6 finds |
| Transcribe | a voice note from somebody on the family list, before its chat turn | the hearing model: OpenAI's speech-to-text model or a Gemini model; never Claude, which takes no recordings | the recording, and one line naming the family, her and home so they are spelled right | nothing | its words, which become the message |

All of them go through one door, `agent/gateway.ask`, which runs the loop
(`agent/loop.run_turn`): the spending limit is checked before each call, and each call is
recorded in `llm_calls` with its kind. Hearing a voice note is not a turn (a recording in, its
words out, no prompt file and no tools), so it has a door of its own beside it, `gateway.listen`,
held to the same two rules: the limit first, and a record under the kind `transcribe`
("listening to voice notes" on `/status`). Its five answers: asked only for a voice note from
the family, while voice notes are switched on, when it is short enough and somebody with a key
can hear it; sees the recording and the names; may do nothing; its words are trusted as what
was said, marked as spoken so the chat model allows for mishearing; and it costs one bounded
request, which is not retried because the recording is not kept. `model_exists` and token
counting call a provider but generate nothing.

## Who is speaking

Chat, the digest and retries speak as a persona, Vera by default; the lookup and discovery
workers write for no reader and never carry one. `personas.active` gives the persona in force,
with what the family wrote on the Personality page laid over her (`docs/PERSONAS.md` is the
design). Her character, how she talks, goes first in the cached prefix, with the family's notes
after it, ahead of the product spec, which decides what she does. The product says the job wins,
not her character: the job's header begins "Where who you are and the job disagree, the job
wins.", so a rewrite of her cannot leave it out. Her name is filled in by code before anything is
sent, so the prefix names her and stays the same from one message to the next. She is how every
reply sounds, so she is measured like any other part of the prefix ("who the assistant is" in
`/status`: about 2,800 tokens for Vera as first written, about 740 in brief) and checked with
`python -m evals --persona` when she changes.

Who reads the reply is not hers to guess. In a shared chat, a Telegram group or the page's
conversation, one line in the turn, between the date and the message, says that everyone there
reads it, and whether kids are among them (`render_audience_line`); a private chat gets none. It
goes in the turn, never the prefix, because it depends on the chat. The spec says what follows
from it whoever she is: keep everything suitable for kids where they can read or a kid is
writing, and ask before a sensitive reminder goes in a shared chat.

What she says without being asked (reminders, "how was it?", lookup notes, the notices when she
cannot answer) is not a model call at all: `voice.py` words each event from her lines
(`personas/<key>/lines.toml`) or the family's rewrite of them, so it costs nothing and arrives
when the model is down or the day's limit is spent. A line may have several wordings, and code
chooses one by a CRC-32 of the event and the message's own id, or of the facts when there is
none, so the same message says the same words after a retry or a restart. The one place a model
does word such an event is where it was already going to be asked: a reminder, follow-up, nudge,
evening heads-up or lookup note that comes due while the family is talking is held for a moment
and handed to the next chat turn, whose reply mentions it; a reply that forgets is given the
written line.

## The gateway: one door, a declaration per kind of call

Everything that wants an answer from a model asks `gateway.ask` for a kind of call, and brings
only what is particular to this one: the conversation, and the context its tools run in. What
does not change from one call of that kind to the next is declared once, in `gateway.KINDS`:

```
kind            chat | digest | retry | enrich | discover
purpose         what it is for, in words, as the cost reports say it
surface         which model setting answers: the chat model or the lookup model
level           the setting naming how strong a model answers: everyday, better or best
prompt          which prompt file ("system" also brings the family and the idea list)
tools           the fixed tool list (None: every chat tool)
hand_back       the tools whose success is a worker's result, and ends its turn
closes          the chat tools that may end a turn with the reply they carry (remember)
web_searches    the cap on hosted search; none means no web at all
iterations      the setting that caps model calls in one turn
effort          the setting naming the reasoning effort
max_tokens      the output cap, thinking included (4,000 for workers, never above max_output_tokens)
```

What it gives:

- `llm_calls` records the kind (migration 0010), so `familydb debug cost` and `/status` say what
  answering the family, the digest, retries, lookups and discovery each cost.
- `familydb debug prompt` builds its request with the same function `ask` sends with, for chat
  and for a lookup (`--kind enrich --idea N`); a test checks the two are identical.
- A test fails if anything else in the package starts a turn, sends to a provider or asks one to
  transcribe, and another checks each declaration is whole: its prompt exists, its tools exist, a
  worker's hand-back is among its tools, a tool that closes a chat turn is one of the chat's own,
  and only workers get the web.

Still to come in the declaration, each as its own measured change: the gate each kind needs
before it runs (callers check for a key themselves, and the loop checks the spending limit),
per-kind retry rules, and escalating a call to a stronger level on evidence that the first one
failed.

## The composer: what goes in, part by part

Under the gateway sits the composer (`agent/compose.py`), and under that the providers:

| Layer | Its one job |
|---|---|
| Gateway | which kind of call this is, its rules, and the record of it |
| Composer | exactly what goes in, and (to come) turning what comes back into something usable |
| Providers | each vendor's exact format, both ways |

The composer builds every request from labelled parts: who the assistant is, the instructions,
who the family is, the idea list, where home is, the tool definitions, the recent conversation,
the message with today's date, and the earlier steps of the same turn. It is where token
efficiency is decided, and it works by choosing what goes in, not by squeezing words:

- **Measure before trimming.** Built: every call records the size of each part. A provider
  reports one real input total per call and never its split, and counting each part exactly would
  cost a request of its own, so the real total is shared out in proportion to the parts' sizes.
  The split is an estimate; the total is what was billed. `/status` and `familydb debug cost`
  show, per purpose, how many tokens each part takes per call and its share.
- **Budgets per part.** Each part gets a budget, and code fits it: the history by recency (the
  newest messages within 6,000 characters, each cut to 1,500, `agent/history.within_budget`),
  the memories by what bears on the message (`docs/MEMORY.md`), and, to come, the ideas the same
  way. A firm requirement (an allergy, a must-have) is never trimmed away; if requirements alone
  exceed a budget, the composer says so rather than dropping one quietly. The budgets are in
  characters; in real tokens is to come.
- **The prefix stays still.** The parts before the conversation are cached by the provider,
  which is the biggest saving there is. The composer never tailors them to a message; selected
  parts go after them. Tests hold it: the prefix built days apart is the same
  (`tests/test_prompt.py`), and what is remembered goes with the message, never in the cached
  part (`tests/test_memory.py`).
- **Reading the answer** (to come). The one place that validates what comes back, and checks the
  model's claims that code can check (the idea exists, the date is inside the window). The memory
  changes of `docs/MEMORY.md` are checked where they arrive, by the `remember` tool's rules.

Two things it must never do: ask a model to shorten a prompt (it spends tokens to save them,
and can change the meaning), or rewrite the cached part per request.

## Choosing models

The default is the cheapest model that meets measured quality, per kind, not one model for
everything. The direction:

- **Route by kind first.** A worker that fills in opening hours and a chat turn that plans a
  weekend need different things; each kind names its own model setting and its own level. Built:
  every company's lineup is known by level in `agent/providers/catalog.py` (everyday, better,
  best: GPT-6 Luna, Sol and Astra; Claude Haiku, Sonnet and Opus; Gemini Flash-Lite, Flash and
  Pro), with what each costs and whether it thinks before answering, and a test holds the catalog
  to what the provider modules send. `everyday` is each company's own model setting, its cheapest
  by default (a test holds that too); the family chooses a level per situation (`chat_level` for
  chat and retries, `digest_level` for the digest and its retries, `lookup_level` for lookups
  and discovery), and a call that moves to the fallback company is answered at the same level
  there. A level up never answers with a cheaper model than everyday, so an everyday model set
  above the lineup's, or one the price table does not list, stays. The family chooses; the model
  never does, and nothing is escalated because a question sounded hard.
- **Escalate on evidence, not on guesswork.** A cheaper model may hand a task up to a stronger one
  when code can see that it failed: a validation error, a hand-back that did not happen, an empty
  answer. Not because the question sounded hard.
- **Measure before switching.** A model is chosen or replaced on `evals/`: the family's own
  requests with the outcomes expected, graded by code, run against a live model for quality
  (`--provider` with `--model` or `--level` to compare) and tested against fakes for the shape.
  The settings page offers the models the price table knows; the evals decide the default.

## Where the next savings are

Each is a candidate change, roughly in order of value for effort, and each should be measured
before and after.

1. **The idea list goes whole into the prefix.** Up to 150 idea lines go with every message,
   whether they bear on it or not, and a change to any idea (a new one, an outcome recorded)
   makes the next message write that part of the cache again. Choosing the ideas a message needs
   in code, under a budget, as the memories are chosen (layer 2), or keeping only stable fields
   in the prefix, is the largest structural saving left.
2. **Characters, not tokens.** The history and the memories are fitted to budgets in characters,
   and `familydb debug cost` estimates the prefix from its characters; providers bill tokens.
3. **Earlier steps go again.** Every call in a turn carries the steps before it, and on Claude,
   where only the prefix is marked for the cache, they are paid for in full each time.

## Open questions

- Telegram's commands are answered without a model because the command says what is asked.
  Which questions in the family's own words could be, and how would a message reach that path
  without a model call to decide it?
- How far can layer 2 go? If ideas, plans and memories are all selected, what is left in the
  prefix is small and very stable; the question is how selection copes with "anything for the
  girls on a rainy day" without a model reading the whole list.
- What is the quality bar per kind, written down so a cheaper model can be tested against it?
  For chat, it is `evals/`: the family's own requests, graded by code on which tools ran
  with which arguments, what was saved and what the reply says (`uv run python -m evals`).
  Lookups and discovery have no such set yet, since they depend on what the web says that day.
- When should the family be told what a question cost?
