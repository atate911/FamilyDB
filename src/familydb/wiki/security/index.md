# Security and trust

Who may do what, what is guarded, and what an admin should know before opening the
page to the internet. This page is the overview; the reasons are in
`docs/DESIGN.md` section 13 and the family's own decisions in section 16.

## Who may do what

There are three roles and one table of permissions (`familydb/roles.py`). The page
asks what a person may do, never which role they have, so a limit for kids is one
change to that table.

| Permission | What it allows | Admin | Parent | Kid |
|---|---|---|---|---|
| sign in | Sign in, and read the ideas and plans | yes | yes | yes |
| chat | Talk to the bot on the page | yes | yes | yes |
| change | Add and change ideas, plans and things to do | yes | yes | no |
| own tasks | Tick off or change your own things to do | yes | yes | yes |
| browse | The household's pages: what she remembers, Status, everybody's things to do, this guide | yes | yes | no |
| wish | Keep your own wish lists | yes | yes | yes |
| decide | See every kid's wishes and answer them | yes | yes | no |
| manage | Settings, setup and the family list | yes | no | no |

A kid's messages are limited to a number a day that the family sets (none by
default), counted only when a model answered, so a command or a button costs her
nothing.

## Signing in

- Each person signs in as themselves, with their own password. It is kept only as a hash (scrypt), apart from the member record, so a hash never reaches a prompt. A password is at least twelve characters.
- An admin gives everybody else a starting password, made up and shown once. That person can go nowhere but the page to choose their own until they have.
- Until an admin has a password of their own, the page takes one the family shares (the installer's, or one chosen on the Settings page), and a session opened with it may do everything. The first admin's own password ends that for everyone, and the last admin who can sign in can never be removed, so it does not quietly come back.
- Wrong guesses are counted per address and locked out after five for fifteen minutes, and across the whole site past fifty, so a page on the open internet is not worth guessing at.
- A session carries a mark of the password it was opened with. A new password, switching someone off, taking their password away, or a role that may not sign in, signs that person out everywhere. "Sign everyone out" replaces the session key.
- Behind a proxy a password is required however the page is bound, and the page refuses to start bound to the network with no password unless that is waived on purpose.

## What is guarded

- **The family list is not a tool.** The model can never change who may message the bot or who signs in; that goes through the Family page and one rules module.
- **Writes go through four doors, pinned by tests.** Idea, plan, task, memory and wish forms run the same tool the model would; the Family page goes through `familydb/family.py`; Settings through the `store.settings` whitelist; chat through the pipeline. Every form carries a CSRF token and an Origin check.
- **A key is write-only.** Stored, never drawn into a form, never written to the change log, and shown only after the password the person signed in with is typed again.
- **Nothing the family typed or a fetched page said is trusted.** Templates escape everything, links saved from chat are filtered to http and https, and fetched pages are information, never instructions. A lookup may only write to its own idea.
- **The page's scripts come only from the page itself**, with no inline script or style, and it cannot be framed.
- **Kids never see how it works**, which is a family decision held by tests: a kid is shown none of the workings, however a thing fails.

## What an admin should know

A sign-in guards a lot. Whoever holds a parent's password can add an idea, mark one
done, cancel a plan and spend the family's tokens by asking a question. Whoever holds
an admin's can also let a Telegram account talk to the bot and change the settings.
That is what the page is for, and it is why a public install needs long passwords. The
damage is visible and reversible: every change is a record in the same tables the bot
keeps, made by the same checked code, and an idea is dropped rather than deleted.

## In this section

- [The trust and threat model](/wiki/security/model): what a sign-in guards, what protects the page, what hostile text can do, and a checklist for a public install.
- [Passwords and sessions](/wiki/security/passwords-and-sessions): how sign-in, sessions and lockouts work.
- [Data and privacy](/wiki/security/data-and-privacy): what is stored, for how long, and what leaves the house.

Deeper detail: `docs/DESIGN.md` sections 13 and 16. What to do when a secret gets out is under [Running it over time](/wiki/operations#when-a-secret-gets-out).
