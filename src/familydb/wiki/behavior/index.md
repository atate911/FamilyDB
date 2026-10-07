# What it does on its own

Most of FamilyDB happens when someone sends a message. A smaller part happens
without being asked: reminders arrive, ideas get looked up, the weekend's options
are posted. This section is about that part, and about the path a message takes
when one does arrive.

## The rule that governs every job

A job that runs on a schedule reads the database and the settings first, and
returns **without calling a model** when there is nothing to do. A test enforces
it. Reminders, follow-ups, the evening-before check, nudges and Telegram's
commands never call a model at all; they word what they say from the persona's
lines by code. So an idle FamilyDB costs nothing.

## The jobs

Each job's schedule is described once, in `jobs/scheduler.py`, and follows the
settings (a change on the Settings page moves the schedule without a restart).
Times are the family's own clock.

| Job | When | What it does | Model call? |
|---|---|---|---|
| Reminders | every minute | Queues a due reminder and sends it once; a failed send is the retry job's | No |
| Admin alerts | every minute | Tells each admin with a Telegram id what only an admin can fix (a company out of credit, a key refused, the day's limit reached, Google shutting the bot out); once per trouble, again at most every 12 hours | No |
| Forget locations | every 10 minutes | Deletes a shared position past its day | No |
| Retry failed | every 5 minutes by default | Finishes a message whose turn failed or whose worker died | Only to answer a message |
| Look up new ideas | every 2 minutes by default | A worker turn per idea due. By default lookups wait for the evening (21:00), when every idea waiting is looked up and each chat gets one note | Yes, when ideas are due |
| Weekend digest | Thursday 18:00 by default | Posts the weekend's options to the family chat | Yes, one question |
| Follow-ups | daily, 10:00 by default | The day after a plan, asks how it went | No |
| Evening-before check | daily, 19:00 by default | The evening before a plan, checks the forecast and the place's hours, and speaks only if something is off | No |
| Model and price check | daily, 05:17 | Asks each company with a key which models it may use and reads two public price lists, so prices and suggestions stay current; tells admins what matters | No |
| Judgements | every 15 minutes | Weighs a change in the models only when something is due and the family has turned it on | Rarely, within a monthly budget |
| Nudges | every 15 minutes | Brings up a task kept for a part of the week when it comes round and the calendar is free; each once a week, one a day per chat | No |

There are also two housekeeping jobs: catching up after a restart, and moving the
schedule when a setting changes.

Several of these can be turned off or moved from the Settings page (Messages and
Lookups). [How you control it](/wiki/controls) says where.

## The path of a message

1. The channel hands the message to the pipeline, which checks that the sender is on the family list.
2. **It is stored first.** From then on it is worked on under a *lease*, an expiring claim that is renewed while the turn runs, so a restart strands nothing and two workers never answer the same message.
3. A voice note is heard, or a photo described, in a call of its own, and its words replace the mark; the recording or picture is never kept.
4. On Telegram, messages sent one after another are answered together, after a short pause (4 seconds by default).
5. The spending limit is checked, and for a kid so is her daily number of messages.
6. The prompt is built from the family context, the ideas, the recent conversation and the current turn, and the model calls tools until it is done. A turn may move to the other company only on its first call, before any tool has run.
7. **The reply is stored before it is sent**, and marked delivered only after the send succeeds. A send that succeeded but lost its answer can arrive twice, which is the cheaper failure: a duplicate notice, never a second model call or calendar write.

## In this section

**Still to come:** a page on each job (what it checks, its settings, how to read
it on the Status page), the Telegram loop, and the end-to-end flows (a message to a
reply, a voice note, a photo, a reminder, a kid's wish).

Deeper detail: `docs/DESIGN.md` sections 5 and 9.
