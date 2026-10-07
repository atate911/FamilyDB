# Developer docs

This guide is for the people who use and run FamilyDB. The repository's own documents are for whoever changes the code, and where they disagree with the guide, they win. They are not served on the web page; read them in a checkout, or on the server under `/opt/familydb`.

The guide summarizes and links. Exact commands and the reasons behind a decision stay in the developer documents, so there is one source of truth for each.

## Reading the badges

The badge at the top of each page says who it is for and how deep it goes.

| Badge | Meaning |
|---|---|
| For admins | The person who runs the server |
| For parents and admins | Anyone who uses the web page and Telegram day to day |
| Overview | What it is and why, with links to the detail |
| How-to | Steps to do one thing, with what you should see |
| Deep dive | How it works inside, for an admin who wants the mechanism |

## Where to look

| Document | What it covers | This guide |
|---|---|---|
| `README.md` | What works today, the commands, the repository layout | [Start here](/wiki) |
| `CLAUDE.md` | The module-by-module map and the rules that keep it working (cost, the prompt cache, security, delivery), for whoever changes the code | (changing the code) |
| `docs/DESIGN.md` | Architecture, the message pipeline, tools, the data model, the suggestion engine, security, cost, and under "Decisions" the choices the family made and why | [About FamilyDB](/wiki/overview), [The pieces](/wiki/model), [Security and trust](/wiki/security) |
| `docs/AI_CALLS.md` | How every model call decides, sees, acts and is trusted | [Outside services](/wiki/boundaries) |
| `docs/MEMORY.md` | How household memory is noticed, kept, chosen and forgotten, and its token rules | [How memory works](/wiki/model/memory) |
| `docs/PERSONAS.md` | The persona layer: Vera, her lines, and what the family may rewrite | [Vera](/wiki/model/vera) |
| `docs/WISHES.md` | The kids' wish lists and their rules | [Wish-list rules](/wiki/model/wishes) |
| `docs/STYLE.md` | How the web page looks and why | [Using FamilyDB](/wiki/controls) |
| `docs/INSTALL.md` | A server from nothing: the installer, HTTPS, the firewall, troubleshooting | [Install and first run](/wiki/operations/install) |
| `RUNBOOK.md` | Running it: backups, upgrades, settings, looking after the server, and the checks to make against live accounts | [Running the server](/wiki/operations) |
| `docs/PRODUCT_EXAMPLES.md` | Illustrative requests that describe the intended experience; not a feature list | [What it is and is not](/wiki/overview/what-it-is) |
| `CHANGELOG.md` | What changed in each release, and the known limits | [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) |
| `evals/` | The family's own requests run against a real model, graded by code | (changing a prompt or a model) |
| `scripts/` and `deploy/` | The installer, `maintain.sh`, the uninstaller, and the service and proxy files | [The server](/wiki/operations/host) |
