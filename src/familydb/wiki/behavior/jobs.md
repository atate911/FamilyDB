# The scheduled jobs

The scheduled jobs are what FamilyDB does without being asked: reminders, lookups, the weekend ideas, the evening-before check and the housekeeping behind them. They run inside the service (`familydb run`) on the family's time zone. `familydb web` alone runs none, so a page started alone sends no reminders. A job that a setting turns off is not scheduled at all, and a change to a schedule setting is picked up within 5 minutes.

## The jobs

| Job | When by default | Setting that moves or turns it off | Asks a model? |
|---|---|---|---|
| Reminders job | every minute | none | No |
| Alerts job | every minute | `admin_alerts` | No |
| Forget-locations job | every 10 minutes | none | No |
| Retry job | every 5 minutes | `retry_interval_minutes`; `retry_max_attempts` bounds the retries | Only to answer a failed message |
| Lookups job | every 2 minutes | `enrich_interval_minutes`; not scheduled while `web_tools_enabled` is off | Yes, one worker turn per idea due |
| Weekend ideas job | Thursday 18:00 | `digest_day`, `digest_hour`; not scheduled while `digest_chat_id` is empty | Yes, one chat turn |
| Follow-ups job | daily 10:00 | `follow_up_hour`; `follow_ups` | No |
| Evening-before check | daily 19:00 | `plan_check_hour`; `plan_checks` | No |
| Models and prices check | daily 05:17 | `model_watch` | No |
| Judgments job | every 15 minutes | `judgements`, off until you turn it on | Only when a question is due |
| Nudges job | every 15 minutes | `task_nudges` | No |
| Catch-up | once, 60 seconds after the service starts | none | Only if it sends the weekend ideas |
| Settings watch | every 5 minutes | none | No |

The program's own defaults leave `digest_chat_id` empty and `web_tools_enabled` off. The installer sets the weekend ideas to the web page's chat and turns lookups on. The settings are on [Messages](/wiki/controls/settings/messages), [Lookups](/wiki/controls/settings/lookups) and [AI model](/wiki/controls/settings/ai-model#keeping-up-with-the-companies).

### Reminders job

It takes open things to do with a reminder due, up to 100 a run, and sends each to the chat it began in or the owner's own chat ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)). After downtime the overdue ones go on the next minute, and one more than 10 minutes late says when it was due.

While the family is talking in a chat, reminders, nudges, follow-ups, plan heads-ups and the note for one lookup wait up to two minutes so the next reply carries them. The reminders job sends any that no reply carried.

### Alerts job

It needs an admin with a Telegram id and a Telegram connection in this process. Without either, the trouble stays on Status under **Needs a look** and the job tries again the next minute. What it tells, and how often, is on [Messages](/wiki/controls/settings/messages#when-something-needs-fixing).

### Retry job

It first sends stored replies that never went, then retries each failed or unanswered message that has retries left, a sender in this process and no lease held. A failed weekend ideas message is asked again as the weekend ideas. A message that has used its retries stays on Status under **Messages that did not go through**. The steps are in [From message to reply](/wiki/behavior/message-to-reply).

### Lookups job

It runs every 2 minutes, but by default ideas wait for the evening: those waiting since before the last 21:00 are looked up together, and each chat gets one note. An idea added on Tuesday at 15:00 is looked up on the first run after 21:00 that evening. [Lookups](/wiki/controls/settings/lookups#when) has the timing and the other choices.

A home or gift idea with no place or link is skipped in code, with no model call. A busy company, or the day's limit, stops the run and leaves the rest waiting. A lookup that fails is marked failed and is not retried by itself: press **Look it up again** on the idea.

### Weekend ideas job

It asks "what should we do this weekend?" through the chat pipeline as the admin who was added first, at `digest_level`. It is one chat turn, but the turn can call the suggestion engine and, through it, a discovery worker that searches the web ([how it is answered](/wiki/behavior/suggestions)), so it can be several model calls. Its id carries the date, so a second run the same day sends nothing, and the retry job asks again after a failed turn. It skips, and logs why, when no chat is set, there is no model key, nothing in this process can send to that chat (Telegram is not connected here), or there is no admin.

### Follow-ups job

It asks once about each confirmed plan that ended before today and started within the last 7 days. It first syncs with Google Calendar and waits when Google cannot be asked, so a canceled plan is not asked about. A plan that already has an outcome is marked asked without a message. The question goes to the plan's chat, or its maker's own chat when it began in a group.

### Evening-before check

It looks at plans for an idea, made in a chat, that start tomorrow and are unchecked, and returns before touching Google when there are none. Otherwise it syncs the calendar (and waits if Google cannot be asked), reads tomorrow's forecast (skipped without a home position), and checks rain for an outdoor or dry-weather idea and the place's saved hours against the plan's time. When all is well it says nothing, and the plan is still marked checked. A heads-up goes to the plan's chat, not its maker's private chat, with a backup idea when the engine finds one.

If nothing can send to the plan's chat when the check runs (for example Telegram is not connected), that plan is not checked. Each run looks only at tomorrow's plans, so only a catch-up on the same day can pick it up ([known limits](/wiki/reference/known-limits#a-skipped-evening-before-check-is-not-retried)).

### Models and prices check, and judgments

The daily check asks each company with a key which models the key may use (this costs no tokens), reads LiteLLM's and OpenRouter's price lists, and tells admins what matters. It then compares the last week of each kind of call with the four weeks before. [Models and prices](/wiki/controls/status/models-and-prices#what-the-daily-check-does) has the rules and shows what it read.

The judgments job asks a stronger model only about a question that code filed. It stops when `judgement_budget` is 0, when the month's spend plus US$0.05 would pass it, or when the day's limit is used up. It runs at most two price checks a run.

### Nudges job

It brings up a thing to do kept for a part of the week that code can read, such as "some Saturday morning". It reads the database and returns when nothing is due, and asks the calendar only when a nudge could go. It holds back when the calendar shows the next hour busy, but goes anyway with no calendar or one it cannot reach. The rules for each thing and each chat are in [Preferred windows and nudges](/wiki/model/tasks-and-reminders#preferred-windows-and-nudges).

### Forget-locations job and settings watch

The forget-locations job deletes a shared position after 24 hours; the assistant uses one for only 3 ([Shared location](/wiki/model/location)). The settings watch re-reads the stored settings and adds, removes or reschedules jobs to match, so a schedule you change on the page moves within 5 minutes. The log says `settings changed` and names what moved.

## An idle job calls no model

Every job reads the database and the settings first and returns when there is nothing to do. Only the retry, lookups, weekend ideas and judgments jobs can reach a model, and so can catch-up when it sends the weekend ideas. The rest word what they say from the persona's lines, in code. A job returns before a call when:

- **Retry job:** no failed message is waiting, or each has used its retries.
- **Lookups job:** web tools are off, no key serves lookups, no idea is due, or the day's [spending limit](/wiki/reference/glossary#spending-limit) is used up.
- **Weekend ideas job:** no chat is set, there is no key, nothing here can send to that chat, there is no admin, or today's weekend ideas already went.
- **Judgments job:** the setting is off, no question is due, there is no key, `judgement_budget` is 0, or the month's budget or the day's limit has no room.

## After a restart

The weekend ideas, follow-ups, evening-before and models-and-prices schedules are cron-style and live in memory. One whose time passes while the service is down is not run when it returns, because nothing is stored: that is what catch-up is for. While the service is running, a run delayed by more than an hour (6 hours for the models and prices check) is dropped. Interval jobs carry on; a run is skipped while the same job is still running, and missed runs merge into one.

Catch-up covers the gap 60 seconds after the service starts. It:

1. Deletes shared positions past their day.
2. Asks follow-ups at any hour, without waiting for 10:00.
3. Runs the evening-before check if it is on and its hour has passed, even late at night.
4. Sends the weekend ideas if today is their day and their hour has passed, even late that day.
5. Runs the models and prices check if it is on and 23 hours have passed since the last.

Repeating is safe: each plan and each day's weekend ideas are marked once.

## Seeing that a job ran

| Where | What it shows |
|---|---|
| [Messages settings](/wiki/controls/settings/messages) | Each kind sent unasked: on or off, when, how many in 30 days, the last one, and the 20 latest in full |
| [Status](/wiki/controls/status#waiting-and-worth-a-look) | Ideas waiting for a lookup, failed lookups, and messages that did not go through |
| [Status](/wiki/controls/status#needs-a-look) | Troubles the alerts job tells admins about |
| [Models and prices](/wiki/controls/status/models-and-prices) | When each source was read, what changed, and what a judgment answered |
| [Logs](/wiki/operations/diagnostics#logs) | Skips (`digest skipped: ...`), the catch-up result and settings moves; a quiet run of the forget-locations job or the settings watch is not logged |

Telegram's connection and message leases are not scheduled jobs; [The Telegram loop](/wiki/behavior/telegram-loop) and [From message to reply](/wiki/behavior/message-to-reply) cover them.

Developer docs: `src/familydb/jobs/scheduler.py`, `src/familydb/jobs/`, `src/familydb/alerts.py`, `src/familydb/model_watch.py`, `src/familydb/judgement.py`; `docs/DESIGN.md`, "Enrichment: filling in the details" and "Tasks, reminders and free-form capture".
