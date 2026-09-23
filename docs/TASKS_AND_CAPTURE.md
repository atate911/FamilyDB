# Tasks, reminders, and free-form ideas

Ideas are possibilities; tasks are obligations; calendar entries are commitments.
The chat layer interprets what somebody means, shared tools validate and save it,
and deterministic services handle reminders and suggestion checks.

## Using the app

- Ideas has a **Save a thought for later** box. Submit natural language and follow
  the Chat confirmation. The configured assistant organizes it using existing idea
  kinds, descriptions, people, locations and tags. Telegram accepts the same language.
  **Add an idea** remains the direct form that does not need AI.
- Original inbound messages remain linked to captured ideas and are available through
  `describe_idea` and the idea page's Original thought section. Chat instructions preserve wording and merge new context into existing
  ideas. This is still model-mediated organization; users can inspect and correct it.
- For topic-specific suggestions, the assistant passes relevant saved `idea_ids` to
  `suggest`. That scope is applied before the eight-item detailed evaluation limit;
  unrelated older activities can no longer crowd out the selected restaurant or idea.
  Calendar, weather, duration and availability rules still apply to those candidates.
- **Things to do** supports add, search, edit, done, cancelled, reopen, and snooze.
  The same operations are available in Chat through `add_task`, `list_tasks`, `update_task`.
- A deadline never implies a reminder. Flexible timing such as "some Saturday morning"
  is stored as text; it does not schedule anything. Explicit reminder times are stored
  as UTC instants. Missing times require clarification; ambiguous or nonexistent local
  times at clock changes are refused unless an unambiguous offset is supplied.
- Reminders return to their originating Telegram chat (including groups). Browser and
  console reminders go to app Chat. Assigning an owner does not change that destination.
  The app uses the existing shared household access model, not private per-person tasks.

## Running and reliability

Use `familydb run` for the service, including the scheduler. `familydb web` alone serves
pages but does not run reminder jobs. With the service running, due reminders are checked
once a minute, including overdue reminders after restart. There are no model calls for
these checks or sends. No new provider or notification configuration is needed.

Migration 0012 adds tasks, reminders and outgoing-message cancellation. Task writes and
reminder replacement are atomic. New task creation deduplicates retries by inbound message
or browser operation identity plus arguments. Browser updates check a revision. Completion
and cancellation suppress queued reminders; reopening does not restore old ones. Edits
are refused while a reminder is actively being sent, since an in-flight send cannot be recalled.

Queued messages use existing delivery claims and retries: the minute job sends a reminder once
when it queues it, and one that could not go is retried by the retry job on its interval. A
reminder queued more than ten minutes late, after downtime, says when it was due. As elsewhere in the app, external
send delivery is at least once: a provider accepting a send before the process dies can
cause a duplicate on retry. Database queuing itself is deduplicated.

## Boundaries and next steps

This supports capture, explicit recall, scoped suggestions, and timed reminders. It does
not yet implement recurring reminders, automatic free-time/location triggers, passport
stamp tracking, a learned preference profile, or live booking inventory. Those should
build on these layers with explicit provenance and user controls.

The product examples are acceptance scenarios, not requests to create real family records.
No examples are seeded into a production database.
