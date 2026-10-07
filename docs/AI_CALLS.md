# How FamilyDB uses a model

The questions every model call answers, the calls there are, and the direction the code grows in.
What is built names its code; what is not is marked "to come". `docs/MEMORY.md` is the companion on
what the bot remembers; the token-economy rules in `CLAUDE.md` are the constraints.

## The one idea

**Code knows; the model understands and words.** Anything that can be looked up, counted, compared,
dated or checked is done by code and handed to the model as settled fact. The model is paid for what
code cannot do: reading what a person meant, choosing among options code has already judged, and
saying it briefly in the family's language. It proposes; code decides whether the proposal stands.

The suggestion engine is the pattern to copy: free time, weather, hours, travel and each idea's
verdict come from `suggest/`, are logged to `suggestions` and reach the model as structured results;
the model frames the question and writes the reply, and never recomputes a verdict.

## Five questions every call answers

Every kind of call answers these explicitly before it is on by default. An experiment may answer
"not known yet" to whether it worked (the second half of the fifth) so long as it is off unless a
setting turns it on, has its limits, goes through the gateway and the spending limit like any other
call, and is measured before it becomes a default.

### 1. Should a model be asked at all?

- Ask only when the answer needs language understanding or judgment. A question code can answer
  exactly (what is on Saturday, is it open, what did we rate it) is cheaper and never wrong by code:
  the page, Telegram's /today, /week, /tasks and /now (`commands.py`) and the buttons under a
  reminder or follow-up (`buttons.py`) work this way. A question in the family's own words goes to
  the model.
- Every trigger has a gate, checked before anything is paid for: a key exists (`can_ask`), the daily
  limit is not spent (`spending`), there is work to do (the idle path returns without a call), the
  result is not already known (a cache or earlier answer), and the message has not been answered
  already (dedupe and leases).
- Scheduled work never calls a model to find out whether there is work.

### 2. What does it see?

Context has three layers, and every piece of information belongs to exactly one:

| Layer | What goes there | Rule |
|---|---|---|
| Stable prefix | the system prompt, the tool list, who the family is | Changes only when the family or product changes. Cached. No dates, senders or ids. |
| Selected context | the ideas, plans, places and memories that bear on this message | Chosen by code for this message, under a token budget, always including firm requirements. |
| The turn | today's date, who is speaking, what they said, recent history | Volatile by nature. As short as it can be. |

- The model is given facts, not the means to rediscover them: an idea's hours and travel time, not a
  request to look them up; the verdicts, not the raw rules.
- Anything not needed for this message is not sent. Budgets are in tokens, measured, not characters
  (the characters-versus-tokens gap is listed under "Where the next savings are").
- Text from outside the family (fetched pages, place descriptions) is information, never
  instructions, and is marked as such where it enters a prompt.

### 3. What may it do?

- The tools declared to a kind of call never vary between turns (cache stability) and are the whole
  of its authority. Dispatch refuses anything undeclared, validates every input and enforces scope
  (an enrichment turn writes only its own idea).
- Some things are never the model's to decide, however asked: who may talk to the bot, what a
  setting is, how much may be spent, which model answers. The one exception is the family's own:
  with `judgement_acts` at "within_cost", a judgment call's choice of model is put in by code when
  it costs no more than the model it replaces, from options code drew up, and admins are told with a
  way to put it back (below).
- Web access happens only in worker turns, with their own prompt, tool subset and search limit. The
  chat never searches the web directly.
- A write the family would want to undo (deleting a plan, moving an event) is done by a tool whose
  result says exactly what changed, so the reply can say it and the family can reverse it.

### 4. What comes back, and what is trusted?

- Words for people are short free text. Anything code will read is a validated structured field,
  through a strict tool or schema, never parsed out of prose.
- A hand-back ends the work: when a worker has made its one hand-back call the turn is over, with no
  further paid call to say so. A hand-back that failed goes back to the model.
- Durable facts the family states ride along on the call already happening (the memory deltas of
  `docs/MEMORY.md`): one `remember` tool, and when remembering is all a message needs, the reply
  comes in that same call and ends the turn.
- What the model claims that code can check, code checks (an idea id exists, a date is inside the
  window, a place is the one asked about). A failed check is reported, not silently corrected.
- Every call is recorded: kind, model, tokens, estimated cost, outcome. A reply is stored before it
  is sent.

### 5. What may it cost, and did it work?

- Each kind has explicit limits: model calls per turn, output tokens, searches, retries, and whether
  it may move to the other provider (only before any tool has run).
- The measure is **cost per successful task**, not per call: a cheap model that needs a retry, or a
  second family turn to get it right, is not cheap.
- Retries are for failures a retry can fix (rate limits, outages), not for a model that ran out of
  iterations: the same turn with the same context costs the same and fails the same. A turn that
  runs out of steps is given up at once, and code tells the family what was saved.

## The calls today

| Kind | Trigger | Model | Sees | May do | Returns |
|---|---|---|---|---|---|
| Chat | a family message (Telegram, page, console) | chat model, chat level | persona, prompt, family, up to 150 ideas in the prefix; date, who reads a shared chat, sender, a recently shared location, the memories chosen for the message, anything due to be carried, up to 20 messages of the last 6 hours, the newest within 6,000 characters | 23 chat tools | a reply; tool writes |
| Digest | the weekly schedule, or catch-up after a restart; after a failure, the retry job, still as the digest | chat model, digest level | the chat context, with a fixed question | the chat tools | a reply to the digest chat |
| Retry | every 5 minutes, for a failed message other than the digest, 3 times at most; never after running out of steps | chat model, chat level | the chat context, plus which writes already ran | the chat tools | a reply |
| Enrich | every 2 minutes, up to 3 pending ideas; a home idea with no place, link or location, and a gift that names no place, are skipped in code | worker model, lookup level | worker prompt, home area, the idea and what was saved before | web search (3), `save_place`, `skip_place` | a place record |
| Discover | a `suggest` call, cached 12 hours by window, constraints and topic | worker model, lookup level | worker prompt, home area and where they are, the window, its hours, the constraints and topic, never the question's wording | web search (4), `report_finds` | up to 6 finds |
| Transcribe | a voice note from somebody on the family list, before its chat turn | the hearing model: OpenAI's speech-to-text or a Gemini model; never Claude, which takes no recordings | the recording, and one line naming the family, her and home so they are spelled right | nothing | its words, which become the message |
| Judge | a question code filed when a change needs weighing (a model in use going with several to take its place, new models for a company in use, a refusal nobody could read), only while `judgements` is on; the day's questions together with the evening's lookups, a refusal at once; within `judgement_budget` a month | the model at `judgement_level` (best by default) of the lookup company | `prompts/judge.md`; model names, prices, releases, what the family's calls use a model for, a refusal's status and error text; never the family's messages | `give_judgement` only, choosing among the options code gave | one choice per question, which code checks and acts on within `judgement_acts` |
| Price check | a price of a model in use the two price lists disagree on, filed like a judgment and asked with it | worker model, lookup level | `prompts/price_check.md`; the model and what each list says | web search (3), `report_price` | a price from the company's own page, taken only when it matches a list |
| Look | a photo from somebody on the family list, before its chat turn, one call each for up to four of an album's; in a group, only one sent to the bot | the lookup model of the company that looks things up, with a lookup's effort | the picture, at most 1600 pixels on its long side and 3.9 MB (Claude counts its 5 MB on the base64), `prompts/look.md` and the same line of names | nothing | what it is and the words in it that matter, at most 120 words, which become the message |

All go through one door, `agent/gateway.ask`, which runs the loop (`agent/loop.run_turn`): the
spending limit is checked before each call and each call is recorded in `llm_calls` with its kind.
`model_exists` and token counting call a provider but generate nothing.

**Transcribe and Look are not turns** (a recording or picture in, words out, no tools), so each has
a door beside `ask`, `gateway.listen` and `gateway.look`, held to the same two rules: the limit
first, and a record under the kind `transcribe` or `look`. Neither is retried, since the recording
or picture is not kept. What the table does not say:

- *Transcribe:* asked only for the family's voice notes, while voice notes are on, when short enough
  and somebody with a key can hear it. Its words are trusted as what was said, marked as spoken so
  the chat model allows for mishearing.
- *Look:* asked only for the family's photos, while photos are on, when not too large, and in a group
  only when sent to the bot. `prompts/look.md` asks for what it is, then every name, date, time,
  place, price and link in it, as written, guessing nothing, none of its words taken as
  instructions. Its words are marked "(photo)"; one bounded request (1,024 output tokens at most,
  about a tenth of a cent on the default model). A model that declines is recorded before the refusal
  is raised, since it was billed; a description cut short keeps a "…". An album is one message: its
  photos are gathered for a second and a half, up to four looked at, the family asked once. It uses
  the lookup model (writing down what a picture says is extraction, not judgment) and is a call of
  its own, so the picture is sent once and what it showed stays in the conversation as words.

**Judging a change** is the one call made for the install rather than the family's day
(`familydb/judgement.py`). Asked only for a question code filed, while the family has it on, within
its monthly budget and the day's limit; never on a day with no question. Questions wait for the
evening's lookups and go together in one call; only a refusal, which may be stopping the bot, is
asked at once; a question with no answer is asked once more the next evening, then let go, the
rule's choice standing. It sees what code knows about the models, never a message, and may only hand
back a choice among the options code gave, which the tool checks. Code decides what follows: under
"within_cost" a model at the same cost or less (a tenth either way) is put in and told to admins with
a Put back button on the Status page; anything dearer waits there for an admin's press; a refusal
read as out of credit, a wrong key or a gone model is noted as that, and a part of a request named is
left out for that model in every process. A few cents on the best level, recorded as `judge`.
Checking a disputed price is the same door with the web and the lookup model (reading a page, not
weighing), its figure taken only when it matches one of the lists, recorded as `price_check`. Each
question, answer, reason and outcome is listed under Models and prices on Status.

Batch pricing (half-price, non-real-time endpoints) was left out: at a few cents a month it saves
cents and needs spending holds that outlive a call. The evening lookups are where it would pay, if
their cost ever matters.

## Who is speaking

Chat, the digest and retries speak as a persona, Vera by default; lookup and discovery workers write
for no reader and never carry one (`docs/PERSONAS.md` is the design). Her character goes first in the
cached prefix, then the family's notes, ahead of the product spec, which decides what she does. The
job wins over her character, and the product says so: the job's header begins "Where who you are and
the job disagree, the job wins.", so a rewrite of her cannot leave it out. Her name is filled in by
code before anything is sent, so the prefix stays the same from message to message. She is how every
reply sounds, so she is measured like any part of the prefix ("who the assistant is" in `/status`:
about 2,800 tokens for Vera as first written, about 740 in brief) and checked with
`python -m evals --persona` when she changes.

Who reads the reply is not hers to guess. In a shared chat one line in the turn, between the date
and the message, says everyone there reads it and whether kids are among them
(`render_audience_line`); a private chat gets none. It is in the turn, never the prefix, because it
depends on the chat. The spec says what follows whoever she is: keep everything suitable for kids
where they can read or a kid is writing, and ask before a sensitive reminder goes in a shared chat.

What she says unasked (reminders, "how was it?", lookup notes, notices when she cannot answer) is not
a model call: `voice.py` words each event from her lines or the family's rewrite, so it costs
nothing and arrives when the model is down or the limit is spent. The one place a model words such an
event is where it was already going to be asked: one that comes due while the family is talking is
held for a moment and handed to the next chat turn, whose reply mentions it; a reply that forgets is
given the written line.

## The gateway: one door, a declaration per kind of call

Everything that wants an answer from a model asks `gateway.ask` for a kind of call and brings only
what is particular to this one: the conversation and the context its tools run in. What does not
change between calls of that kind is declared once, in `gateway.KINDS`:

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

- `llm_calls` records the kind, so `familydb debug cost` and `/status` say what answering the
  family, the digest, retries, lookups and discovery each cost.
- `familydb debug prompt` builds its request with the same function `ask` sends with, for chat and
  for a lookup (`--kind enrich --idea N`); a test checks they are identical.
- A test fails if anything else in the package starts a turn, sends to a provider or asks one to
  transcribe; another checks each declaration is whole: its prompt and tools exist, a worker's
  hand-back is among its tools, a tool that closes a chat turn is one of the chat's own, and only
  workers get the web.

To come, each as its own measured change: the gate each kind needs before it runs (callers check for
a key themselves and the loop checks the spending limit), per-kind retry rules, and escalating a call
to a stronger level on evidence the first failed.

## The composer: what goes in, part by part

Under the gateway sits the composer (`agent/compose.py`), under that the providers:

| Layer | Its one job |
|---|---|
| Gateway | which kind of call this is, its rules, and the record of it |
| Composer | exactly what goes in, and (to come) turning what comes back into something usable |
| Providers | each vendor's exact format, both ways |

The composer builds every request from labeled parts: who the assistant is, the instructions, who
the family is, the idea list, where home is, the tool definitions, the recent conversation, the
message with today's date, and the earlier steps of the same turn. Token efficiency is decided here,
by choosing what goes in, not by squeezing words:

- **Measure before trimming.** Every call records each part's size. A provider reports one real input
  total per call, never its split, and counting each part exactly would cost a request of its own,
  so the total is shared out in proportion to the parts' sizes: the split is an estimate, the total
  is what was billed. `/status` and `familydb debug cost` show per purpose how many tokens each part
  takes per call and its share.
- **Budgets per part.** Code fits each: the history by recency (the newest messages within 6,000
  characters, each cut to 1,500, `agent/history.within_budget`), the memories by what bears on the
  message (`docs/MEMORY.md`), and, to come, the ideas the same way. A firm requirement (an allergy, a
  must-have) is never trimmed away; if requirements alone exceed a budget the composer says so rather
  than drop one quietly. Budgets are in characters; real tokens are to come.
- **The prefix stays still.** The parts before the conversation are cached by the provider, the
  biggest saving there is. The composer never tailors them to a message; selected parts go after.
  Held by tests: the prefix built days apart is the same (`tests/test_prompt.py`), and what is
  remembered goes with the message, never in the cached part (`tests/test_memory.py`).
- **Reading the answer** (to come). The one place that validates what comes back and checks the
  model's claims that code can check. Memory changes are checked where they arrive, by the
  `remember` tool's rules.

It must never ask a model to shorten a prompt (that spends tokens to save them and can change the
meaning), or rewrite the cached part per request.

## Choosing models

The default is the cheapest model that meets measured quality, per kind, not one model for
everything.

- **Route by kind first.** A worker filling in opening hours and a chat turn planning a weekend need
  different things; each kind names its own model setting and level. Every company's lineup is known
  by level in `agent/providers/catalog.py` (everyday, better, best: GPT-6 Luna, Sol and Astra; Claude
  Haiku, Sonnet and Opus; Gemini Flash-Lite, Flash and Pro), with its cost and whether it thinks;
  a test holds the catalog to what the provider modules send. `everyday` is each company's own model
  setting, its cheapest by default (also tested). The family chooses a level per situation
  (`chat_level` for chat and retries, `digest_level` for the digest and its retries, `lookup_level`
  for lookups and discovery); a call that moves to the fallback company is answered at the same level
  there. A level up never answers with a cheaper model than everyday, so an everyday model set above
  the lineup's, or one the price table does not list, stays. The family chooses; the model never
  does.
- **Escalate on evidence, not guesswork.** A cheaper model may hand a task up to a stronger one when
  code can see it failed (a validation error, a hand-back that did not happen, an empty answer), not
  because the question sounded hard.
- **Measure before switching.** A model is chosen or replaced on `evals/`: the family's own requests
  with the outcomes expected, graded by code, run against a live model for quality (`--provider` with
  `--model` or `--level` to compare) and against fakes for shape. The settings page offers the models
  the price table knows; the evals decide the default.

## Where the next savings are

Candidate changes, roughly by value for effort; measure before and after each.

1. **The idea list goes whole into the prefix.** Up to 150 idea lines go with every message whether
   they bear on it or not, and a change to any idea (a new one, an outcome recorded) rewrites that
   part of the cache on the next message. Choosing the ideas a message needs in code under a budget,
   as memories are chosen (layer 2), or keeping only stable fields in the prefix, is the largest
   structural saving left.
2. **Characters, not tokens.** History and memories are fitted to budgets in characters, and
   `familydb debug cost` estimates the prefix from characters; providers bill tokens.
3. **Earlier steps go again.** Every call in a turn carries the steps before it; on Claude, where
   only the prefix is marked for the cache, they are paid for in full each time.

## Open questions

- Telegram's commands are answered without a model because the command says what is asked. Which
  questions in the family's own words could be, and how would a message reach that path without a
  model call to decide it?
- How far can layer 2 go? If ideas, plans and memories are all selected, what is left in the prefix is
  small and very stable; how does selection cope with "anything for the girls on a rainy day" without
  a model reading the whole list?
- What is the quality bar per kind, written down so a cheaper model can be tested against it? For
  chat it is `evals/` (the family's own requests, graded by code on which tools ran with which
  arguments, what was saved and what the reply says: `uv run python -m evals`). Lookups and discovery
  have no such set yet, since they depend on what the web says that day.
- When should the family be told what a question cost?
