# FamilyDB web alpha

The browser app now supports family planning without Telegram. It shares the same database,
settings, calendar tools, and AI pipeline as the bot.

## Available workflows

- **Home** (`/home`): recent ideas, restaurant count, saved upcoming plans, and quick actions.
- **Ideas** (`/`): search and filters; add, edit, clear optional details, and archive ideas.
  Archive uses the existing `dropped` status and is reversible through the status filter.
  Changing a status is a label change; scheduling uses Make a plan, and visit ratings can be
  recorded by telling the assistant how an activity went.
- **Restaurants**: browse saved places and their enrichment details; add or edit directly.
- **Plans**: create, edit, and explicitly confirm cancellation of FamilyDB plans in Google Calendar.
  Native date/time controls use the family timezone. All-day end dates are exclusive.
- **Calendar**: month navigation, multi-day plans, and Google events created outside FamilyDB.
  Outside events are visible here and remain managed in Google Calendar. An agenda works on
  small screens. Failed live reads show a warning and fall back to saved plans.
- **Ask AI**: one shared family conversation, member attribution, saved requests and replies,
  background processing, bounded concurrency, and a Resume saved request button. Drafts remain
  visible after validation or busy errors. Messages can invoke the existing idea, planning,
  discovery, suggestion, and feedback tools.
- **Family**: add family members from the browser, including the first member needed for AI
  conversations. Edit names and roles, deactivate members, and restore profiles without replacing
  their identity, history, or channel connection. Duplicate names and stale edits are rejected.
  The last active administrator is protected; running AI work must finish before profile edits.
  Deactivation stops pending requests, and restoring a profile does not restart those requests.
  This is attribution, not individual login; Telegram connections still require server setup.
- **Settings and Status**: existing provider configuration, credentials, health, and usage pages.

## Running it

Use the existing Linux installer described in `INSTALL.md`. For an installed environment,
`familydb web --host 127.0.0.1 --port 8080` starts the web app and applies migrations, including
`0007_web.sql`. Open `/home` after signing in. Existing `/` bookmarks still open the ideas list.
Access a loopback server through an SSH tunnel or the documented TLS reverse proxy.

Ideas and restaurant forms work without an AI key or Google account. AI conversations require a
configured provider and at least one family member (add one on the Family page). Calendar writes require the Google Calendar
OAuth setup from the installation guide; a missing connection is explained on the plan form.

The standalone `familydb web` command serves browser requests and their AI work. The normal bot
service runs scheduled enrichment, automatic retries, digests, and follow-ups. Without that
service, use Resume saved request for an interrupted browser conversation. Browser-created
plans route their scheduled follow-up into the shared web conversation.

## Access and reliability

This remains a shared-password alpha. Everyone with the family password can edit data, use AI,
manage calendar plans, and access administrator settings. Selecting a name only attributes a
message; it is not an individual identity or a permission boundary. Individual accounts, separate
administrator permissions, recurrence editing, and multiple calendars are not implemented.

Every new POST is behind the login gate, checks CSRF and Origin, and validates a signed token
bound to the action and browser session. Idea saves deduplicate repeated submissions and reject
stale edits. Calendar creates reuse the persisted remote event identity for an unchanged retried
submission. A materially changed event is a different intent. No write transaction stays open
during model calls or calendar network calls.

The app uses server-rendered, escaped HTML with no JavaScript dependency. The referrer policy is
`same-origin`, so browser form POSTs retain their same-origin header while cross-origin links
do not disclose page URLs. The content security policy still forbids scripts.

## Verification and remaining installation checks

Regression tests cover validation, clearing and archiving records, replayed submissions, stale
idea edits, cross-site and unauthenticated requests, calendar create/edit/cancel, native timed
and all-day forms, month boundaries, local timezone conversion, exclusive midnight endings, ongoing plans,
first-member setup, duplicate member names, persisted AI replies, interrupted-request recovery, and
escaped user content. External APIs are replaced with deterministic fakes in these tests.

The desktop and 390px mobile dashboard were visually checked in the browser, and an idea was
created through the real browser form against a separate fictional database. Live Google OAuth,
paid AI calls, Linux service startup, backups, and external HTTPS still need the installation
smoke checks in `ALPHA_READINESS.md`. No production database was used for the browser preview.

Family management also has regression coverage for profile identity and channel preservation,
last-administrator protection, stale edits, running-request guards, deactivation and restoration,
inactive-member retries, and terminal requests that must not block a new conversation.
Deactivating a profile does not revoke the shared website password.
