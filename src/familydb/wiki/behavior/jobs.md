# The scheduled jobs

The scheduled jobs are what FamilyDB does without being asked: reminders, lookups, the weekend ideas, the evening-before check and the housekeeping behind them. They run inside the long-running service (`familydb run`) on the family's time zone. `familydb web` serves only the page and runs none of them, so a page started alone sends no reminders.

A job that a setting turns off is not scheduled at all.

## The jobs

| Job | When by default | Setting that moves or turns it off | What it does | Calls a model? |
|---|---|---|---|---|
| Reminders (`reminders`) | every minute | none | Queues each due reminder and sends it | No |
| Admin alerts (`alerts`) | every minute | `admin_alerts` off | Tells each admin with a Telegram id what only an admin can fix | No |
| Forget locations (`forget_locations`) | every 10 minutes | none | Deletes shared positions older than a day | No |
| Retry failed (`retry_failed`) | every 5 minutes | `retry_interval_minutes`; `retry_max_attempts` bounds the tries | Resends stored replies that did not go, then answers messages whose turn failed | Only to answer a failed message |
| Look up new ideas (`enrich`) | every 2 minutes | `enrich_interval_minutes`; not scheduled while `web_tools_enabled` is off; `lookups_when` and `lookup_hour` (21) pick which ideas are due | One worker turn per idea due | Yes, when an idea is due |
| Weekend digest (`weekend_digest`) | Thursday 18:00 | `digest_day`, `digest_hour`; not scheduled while `digest_chat_id` is empty | Asks the weekend question as the first admin and sends the answer | Yes, one chat turn |
| Follow-ups (`follow_ups`) | daily 10:00 | `follow_up_hour`; `follow_ups` off | Asks how a finished plan went | No |
| Evening-before check (`plan_checks`) | daily 19:00 | `plan_check_hour`; `plan_checks` off | Checks tomorrow's plans against forecast and hours; speaks only when something is off | No |
| Models and prices (`model_watch`) | daily 05:17 | `model_watch` off | Reads what each company offers and two public price lists; tells admins what matters | No |
| Judgements (`judgements`) | every 15 minutes | `judgements`, off until you turn it on | Weighs a change in the models when a question is due | Rarely |
| Nudges (`nudges`) | every 15 minutes | `task_nudges` off | Brings up a thing to do kept for a part of the week | No |
| Catch-up (`catch_up`) | once, 60 seconds after the service starts | none | Runs what a restart skipped | Only if it sends the digest |
| Settings watch (`settings_watch`) | every 5 minutes | none | Moves the other jobs when a setting changes | No |

The program's own default leaves the digest chat empty and lookups off; the installer sets the digest to the page's chat and turns lookups on. The settings are on [Messages](/wiki/controls/settings/messages), [Lookups](/wiki/controls/settings/lookups) and [AI model](/wiki/controls/settings/ai-model#keeping-up-with-the-companies); this page does not repeat them.

## An idle job calls no model

Every job reads the database and the settings first and returns when there is nothing to do. Retries, lookups, the digest and judgements can reach a model, and so can catch-up when it sends the digest. The rest have no path to one: they word what they say from the persona's lines, in code. The evening-before check runs the suggestion engine with web discovery and stale-lookup queuing off.

A test hands retries, lookups, follow-ups and catch-up an API that fails on any request; for the other jobs it holds by the code. Each returns before a call when:

- **Retries:** no failed message is waiting, or each has used its tries.
- **Lookups:** web tools are off, no key serves lookups, no idea is due, or the day's [spending limit](/wiki/reference/glossary#spending-limit) is used up.
- **Digest:** no chat is set, there is no key, nothing here can send to that chat, there is no admin, or today's digest already went.
- **Judgements:** the setting is off, no question is due, there is no key, or the month's budget or the day's limit has no room.

## Job by job

### Reminders

It takes open things to do with a reminder due, up to 100 a run. Each goes to the task's chat, or to the owner's own Telegram chat when it began in a group and `private_when_personal` is on. After downtime the overdue ones go on the next minute, and one more than 10 minutes late says when it was due. While the family is talking in a chat, reminders, nudges, follow-ups, plan heads-ups and the note for one lookup wait about two minutes so the next reply carries them. [Tasks and reminders](/wiki/model/tasks-and-reminders) has the rest.

### Admin alerts

It needs an admin with a Telegram id and a Telegram connection in this process. Without either the trouble stays on Status under Needs a look, and the job tries again next minute. Each trouble is told once, again after 12 hours at the soonest while it lasts, and forgotten when the thing works again. A refusal the program cannot read is told only once it has happened twice.

### Retry failed

It first sends stored replies that never went, then retries each failed or unanswered message that has tries left, a sender here and no lease held. A failed digest is asked again as the digest. A message out of tries stays on Status under Messages that did not go through. [Lifecycles](/wiki/behavior/lifecycles) covers leases and delivery.

### Look up new ideas

By default it runs every 2 minutes but ideas wait for the evening: those waiting since before the last 21:00 are looked up together, up to 40 a run, and each chat gets one note. An idea asked for now goes first, with its own note. With `lookups_when` set to as soon as added, a run takes up to `enrich_batch` (3). See [Lookups](/wiki/controls/settings/lookups#when).

A busy company, or the day's limit, stops the run and leaves the rest waiting. A lookup that fails is marked failed and is not retried by itself: press **Look it up again** on the idea.

### Weekend digest

It asks "what should we do this weekend?" as the first admin through the chat pipeline, at `digest_level`. It can call tools, so one digest can be several calls and can include a web search for what is on ([how it is answered](/wiki/behavior/suggestions)). Its id carries the date, so a second run the same day sends nothing, and the retry job asks again after a failed turn. It skips, and logs why, when no chat is set, there is no model key, nothing in this process can send to that chat (Telegram is not connected here), or there is no admin.

### Follow-ups

It asks once about each confirmed plan that ended before today and started within the last week. It first brings plans in line with Google Calendar and waits when Google cannot be asked, so a cancelled plan is not asked about. A plan with an outcome already is marked asked without a message. The question goes to the plan's chat, or its maker's own chat when it began in a group.

### Evening-before check

It looks at plans for an idea, made in a chat, that start tomorrow and are unchecked, and returns before touching Google when there are none. Otherwise it syncs the calendar (waiting if Google cannot be asked), reads tomorrow's forecast (skipped without a home position) and checks rain for an outdoor idea and the place's saved hours against the plan's time. All well says nothing, and the plan is still marked checked. A heads-up goes to the plan's chat, with a backup idea when the engine finds a good one. A plan nothing can send to waits for the next run.

### Models and prices, and judgements

The daily check asks each company with a key which models the key may use (this costs no tokens), reads LiteLLM's and OpenRouter's price lists, and notes for admins what matters. It then compares the last week of each kind of call with the four weeks before. [Models and prices](/wiki/controls/status/models-and-prices) shows what it read.

Judgements ask a stronger model only about a question code filed. Once the lookup hour has passed (at once with lookups as soon as added), the day's questions go in one call at `judgement_level`; a refusal nobody can read goes at once. It stops when the month's spend plus 5 cents would pass `judgement_budget`, or the day's limit is used up.

### Nudges

It brings up a thing to do whose preferred window code can read ("some Saturday morning"), from an hour into that part of the day. It skips tasks that repeat, have a reminder pending or are under 12 hours old, and any nudged in the last six days; each chat gets at most one a day. It holds back when the calendar shows the next hour busy; with no calendar, or one it cannot reach, it goes anyway.

### Forget locations and settings watch

Forget locations deletes a shared position after 24 hours; the assistant uses one for only three. The settings watch re-reads the stored settings and adds, removes or reschedules jobs to match. A schedule you change on the page can take up to five minutes to move, and the log says `settings changed` and names what moved.

## After a restart

The digest, follow-ups, the evening check and the models check are cron-style and live in memory. One whose time passes while the service is down is not run when it returns, and one that starts more than an hour late (six for the models check) is dropped. Interval jobs carry on. A run is skipped while the same job is still running, and missed runs merge into one.

Catch-up covers the gap 60 seconds after the service starts. It:

1. Deletes shared positions past their day.
2. Asks follow-ups at any hour, without waiting for 10:00.
3. Runs the evening check if it is on and its hour has passed, even late at night.
4. Sends the digest if today is its day and its hour has passed, even late that day.
5. Runs the models check if it is on and 23 hours have passed since the last.

Repeating is safe: each plan and each day's digest is marked once. Lookups and reminders need no catch-up.

## Seeing that a job ran

| Where | What it shows |
|---|---|
| [Messages settings](/wiki/controls/settings/messages) | Each kind sent unasked: on or off, when, how many in 30 days, the last one, and the 20 latest in full |
| [Status](/wiki/controls/status#waiting-and-worth-a-look) | Ideas waiting for a lookup, failed lookups, and messages that did not go through |
| [Status](/wiki/controls/status#needs-a-look) | Troubles the alerts job tells admins about |
| [Models and prices](/wiki/controls/status/models-and-prices) | When each source was read, what changed, and what a judgement answered |
| [The log](/wiki/operations/diagnostics#logs) | Skips (`digest skipped: ...`), the catch-up result and settings moves; nothing else records forget-locations or the settings watch |

Telegram's connection and message leases are not scheduled jobs; [Lifecycles](/wiki/behavior/lifecycles) covers them.

Developer docs: `familydb/jobs/scheduler.py` (`job_specs`, `build_scheduler`), `familydb/jobs/` (one module per job, `catch_up.py`), `familydb/alerts.py`, `familydb/model_watch.py`, `familydb/judgement.py`, and `docs/DESIGN.md`, "Enrichment: filling in the details" and "Running and reliability".
