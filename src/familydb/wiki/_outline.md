# The guide's outline (not served)

The build-out backlog for `/wiki`. Files and folders beginning with an underscore are
never served and never searched, so this is for whoever writes the next page. A page
is added by writing its file, adding it to `_nav.json` (title, audience, depth, see
also), and updating the row here. `tests/test_wiki.py` fails if the nav and the files
disagree or a link or anchor does not resolve.

Audience: **A** admin, **G** parents and admins. Depth: **O** overview, **H** how-to,
**D** deep dive. Sources are the documents the page summarizes; the code is checked
too, since the documents can lag it. Status: written, or to do.

## Written

| Page | Aud | Depth | Status |
|---|---|---|---|
| `index` (Start here) | G | O | written |
| `overview/index` | G | O | written |
| `overview/what-it-is` | G | O | written (the exemplar for voice and structure) |
| `model/index` | G | O | written, broad |
| `behavior/index` | A | O | written, broad |
| `boundaries/index` | A | O | written, broad |
| `controls/index` | G | O | written, broad |
| `operations/index` | A | O | written, broad |
| `security/index` | A | O | written, broad |
| `reference/index`, `glossary`, `dev-docs` | G, G, A | O | written (glossary is a seed) |

## To do, by section

**overview/**: `how-its-built` (A, O: one process, its parts, threads; DESIGN 4, CLAUDE.md layout) ·
`layers-and-flow` (A, D: a request across the layers; DESIGN 4 and 5) ·
`building-blocks` (A, O: libraries and why; pyproject, DESIGN 16 "Language", "Web page stack")

**model/**: `ideas-and-places` (G, O; DESIGN 7 and 9) · `plans-and-calendar` (G, O; DESIGN 7, `calendar_sync`) ·
`tasks-and-reminders` (G, H; DESIGN 18, `task_service`, `windows`) · `memory` (G, O; MEMORY.md) ·
`family-and-roles` (A, O; DESIGN 13 and 16, `roles.py`, `family.py`) · `wishes` (G, O; WISHES.md) ·
`vera` (G, O; PERSONAS.md) · `state-and-database` (A, D: tables, migrations, what a backup holds; DESIGN 7)

**behavior/**: one page per job in the table (A, D; `jobs/scheduler.py`, DESIGN 9 and 10) ·
`telegram-loop` (A, D; `channels/telegram`, gathering, leases) · `lifecycles` (G, O: a message to a reply, a voice
note, a photo, a reminder, a kid's wish; DESIGN 5) · `suggestions` (A, D: how the engine weighs an idea; DESIGN 10)

**boundaries/**: per service, the five-page pattern (communication, setup, capabilities, security, compatibility)
for the model companies, Telegram and Google Calendar · `weather-and-maps` (A, O) · `price-lists` (A, O) ·
`host` (A, D: what the installer put on the server; INSTALL "What the installer changes", `MANIFEST`-style list)

**controls/**: one page per screen in the table (G, O) · `settings` (A, H: every section, every setting, its default;
`fields.py`, `config.py`) · `telegram` (G, O: commands and buttons; `commands.py`, `buttons.py`) ·
`command-line` (A, H; README commands) · `status-page` (A, O: reading health, cost and what changed)

**operations/**: `install` (A, H; INSTALL) · `configuration` (A, D: every `.env` key) · `backup-and-restore` (A, H) ·
`upgrade-and-rollback` (A, H) · `diagnostics` (A, H: `doctor`) · `troubleshooting` (A, H: symptom table;
RUNBOOK 13, INSTALL troubleshooting) · `recovery` (A, H: locked out, forgotten password) · `cost` (A, H:
`debug cost`, the limit, what to turn down; DESIGN 14) · `hardening-and-uninstall` (A, H)

**security/**: `model` (A, D: trust and threat model; DESIGN 13) · `passwords-and-sessions` (A, D) ·
`data-and-privacy` (A, D: what is stored, how long, what leaves) · `kids-and-the-workings` (A, O: DESIGN 16)

**reference/**: `tasks` ("How do I…?" index) · `settings-reference` · `telegram-reference` · `env-reference`;
grow the glossary as pages land

## Keeping it true

A change to a setting, job, tool, role, page or command updates the page that names it,
in the same change. When pages exist for them, tests should pin the set of settings, jobs
and tools to the pages that name them, as the screen-time guide does for its config keys
and jobs.
