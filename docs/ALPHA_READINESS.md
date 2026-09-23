# Alpha readiness after the September 2026 review

The reviewed defects have fixes and regression coverage in this working tree. This is ready
for installation testing with a disposable calendar. Real Telegram, Google OAuth, paid AI
requests, and a Linux installation still need an end-to-end smoke test before family alpha.

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
| Unsupported worker requests | Haiku requests omit adaptive thinking and effort, and use basic web tool versions. Gemini workers default to `gemini-3.8-flash`, include server tool context circulation, and reject unsupported older model combinations before making a request. |
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

- Full local suite: **353 passed, 4 skipped** on Windows/Python 3.12.
- Ruff lint and formatting, shell syntax, and Git whitespace checks pass. The source archive
  and wheel build successfully; the wheel includes the new migration and recovery modules.
- Includes **23 added regression cases**, covering interrupted processing, lost calendar responses,
  expired and competing claims, failed notification delivery, worker boundaries, provider request
  compatibility, calendar changes, suggestion accuracy, and migration of old outgoing messages.
- Four shell integration cases exercise the actual backup function with mocked privilege and
  Docker commands: successful backups preserve committed WAL data, and failures leave no backup
  falsely reported as usable. They do not substitute for testing a real Docker daemon.
- Linux CI now includes Docker backup/restore and ownership checks. The updated CI workflow has
  not been run remotely as part of this local change.
- The non-live test suite blocks outbound network connections while allowing local web-server
  tests. No real credentials or paid integration validation were used.

## Installation and live alpha gate

1. Install the updated code on the chosen Linux server using a dedicated test calendar. Start
   FamilyDB so the new migration is applied; run `familydb doctor` and address its findings.
2. Configure one provider. Existing `.env` or saved settings override defaults: if using Gemini
   for lookups, replace an older worker model with a supported Gemini 3 model. Verify actual
   capture, enrichment, discovery and scheduling on the selected account/model.
3. Add the Telegram token and family members, then restart with `sudo systemctl restart familydb`
   or `docker compose restart bot`. Check two users in private chat and the intended group.
4. Create, move and cancel a test event. Edit one directly in Google, and verify the plans page
   and a subsequent chat edit reflect it. Test a busy all-day trip and a transparent birthday.
5. Restart during processing, temporarily interrupt delivery, and verify eventual recovery.
   Restore a fresh backup onto a separate test installation and check recent records.
6. Reboot the Linux host and verify startup, persistent data, logs, dashboard access, and backups.
   Keep the dashboard private or behind correctly configured HTTPS. Keep an off-host backup and
   a separate recovery copy of `.env` and Google credentials.

## Intentional limits

Telegram delivery is **at least once**: Telegram supplies no idempotency key, so a lost response
after a successful send can duplicate a notification. Retrying that notification does not rerun
the model or repeat calendar writes. Split long replies can similarly repeat already-sent chunks.

Calendar creation deduplicates the same normalized event intent within an inbound message.
A separate new user message can intentionally create another event. Significantly changed event
arguments represent a different intent; the operation log is not a semantic duplicate detector.

Suggestion availability still uses coarse morning/afternoon/evening blocks and estimated travel.
It may omit a short usable gap. It does not establish actual reservations or ticket availability.

The dashboard still uses a shared administrator password. Do not give that password to someone
who should not manage settings or reveal credentials. Separate viewer/admin web roles, recurring
event management, multi-calendar availability and richer family profiles remain later product work.

Provider compatibility was checked against the official
[Anthropic thinking documentation](https://platform.claude.com/docs/en/build-with-claude/extended-thinking),
[basic web-search documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool),
[web-fetch documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool), and
[Gemini tool-combination documentation](https://ai.google.dev/gemini-api/docs/generate-content/tool-combination).
Live account availability and behavior remain part of the installation test.
