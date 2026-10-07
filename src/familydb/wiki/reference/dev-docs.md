# Map to the developer docs

This guide is the layer for the people who use and run FamilyDB: how it works and
how to look after it. The repository's own documents are the layer for someone
changing the code. They are not served on the page; read them in a checkout, or on
the server under `/opt/familydb`.

The two are kept deliberately apart. Facts that can drift (a setting, a job's
schedule, a command) are kept correct in both, and where they overlap this guide
summarizes and links rather than copying, so there is one source of truth for
exact commands and for the reasons behind a decision.

## Where to look

| Document | What it covers | This guide |
|---|---|---|
| `README.md` | What works today, the commands, the repository layout | [Start here](/wiki) · [What it is and isn't](/wiki/overview/what-it-is) |
| `CLAUDE.md` | The module-by-module map and the rules that keep it working (cost, the prompt cache, security, delivery), for whoever changes the code | (changing the code) |
| `docs/DESIGN.md` | The design: architecture, the message pipeline, tools, data model, the suggestion engine, security, cost, and the decisions the family made and why (section 16) | [The big picture](/wiki/overview) · [The pieces](/wiki/model) · [Security and trust](/wiki/security) |
| `docs/AI_CALLS.md` | How every model call decides, sees, acts and is trusted | [What it touches](/wiki/boundaries) |
| `docs/MEMORY.md` | How household memory is noticed, kept, chosen and forgotten, and its token rules | [The pieces](/wiki/model) |
| `docs/PERSONAS.md` | The persona layer: Vera, her lines, and what the family may rewrite | [The pieces](/wiki/model) |
| `docs/WISHES.md` | The kids' wish lists and their rules | [The pieces](/wiki/model) |
| `docs/STYLE.md` | How the page looks and why | [How you control it](/wiki/controls) |
| `docs/INSTALL.md` | A server from nothing: the installer, HTTPS, the firewall, troubleshooting | [Running it over time](/wiki/operations) |
| `RUNBOOK.md` | Running it: backups, upgrades, settings, looking after the server, and the checks to make against live accounts | [Running it over time](/wiki/operations) |
| `docs/PRODUCT_EXAMPLES.md` | Illustrative requests that describe the intended experience; not a feature list | [What it is and isn't](/wiki/overview/what-it-is) |
| `CHANGELOG.md` | What changed in each release, and the known limits | (release history) |
| `evals/` | The family's own requests run against a real model, graded by code | (changing a prompt or a model) |
| `scripts/` and `deploy/` | The installer, `maintain.sh`, the uninstaller, and the service and proxy files | [Running it over time](/wiki/operations) |

*See also: [Start here](/wiki) · [Glossary](/wiki/reference/glossary).*
