# Ideas and places

An [idea](/wiki/reference/glossary#idea) is something the family might do one day, and a place is the set of facts FamilyDB looks up for it. This page explains how ideas, places and outcomes are kept, what moves an idea from one status to the next, and how an idea is filled in from the web. To add, edit or look one up, use the [Ideas page](/wiki/controls/ideas).

## What an idea is

All ideas live in one table. The *kind* is free text, so a new kind needs no change to the software. The assistant is told to prefer one of `restaurant`, `activity`, `outing`, `day_trip`, `trip`, `show`, `event`, `seasonal`, `home`, `gift` or `other`, and to invent a kind only when none fits. A kind is saved in lower case, and any way of saying present ("present", "gifts", "gift idea") is saved as `gift`.

| Part | What it holds |
|---|---|
| For | Who it is for, as typed: "whole family", "with the girls". Empty means anyone |
| Tags | Lower-case keywords, sorted, without repeats |
| Setting, weather | Indoor, outdoor or either; and any, dry, warm or snow |
| Seasons | Only when the idea suits some seasons |
| Cost level | 0 free, 1 cheap, 2 moderate, 3 pricey, 4 expensive. Empty is unknown |
| Happens from, until | Only for something tied to dates, such as a festival or a show's run |

**Dates.** *Happens from* is a day, or a day and start time. *Happens until* is the last day, empty when there is no end. A start time alone means one day. An end before the start is refused, so is an end with no start, and so is a change that leaves the idea already over. Clearing the start clears the end. A suggestion rules out a dated idea for days it is not on, and an idea with seasons for the wrong season.

## Status

| Status | How an idea gets there |
|---|---|
| idea | The start. A plan cancelled, or its event deleted in Google, puts a planned idea back. So does **Bring it back**, or the **Didn't go** button on a follow-up |
| planned | A plan is made for it |
| done | An outcome is recorded, even for a dropped idea |
| dropped | Somebody drops it. It leaves lists, suggestions and lookups and keeps its outcomes and place |

Only a *planned* idea goes back by itself; a done idea stays done. Nothing deletes an idea. See [plans and the calendar](/wiki/model/plans-and-calendar) for the plan side.

## Duplicates

When an idea is added, FamilyDB reduces the title to a plain form: lower case, punctuation turned to spaces, spaces collapsed, so "Ramen Place, Main St." and "ramen place main st" are the same. An idea that is not dropped with the same plain title is a duplicate, and so is one whose title is 85 percent alike or more to one of up to 20 text-search matches. A duplicate adds nothing, and the assistant is handed the existing idea. Only titles are compared, and dropped ideas are not.

## Places

A place holds the facts looked up for an idea: address, coordinates, website, booking link, phone, price note, opening hours, drive time from home, the pages the facts came from, and when they were last checked. An idea that is not a place has none. Two ideas with the same place name, ignoring capitals, share one place, and a new lookup replaces its facts.

- **Hours** are kept per weekday as opening and closing times. A day recorded as closed is closed; a day with nothing recorded is unknown, and an unknown day is not guessed.
- **Drive times** are estimates: straight-line distance, a road factor and an average speed, from home. With no home position there is none. The factors are on [General](/wiki/controls/settings/general).
- **Stale** means never checked, or checked more than `place_stale_days` ago (30 by default, on [Lookups](/wiki/controls/settings/lookups)). The page marks the details as possibly out of date. A suggestion treats the idea as only "possible", and, when lookups are on, a suggestion the assistant makes also queues a fresh lookup. The Telegram commands that run the suggestion step without a model, and the evening-before check, queue none.

## How an idea is filled in

Each idea carries a lookup state.

| State | Meaning |
|---|---|
| pending | Waiting for a lookup. Every new idea starts here |
| done | A place was saved |
| skipped | Nothing to look up |
| failed | The lookup could not identify it, ended without saving, or hit an error. Not retried by itself |

Code decides first. A `home` or `gift` idea with no place and no link is skipped with no model call (a gift's link is ignored, as it points at the thing itself).

Otherwise one idea gets one [worker turn](/wiki/reference/glossary#worker-turn), apart from the chat, with its own short instructions. It may search the web at most three times, runs at most `worker_max_iterations` steps (12 by default), and its output is capped at 4,000 tokens. Its only tools are `save_place` and `skip_place`, and each must name the idea it was given or the call is refused, so a fetched page cannot talk it into writing elsewhere.

- `save_place` stores the place, links it and marks the idea done. With no coordinates given, FamilyDB looks the address up and estimates the drive. Only real web addresses are kept as links. The idea's location is filled in only when it had none; nothing else on the idea changes.
- `skip_place` marks it skipped ("not one place") or failed, with a reason of up to 500 characters.

The result is read from what the worker did, not what it said. No hand-back means failed ("worker ended without saving"). A retryable error, or the day's spending limit, leaves the idea pending and stops the run. Any other error marks it failed with the reason. To try a failed one again, use **Look it up again**, or run `familydb enrich --idea <number>`. When lookups run, and the note sent afterwards, are on [Lookups](/wiki/controls/settings/lookups) and [jobs](/wiki/behavior/jobs).

## How it went

An [outcome](/wiki/reference/glossary#outcome) is one time the family did something: the day (not in the future), an optional rating from 1 to 10, an optional would-repeat, notes, who recorded it, and the plan if there was one. An idea can have many.

Recording one marks the idea done, adds one to its times done, sets the last done day to the latest, and recomputes the average over the rated ones. The latest would-repeat answer decides: while it is "no" the idea stays out of suggestions, and an outcome with no answer changes nothing.

## Presents

An idea of kind `gift` is a present. It is hidden from every kid, always. By default it is also hidden from any grown-up named in its *For* list, matched as a whole word, ignoring capitals. A parent can choose a different list of grown-ups on the idea's edit form, even an empty one. Under the shared password nothing is hidden.

A hidden present is missing from lists, counts, search, the assistant's tools and direct links, and a hidden idea number answers "no idea". A thing to do about it is hidden the same way. A present is never suggested as something to do, and never looked up unless it names a place. Hiding follows the kind: a present saved as another kind is not hidden. See [things to do and reminders](/wiki/model/tasks-and-reminders) for birthdays and [wish lists](/wiki/model/wishes).

## The ideas list in the prompt

Each chat message carries the idea list in the [cached start of the request](/wiki/reference/glossary#prompt-cache): one line per idea, oldest first, leaving out dropped ideas and presents. Only the newest `prompt_idea_limit` are listed (150 by default; 0 sends all, set on [Spending](/wiki/controls/settings/spending)). The request says how many older ones were left out and tells the assistant to use `search_ideas`, which filters by words, kind, status, who, setting, length, cost, tags and recently done. A line leaves out the lookup state, so a finished lookup does not rewrite the cached part. Adding or changing an idea does, and the next message writes the cache again.

Developer docs: `src/familydb/store/ideas.py`, `places.py`, `outcomes.py`; `tools/ideas.py`, `places.py`, `outcomes.py`; `presents.py`; `jobs/enrich.py`; `agent/worker.py`; `agent/prompt.py` (`trim_ideas`); `docs/DESIGN.md`, "Enrichment: filling in the details".
