# Alpha readiness after the September 2026 review

The reviewed defects have fixes and regression coverage in this working tree. This is ready
for installation testing with a disposable calendar. Real Telegram, Google OAuth, paid AI
requests, and a Linux installation still need an end-to-end smoke test before family alpha.

## Found in the pre-VPS review (September 23)

### Follow-up correctness fixes

- A spending-limit interruption after successful writes now returns a local summary of the
  completed operations and their record numbers. The message is completed rather than retried;
  any remaining work must be requested separately after reviewing what was saved.
- Before each paid request, the budget check and a hold on that request's estimated cost happen
  in one short write transaction, so two processes cannot spend the same remaining allowance.
  Nothing is locked while the request is on the network, so a slow lookup does not hold up
  chat; every vendor client times out after two minutes. A hold left by a crash stops counting
  after 30 minutes. One accounted request may cross the estimated limit; unknown charges from
  timeouts, vendor retries, or a crash before accounting remain outside that guarantee. This is
  not a provider-enforced billing cap. (The first version held an OS lock over every request,
  which made all paid calls wait on each other; it was replaced.)
- Browser calendar forms reuse a durable operation identity after a restart or lost response,
  and a form drawn again after a lost reply from Google takes over the unfinished attempt
  rather than creating a second event. Other forms retain the in-memory double-submit guard.
- Idea edits carry a content revision that is checked inside the update transaction, including
  when two saves arrive in the same second. Older forms must be reloaded.
- Changing the timezone rebuilds the application clock immediately, without a restart.
- Windows startup no longer invokes POSIX ownership APIs. Linux keeps its existing permission
  hardening; Windows relies on the account's inherited filesystem ACLs, not chmod guarantees.

These changes have local regression tests. Live default-model quality, Google consent, and
Telegram onboarding still require the live-account checklist below.

A second review, before installing on a VPS, found these and fixed them:

- **Nobody could sign in behind the HTTPS proxy.** Waitress strips forwarding headers from a
  peer it has not been told to trust, before Flask sees them, so behind Caddy every request
  looked like plain HTTP from the proxy: the Origin check refused every sign-in, and five wrong
  guesses from anyone locked the whole family out. The server is now told which proxy to trust,
  and the tests go through the real server. Checked in Chromium through Caddy and nginx.
- **A fresh install got the old code, and an upgrade could go backwards.** The `v0.1.0` tag
  predated the web page and these fixes. While CHANGELOG.md says a version is in progress,
  installs follow the default branch; an upgrade never moves to anything older.
- **The database was readable by every account on the machine**, keys typed on the page
  included. Everything is owner-only now, and the systemd unit is sandboxed.
- **Behind a proxy on the loopback, the page could run with no password.** It cannot now.
- **Strangers could hold sign-in shut** with the site-wide guess ceiling; a browser that has
  signed in before is spared it.
- **Nothing capped what the models could cost.** A daily spending limit is checked before
  every call; the default model is now GPT-6 Luna, the cheapest capable one.
- **Setup meant editing a file and restarting.** It is done on the page, Google Calendar and
  the Telegram token included, and the installer asks one question.

## How these fixes arrived

This review and its fixes came as PR #2, one commit that also rebuilt the web page. The fixes
were taken into the branch that replaced PRs #1 and #2 one theme per commit, each with its regression tests
(`tests/test_alpha_regressions.py`), and the web page was rebuilt on the existing one instead of
replaced. Where the port differs from PR #2:

- **What a request carries** follows the model by what it is rather than a hand-made list, so a
  Fable chat model keeps its effort setting; the fast web tools go to the models that run them
  rather than to none; and the server-side refusal fallback, which PR #2 still sent to the Haiku
  lookup model, now goes only to the models with a classifier that can refuse.
- **The calendar sync** wrote Google's spelling of a time back to each plan, with seconds, where
  plans are stored to the minute, so every read of the calendar rewrote every upcoming plan. It
  writes the stored spelling now, a read that finds nothing changed writes nothing, and reading
  one weekend refreshes only that weekend's plans.
- **Scheduling backups** removes the older schedule from the service account's crontab itself.
- **Sign-in from a real browser** was impossible before either PR: under `Referrer-Policy:
  no-referrer` a browser posts every form with `Origin: null`, which the page refuses. PR #2
  changed the header without saying why; this branch says why and tests both halves.
- **Not taken:** migration `0007_web.sql`, which held PR #2's form tokens. The rebuilt page keeps
  those in memory. Migration `0006_recovery.sql` is PR #2's file byte for byte, so a database that
  ran PR #2 is consistent with this branch; the next migration should be numbered `0008` so that such a
  database never mistakes it for one already applied.
- **Not verified here:** the Gemini lookup model `gemini-3.8-flash`, which PR #2 chose from
  Google's documentation. That documentation could not be reached from where the port was done;
  check the name against your own account before relying on it.

## Changes

| Review finding | Implemented change |
|---|---|
| Discovery skipped under production wiring | Workers use the configured provider without requiring a test API injection. |
| Discovery cache reused unrelated answers | Cache identity includes date, question, constraints and home location; settings changes clear it. |
| Unsupported worker requests | Haiku requests omit adaptive thinking and effort, and use basic web tool versions. Gemini workers default to `gemini-3.1-flash-lite` (Gemini 3, which searches alongside our tools), include server tool context circulation, and reject unsupported older model combinations before making a request. |
| Duplicate calendar creation after a lost response | Persist a client-generated Google event ID before insertion; reconcile that ID on retry and persist the local result atomically. Identical event creation within one inbound message reuses the operation. |
| Received messages stranded on restart | Retry unfinished inbound records using renewable database claims. A dead claim expires after five minutes; the next retry job can recover it. Relative dates retain the original message's time context. |
| Replies, digests and follow-ups lost on send failure | Persist outgoing messages and mark delivery only after sending succeeds. Retry delivery separately from AI processing and calendar writes. |
| All-day commitments ignored | Busy all-day events block suggestions; transparent informational events do not. Suggestion results include commitment titles. |
| Activity hours/duration mismatch | Check the longest continuous intersection of opening hours and free blocks, using full visit duration and estimated round-trip travel. |
| Workers could mutate unrelated records | Dispatch enforces the tools declared for that turn, and enrichment writes are restricted to the assigned idea. |
| Calendar views stale and existing plans hard to find | Plans page reads live Google events, including externally created events, with a visible cached-data warning on failure. Calendar reads return plan IDs. `search_plans` finds existing plans after conversation history expires. Google edits/cancellations are reconciled before relevant edits and follow-ups. |
| “Would not repeat” feedback ignored | Suggestions honor the latest explicit repeat preference; a later explicit positive preference can override it. |
| Unsafe backup fallback / broken Docker maintenance | Online backup failure stops the operation instead of copying a WAL database. Docker mounts the backup directory; restore validates the backup first and preserves container ownership. Scheduled backups invoke the maintenance script for either installation type. Pruning happens only after a successful backup. Purge also uses SQLite's backup API. |
| Telegram token changes appeared live | Settings UI and setup documentation explicitly require restarting after adding, changing or clearing the Telegram token. |

Migration `0006_recovery.sql` adds calendar-operation records, message claims, and delivery
acknowledgements. Existing historical outgoing messages are considered delivered during the
migration, so upgrading does not resend old conversations. Fresh outgoing messages are queued.

## Verification

- Full local suite: **353 passed, 4 skipped** on Windows/Python 3.12 when the review was
  ported; the suite is larger now, and CI runs it on Linux with Python 3.11 and 3.12.
- Ruff lint and formatting, shell syntax, and Git whitespace checks pass. The source archive
  and wheel build successfully; the wheel includes the new migration and recovery modules.
- Includes **23 added regression cases**, covering interrupted processing, lost calendar responses,
  expired and competing claims, failed notification delivery, worker boundaries, provider request
  compatibility, calendar changes, suggestion accuracy, and migration of old outgoing messages.
- Four shell integration cases exercise the actual backup function with mocked privilege and
  Docker commands: successful backups preserve committed WAL data, and failures leave no backup
  falsely reported as usable. They do not substitute for testing a real Docker daemon.
- Linux CI includes Docker backup/restore and ownership checks, and it runs on every push.
- The non-live test suite blocks outbound network connections while allowing local web-server
  tests. No real credentials or paid integration validation were used.

## Installation and live alpha gate

1. Install the updated code on the chosen Linux server with `scripts/bootstrap.sh`, giving the
   page's domain, and use a dedicated test calendar. Sign in to the page and follow its
   "Finish setting up" list; run `familydb doctor` and address its findings.
2. Paste an OpenAI key on the settings page and check that saving `gpt-6-luna` is accepted (the
   page asks OpenAI whether the model exists). Verify actual capture, enrichment, discovery and
   scheduling on it, and that `/status` shows today's spend. Set a spending limit on the key in
   OpenAI's console too. If using Gemini for lookups, check `gemini-3.8-flash` the same way.
3. Paste the Telegram token on the settings page; within seconds `/status` should say
   "connected as @…" with no restart. Add each person's Telegram id on the Family page. Check two
   users in private chat and the intended group.
4. Connect Google Calendar from the settings page: paste the Desktop-app client JSON, open the
   consent link, paste back the address Google sends the browser to. This flow is new and
   untried against Google; if it fails, `familydb google auth` on a laptop still works.
5. Create, move and cancel a test event. Edit one directly in Google, and verify the plans page
   and a subsequent chat edit reflect it. Test a busy all-day trip and a transparent birthday.
6. Restart during processing, temporarily interrupt delivery, and verify eventual recovery.
   Restore a fresh backup onto a separate test installation and check recent records.
7. Reboot the Linux host and verify startup, persistent data, logs, dashboard access, and backups.
   Keep the dashboard private or behind correctly configured HTTPS. Keep an off-host backup and
   a separate recovery copy of `.env` and Google credentials.
8. With something on the test calendar this afternoon, ask "I'm bored, what can we do now?",
   "anything for tonight?" and "what about Saturday morning?". Check the free times it reports
   leave out the event and the part of today that has gone, and that an option says when it can
   start ("can go 16:10-17:55 today"). Ask two differently worded weekend questions with
   discovery on and check `/status` shows one discovery search, not two. Within a couple of
   hours of sunset, ask "anything outdoors tonight?": an outdoor idea that needs longer than
   the daylight left should be offered as one in the dark, which shows the real forecast's
   sunrise and sunset were read.
9. Add a restaurant idea and watch its lookup: `/status` should show one fewer call per lookup
   than before (the turn ends at `save_place`), and a "home" idea with no place is skipped with
   no call at all. Send a web chat question while a lookup runs: it must not wait for it.
10. On a phone away from home, share your location with the bot on Telegram (paperclip, then Location), then ask "what's open near here?": options should be measured from there, and the reply should say so. Share a live location instead and move a few streets: asking again should name where you are now, not where you started, with no second "Got it", and none when you stop sharing. On the web page's chat over HTTPS, tick "Send where I am", allow the location when the browser asks, and ask the same: no place should need typing. Untick it and send "thanks": no position should be kept for that message.
11. Set a reminder a few minutes ahead, stop the service past its time, start it again: the
    reminder arrives once and says when it was due. Set another for a minute ahead and keep
    chatting in that chat: the next reply should carry it rather than a separate message, with
    its buttons under the reply. In the family group, tap "In an hour" on a reminder: everyone
    should see who snoozed it and until when, with the buttons gone, and it should come back an
    hour later; tap "✓ Done" on that one and it should not come back. Have someone not on the
    family list tap one: they should be told only the family can, and nothing should change.
    The day after a plan, tap an answer under "how was it?" and check the idea's page.
    Ask for something every day at a time a few minutes ahead: it should come, and come again
    the next day at the same time; tick it off and it should still come the day after.
    Say "Grandma would love a gardening apron", then set Grandma's birthday with a reminder a
    few minutes ahead: the reminder should list the apron, and the apron's page should say it
    is "not one place to look up", with no lookup on the status page's costs.
    On Telegram, type "/": today, week, tasks and now should be offered. Each should answer at
    once with no model call on the status page: /today and /week with what Google shows,
    /tasks with this chat's tasks only (none from a private chat in the group), and /now with
    what could start in the next few hours. From somebody not on the list, /today should get
    the stranger's line.
    On a Wednesday, say "one of these Thursday evenings I need to fix the bike light": the
    answer should say it comes up on a free Thursday evening, and the tasks page should say so
    too. On Thursday it should come up once, with buttons, from 18:00 if the calendar is clear
    then, or once an hour is free after whatever is on; and not again that day.
12. On `/settings/personality`, rewrite one of her lines and add a sentence to "About the
    family"; the next reminder or follow-up should use the new line, and the next answer should
    know the sentence. Give her another name: "what's your name?" should get it, in the chat and
    on Telegram, and within a few seconds the bot's name and description in Telegram should be
    hers. Rewrite her description and add a line under "Anything to add", then choose no persona:
    the replies should be plain, her lines and your rewrites of them included, and the Telegram
    contact called FamilyDB. Choose her again: the name, the rewrite, the notes and the lines
    should all be back. Choose Vera in brief: the list should show her at about 740 tokens a
    message before your notes, and a few everyday requests should be answered as well as
    before; choosing Vera as first written again brings your rewrite of her back.
13. With the chosen model's key in the environment, run `uv run python -m evals` (it spends at
    most $0.50, and the one call that crosses it, unless `--budget` says otherwise) and read what failed before the family does.

After a week of family use, read `/status` and `familydb debug cost` by kind before changing
anything for cost: at `gpt-6-luna` prices the chat prefix is about $0.0006 a message and each web
search $0.01, so lookups and discovery, not chat, are where the money goes.

## Intentional limits

Telegram delivery is **at least once**: Telegram supplies no idempotency key, so a lost response
after a successful send can duplicate a notification. Retrying that notification does not rerun
the model or repeat calendar writes. Split long replies can similarly repeat already-sent chunks.

Calendar creation deduplicates the same normalized event intent within an inbound message.
A separate new user message can intentionally create another event. Significantly changed event
arguments represent a different intent; the operation log is not a semantic duplicate detector.

Suggestion availability uses the calendar's real free stretches in minutes, but travel is a
straight-line estimate, from home unless someone shared their location in the last three hours
or named where they are, and the forecast is per day, not per hour. A shared location's name and
coordinates go to the model provider with the message; the family chose that. It does not establish actual reservations or ticket availability.

The daily spending limit is an estimate from a price table checked by hand in September 2026,
not the bill. The model IDs `gpt-6-luna` and `gemini-3.8-flash` were taken from published
documentation that could not be opened from where this was built; the settings page's model
check is the first live confirmation.

The dashboard still uses a shared administrator password. Do not give that password to someone
who should not manage settings or reveal credentials. Separate viewer/admin web roles, recurring
event management, multi-calendar availability and richer family profiles remain later product work.

Provider compatibility was checked against the official
[Anthropic thinking documentation](https://platform.claude.com/docs/en/build-with-claude/extended-thinking),
[basic web-search documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool),
[web-fetch documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool), and
[Gemini tool-combination documentation](https://ai.google.dev/gemini-api/docs/generate-content/tool-combination).
Live account availability and behavior remain part of the installation test.
