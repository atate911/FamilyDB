# Troubleshooting

Find the symptom in the tables below; each row says what it usually means and how to fix it. Run the commands in the first section before you guess.

## Start here

The doctor checks the install end to end and prints a fix under each finding: `✗` must be fixed, `!` is worth a look.

```bash
sudo /opt/familydb/scripts/maintain.sh check
sudo /opt/familydb/scripts/maintain.sh status
sudo journalctl -u familydb -n 100 --no-pager
```

On Docker the log is `sudo docker compose --project-directory /opt/familydb logs --tail 100 bot`; `maintain.sh logs` follows either. On Docker the doctor runs in a fresh container, so "service" is skipped and "web page answering" can warn while the page is up: use `docker compose ps`.

**To restart, run `sudo /opt/familydb/scripts/maintain.sh restart`.** It works on both installs, and "restart" below means this.

`familydb doctor --online` ([The command line](/wiki/controls/command-line#how-to-run-it)) also asks Telegram whether the token is live. On Status, **Needs a look** lists what only an admin can fix and **Messages that did not go through** lists failed messages; press **Check again** to refresh it. Some strings below are log lines and some appear on Status or Connections; each row says which.

## The page will not open

| You see | It usually means | Do this |
|---|---|---|
| The browser waits, then times out | The page's ports are closed, nearly always by the hosting provider's own firewall | Allow incoming TCP on 80 and on the page's port (443 unless moved) in the provider's panel. On a virtualenv install, then run `sudo /opt/familydb/scripts/maintain.sh https` for a real certificate. On Docker that command is refused until `.env` has `WEB_DOMAIN`, `WEB_TRUST_PROXY=true` and `COMPOSE_PROFILES=tls` ([The server](/wiki/operations/host#https-caddy)). If `curl -skI https://127.0.0.1 -H 'Host: <server address>'` answers on the server, the server is fine |
| A 502 from Caddy | Caddy answers, but FamilyDB behind it is not serving | `sudo journalctl -u familydb -n 40 \| grep -E 'not serving\|could not serve'` names why |
| Log: "the web page is not serving" | The page is on and faces the network, but no password rule is met: nobody has their own and there is no shared password of 12 or more characters | Choose a password for an admin (`sudo /opt/familydb/scripts/maintain.sh password "<name>"`), or set `WEB_PASSWORD` of 12 or more characters in `.env`, then restart. The bot keeps running without a page |
| Log: "could not serve the web page" with "Address already in use" | Another program, or a second copy of FamilyDB, has the port | `sudo ss -ltnp \| grep ':8080'` (or your `WEB_PORT`), stop what holds it, or `sudo /opt/familydb/scripts/maintain.sh port random`. On Docker a busy host port shows when you start the containers ("port is already allocated"), not in the bot's log |
| No page and no log line; the doctor says the page is "off" | `WEB_ENABLED` is false | Set `WEB_ENABLED=true` in `.env` and restart |
| It opens on the server only | The page listens on this machine, and Caddy reaches it. On Docker the compose `ports` line starts `127.0.0.1:` | Use the HTTPS address, or an SSH tunnel if you installed with `--local-only` ([Install and first run](/wiki/operations/install#choices-you-can-make)) |

## Somebody cannot sign in

[Recovery](/wiki/operations/recovery) covers forgotten passwords, the shared password, "Too many tries" and a lost phone. What else shows up:

| You see | It usually means | Do this |
|---|---|---|
| "That request did not come from this page." | The address in the browser does not match what the server saw, usually http against https. Behind a proxy, `WEB_TRUST_PROXY` is off | The doctor warns "web page behind a proxy". Set `WEB_TRUST_PROXY=true` in `.env` and restart |
| "That form was too old to use. Here it is again." | The page was open from before a sign-out | Send the form again |
| Asked for the password again and again | A changed password, or "Sign everyone out", ends open sessions on purpose. If it keeps happening, the cookie does not come back: `data/` is not writable, so the signing key changes at each start (`ls -l /opt/familydb/data/web_secret`), or over HTTPS `WEB_TRUST_PROXY` is off | Sign in once more. Otherwise fix the owner of `data/`, set `WEB_SECRET_KEY` (also needed with more than one process), or turn the proxy setting on, then restart |

## The assistant does not answer, or answers wrongly

The wording is Vera's as shipped. The family can reword it on Personality, and with no persona a plainer line says the same.

| You see | It usually means | Do this |
|---|---|---|
| No reply at all | The bot is not running, or Telegram is not connected (the page's own chat still works without Telegram) | Systemd: `sudo systemctl status familydb`. Docker: `sudo docker compose --project-directory /opt/familydb ps`. Then restart |
| "Sorry, I only talk to the family … your id here is …" | The sender is not on the family list for that channel | Add them from "Waiting to be let in" on the Family page |
| "I can't answer yet: nobody has given me a model key." | No key for any model company. That message is not retried | Add one on [AI model](/wiki/controls/settings/ai-model#keys), then ask again |
| "Got it, but I can't get to it right now. I'll try again shortly." | The call failed in a way worth retrying: the company is busy or rate limiting, the server cannot reach it, or something unexpected broke | By default the retry job tries every 5 minutes, 3 times, and the family hears nothing after the first line ([Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)). When Status shows as many tries as the limit, retrying has ended though it still says "will try again". Check the log, the network (`ping -c1 1.1.1.1`) and the clock (`date -u`; a day off breaks certificates; `sudo timedatectl set-ntp true`), then ask the person to send it again, or use `familydb db retry-failed --reset` |
| "Got it, but I can't reach my model at the moment. Someone should look at the logs." | The company refused for a reason retrying will not fix: a wrong or revoked key, no credit, a refused request. The message was given up | Needs a look usually names it. Fix it, then ask again, or use `--reset` as above |
| "I've reached today's spending limit" | The day's estimate, with calls still in flight, reached the limit. The message that hit it is not retried | Raise it on [Spending](/wiki/controls/settings/spending#the-daily-limit) if the day was genuine, or wait for midnight in home time, then ask again. See [Cost](/wiki/operations/cost) |
| "I went around in circles on that one", or "That part is saved…" | The turn used all its steps (8 by default). The second wording means the steps or the day's limit ran out after something was already written | Ask more simply, or raise "Steps per message" on Spending. Check what is saved before asking again |
| An answer cut short | The model hit the output limit; Status lists it under Worth a look | Raise "Longest answer (tokens)" on Spending |
| A voice note or photo is not read | Hearing needs an OpenAI or Gemini key, the setting is off, or the file was too long or large. It is not kept, so not retried | [Voice notes and photos](/wiki/controls/settings/ai-model#voice-notes-and-photos); ask for it again or typed |

**`--reset` re-arms every failed message, including ones given up on purpose.** Old messages can be answered late and billed again, so check **Messages that did not go through** on Status first.

A kid is given gentler words ("That's N messages today", "That's all our chatting for today" are the two limits on Spending) and is not told about money or how the bot works, so look in the log. To see why one answer went wrong, open it under [Recent activity](/wiki/controls/status/activity).

### What admins are told on Telegram

Each is also a **Needs a look** row on Status, the only place if no admin has a Telegram id or "Tell admins on Telegram" is off.

| Telegram line, and the Status title | Do this |
|---|---|
| "… says the account is out of credit" ("is out of credit") | Add credit with the model company, or save a second company's key |
| "… refused my key" ("refused its key") | Paste a good key on [AI model](/wiki/controls/settings/ai-model#keys) |
| "Today's spending limit … so I'm not answering anyone" ("The day's spending limit was used up") | Raise the limit; the row stays until a call goes through that day |
| "… keeps refusing what I send it" ("is refusing requests") | Told only once it has happened twice. Try another model, or upgrade FamilyDB |
| "A model I use is going away" ("A model in use is going, or has gone") | Choose another on AI model; [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models) has the rest |

## Telegram is silent, or its buttons do nothing

| You see | It usually means | Do this |
|---|---|---|
| Status or Connections: "the token was refused by Telegram" (the log says "Telegram refused the bot token") | The token is wrong or revoked. It is not retried until it changes | Paste the current one on [Connections](/wiki/controls/settings/connections#telegram); it takes effect within seconds |
| Status or Connections: "cannot reach Telegram; trying again" (the log says "cannot reach Telegram … trying again shortly") | The server cannot get out; it tries every 30 seconds | Check the network and DNS |
| Nothing from a group | "Answer only when mentioned" is on, or Telegram's privacy setting for bots is, so the bot sees only mentions and replies | The Connections card says which. For privacy send BotFather `/setprivacy`, choose Disable, then remove the bot from the group and add it again |
| The log says "delivery pending for message …" | The send failed; the reply is stored and the retry job sends it again | Fix the connection if it repeats |
| A reply arrived twice | Telegram has no idempotency key, so delivery is at least once | Nothing. A resend never runs the model or repeats a calendar change |
| "That button no longer works.", "That's already dealt with.", "That didn't go through." | The thing is gone, was already done, or the action was refused (the log has "tap … did not go through") | Say it in words |
| "Only the family can use these." | The person who tapped is not on the list | Add them on the Family page |

## Calendar problems

| You see | It usually means | Do this |
|---|---|---|
| "A calendar is named but not connected yet", or the doctor's "no key at …" | `data/google_key.json` is missing. Backups do not hold it | Make a new key and connect again on Connections |
| "Google Calendar stopped letting the bot in" | Google refuses the key: it or its service account was deleted. This alert comes only from a refused key | Make a new key and connect again; the row clears when Google answers |
| On connecting: "cannot find that calendar", "can see that calendar but not change it", or "not turned on in the project" | The id is wrong or the calendar is not shared with the service account; it was shared read-only; or the Calendar API is off | Share it with "Make changes to events", or turn the API on and wait a minute |
| Plans stop reaching the calendar and nothing is flagged | It was unshared or made read-only after connecting, which raises no alert | `familydb google events` shows what the bot sees; share it again with "Make changes to events" |
| An event added on a phone is not on the page | The page keeps Google's answer for up to a minute | Wait, then reload |

With no calendar connected, plans stay inside FamilyDB: a choice, not a fault. More: [Connections](/wiki/controls/settings/connections#google-calendar).

## Lookups are not happening

Lookups run only in the long-running service. A new idea waits, by default, for the evening lookup at 21:00.

| You see | It usually means | Do this |
|---|---|---|
| Doctor "web lookups: off" | The setting is off | Turn on "Look ideas up on the web" on [Lookups](/wiki/controls/settings/lookups#looking-ideas-up) |
| Ideas stay "waiting to be looked up" | It is before the evening hour, or there is no key for the company that does lookups, or the day's limit is used up | Press **Look them up now** on Status, or send `/lookup` (parents and admins) |
| A lookup failed | The note on the idea says why | Open the idea and press **Look it up again** |

## Reminders or the weekend digest do not arrive

Reminders, follow-ups and plan checks ask no model, so a model outage does not stop them. A plan check says nothing when all is well.

| You see | It usually means | Do this |
|---|---|---|
| The wrong hour | The time zone: a rented server is usually on UTC | [General](/wiki/controls/settings/general#where-home-is) |
| A reminder waits a couple of minutes | Someone is chatting in that chat, so it rides the next reply | It goes after a hold of about two minutes |
| The digest never comes | With no chat set the job is not scheduled (doctor: "no chat id") | Choose the chat on [Messages](/wiki/controls/settings/messages#weekend-ideas) |
| The digest was skipped | The log says "digest skipped: there is no model key yet", "nothing here can send to …" or "no active admin to ask as", or "digest already sent today" | Fix that. A Telegram group needs the bot in it and able to see its messages |

## Costs are higher than expected

See [Cost](/wiki/operations/cost).

## The server

| You see | It usually means | Do this |
|---|---|---|
| `failed`, or "started and then stopped" | A value the settings will not take, or a file it cannot write | The doctor names it. The usual three: `familydb` does not own `data/` and `.env`, the checkout is under `/home`, a bad value in `.env` |
| "a setting will not do" | A value in `.env` has the wrong type, such as `WEB_PORT=eighty` (quote any value with a space or `#`), or a value saved on the page no longer validates ("stored settings are not usable") | The message names the setting; fix or empty it, then restart |
| `Permission denied: '.env'` | You ran a command as yourself; `.env` belongs to `familydb` | Run it as that user from `/opt/familydb` |
| "cannot write", or "attempt to write a readonly database" | `data/` belongs to someone else, often after a by-hand restore | `sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env`, then restart. On Docker use `1000:1000` and no `.env` |
| "database is locked" | More than one `familydb run` is writing | Run one; the command line beside it is fine |
| "No space left on device" or `Killed` | The disk is full, or the kernel ran out of memory, usually while the virtualenv is built on a 512 MB or 1 GB machine | [The server](/wiki/operations/host#disk-and-memory) has the fixes, including swap; the nightly backup prune and a shorter `--keep-days` free the most |
| "Could not get lock /var/lib/dpkg/lock-frontend" | Another program is installing packages | `sudo fuser -v /var/lib/dpkg/lock-frontend`, wait a minute, run the installer again. After an interrupted install, `sudo dpkg --configure -a` first. Do not delete the lock file |

A failed install is safe to repeat: paste the same block again (its log is `/var/log/familydb-bootstrap.log`). See also [Diagnostics](/wiki/operations/diagnostics) and [Upgrade and rollback](/wiki/operations/upgrade-and-rollback).

Developer docs: `RUNBOOK.md`, "Troubleshooting"; `docs/INSTALL.md`, "Troubleshooting"; `familydb/doctor.py` (the checks); `familydb/alerts.py` and `familydb/web/status.py` (`attention`, `health`); `familydb/voice.py` (`EVENTS`).
