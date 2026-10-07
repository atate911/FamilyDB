# Troubleshooting

Use this runbook to go from what you see to what to do: find the symptom in the tables, and each row says what it usually means and how to fix it. Run the three commands in the first section before you guess.

## Start here

The doctor checks the install end to end and prints a fix under each finding: `✗` must be fixed, `!` is worth a look.

```bash
sudo /opt/familydb/scripts/maintain.sh check
sudo /opt/familydb/scripts/maintain.sh status
sudo journalctl -u familydb -n 100 --no-pager
```

On Docker the log is `sudo docker compose --project-directory /opt/familydb logs --tail 100 bot`, and `maintain.sh logs` follows either. On Docker the doctor runs in a fresh container, so its "service" line is skipped and "web page answering" can warn while the page is up: use `docker compose ps` and the log for that.

For a deeper check run `familydb doctor --online` as [The command line](/wiki/controls/command-line#how-to-run-it) shows: it asks Telegram whether the token is live and, on Claude and Gemini, the model company whether the key works, for free.

When you can open Status, **Needs a look** lists what only an admin can fix and **Messages that did not go through** lists failed messages. Nothing on Status updates by itself: press **Check again**.

## The page will not open

| You see | It usually means | Do this |
|---|---|---|
| The browser waits, then times out | Ports 80 and 443 are closed, nearly always by the hosting provider's own firewall | Allow incoming TCP on both in the provider's panel, then `sudo /opt/familydb/scripts/maintain.sh https`. If `curl -skI https://127.0.0.1 -H 'Host: <server address>'` answers on the server, the server is fine |
| A 502 from Caddy | Caddy answers, but FamilyDB behind it is not serving | `sudo journalctl -u familydb -n 40 \| grep -E 'not serving\|could not serve'` names why |
| "the web page is not serving" in the log | The page faces the network without a password it accepts: none of 12 or more characters, no shared password chosen, nobody with their own | The doctor's "web page" line says which. The bot keeps running without a page |
| "could not serve the web page" and "Address already in use" | Another program, or a second copy of FamilyDB, has the port | `sudo ss -ltnp \| grep ':8080'`, stop what holds it, or `sudo /opt/familydb/scripts/maintain.sh port random` |
| The doctor says the web page is off | `WEB_ENABLED` is false | Set `WEB_ENABLED=true` in `.env` and restart |
| It opens on the server only | By default the page listens on this machine, and Caddy is what reaches it. On Docker the compose `ports` line starts `127.0.0.1:` | Use the HTTPS address, or an SSH tunnel if you installed with `--local-only` ([Install and first run](/wiki/operations/install#choices-you-can-make)) |

## Somebody cannot sign in

[Recovery](/wiki/operations/recovery) covers forgotten passwords, the shared password, "Too many tries" and a lost phone. What else shows up:

| You see | It usually means | Do this |
|---|---|---|
| "That request did not come from this page." | Behind a proxy, `WEB_TRUST_PROXY` is off, so the address the browser used does not match what the server saw | The doctor warns "web page behind a proxy". Set `WEB_TRUST_PROXY=true` in `.env` and restart |
| "That form was too old to use." | The page was open from before a sign-out | Send the form again |
| Asked for the password again and again | The cookie does not come back: `data/` is not writable, so the signing key changes at each start (`ls -l /opt/familydb/data/web_secret`), or over HTTPS `WEB_TRUST_PROXY` is off | Fix the owner of `data/`, or set `WEB_SECRET_KEY` (also needed with more than one process), or turn the proxy setting on |

## The assistant does not answer, or answers wrongly

| You see | It usually means | Do this |
|---|---|---|
| No reply at all | The bot is not running, or Telegram is not connected | The doctor's "service" line; `sudo systemctl start familydb`, or on Docker `sudo docker compose --project-directory /opt/familydb up -d` |
| "Sorry, I only talk to the family … your id here is …" | The sender is not on the family list for that channel | Add them from "Waiting to be let in" on the Family page |
| "I can't answer yet: nobody has given me a model key." | No key for any model company. That message is not retried | Add one on [AI model](/wiki/controls/settings/ai-model#keys), then ask again |
| "Got it, but I can't get to it right now. I'll try again shortly." | The call failed in a way worth retrying: the company is busy or rate limiting, the server cannot reach it, or something unexpected broke | The message is retried every 5 minutes, 3 times at most; after that the job stops, though Status can still say "will try again". Check the log, outbound internet, DNS and the clock (`date -u`) |
| "Got it, but I can't reach my model at the moment. Someone should look at the logs." | The company refused for a reason retrying will not fix: a wrong or revoked key, no credit, a refused request. The message was given up | Needs a look usually names it. Fix it, then ask again, or run `familydb db retry-failed --reset`, which re-arms every failed message |
| "I've reached today's spending limit" | The day's estimate reached the limit | Raise it on [Spending](/wiki/controls/settings/spending#the-daily-limit) if the day was genuine; otherwise see [Cost](/wiki/operations/cost) |
| "I went around in circles on that one", or "That part is saved…" | The turn used all its steps (8 by default). The second wording means something was already written | Ask more simply, or raise "Steps per message" on Spending. Check what is saved before asking again |
| An answer cut short | The model hit the output limit; Status lists it under Worth a look | Raise "Longest answer, in tokens" on Spending |
| It forgets earlier chat | History is 20 messages from the last 6 hours by default | Raise them on Spending |
| A voice note or photo is not read | Hearing needs an OpenAI or Gemini key; the setting may be off; the recording was too long or large. It is never kept, so it is not retried | [Voice notes and photos](/wiki/controls/settings/ai-model#voice-notes-and-photos); ask for it again or typed |

A kid is given gentler words and is not told about money or how the bot works, so look in the log, not at what the kid was told. To see why one answer went wrong, open it under [Recent activity](/wiki/controls/status/activity).

## Telegram is silent, or its buttons do nothing

| You see | It usually means | Do this |
|---|---|---|
| "the token was refused by Telegram" | The token is wrong or revoked. It is not retried until it changes | Paste the current one on [Connections](/wiki/controls/settings/connections#telegram); it takes effect within seconds |
| "cannot reach Telegram; trying again" | The server cannot get out; it tries every 30 seconds | Check the network and DNS |
| Nothing from a group | "Answer only when mentioned" is on, or Telegram's privacy setting for bots is, so the bot sees only mentions and replies | The Connections card says which. For privacy send BotFather `/setprivacy`, choose Disable, then remove the bot from the group and add it again |
| A reply is missing and the log says "delivery pending for message …" | The send failed; the reply is stored and sent again by the retry job | Fix the connection if it repeats |
| A reply arrived twice | Telegram has no idempotency key, so delivery is at least once | Nothing. A resend never runs the model or repeats a calendar change |
| "That button no longer works.", "That's already dealt with.", "That didn't go through." | The thing is gone, was already done, or the action was refused (the log has "tap … did not go through") | Say it in words |
| "Only the family can use these." | The person who tapped is not on the list | Add them on the Family page |

More: [Telegram](/wiki/controls/telegram).

## Calendar problems

| You see | It usually means | Do this |
|---|---|---|
| "A calendar is named but not connected yet", or the doctor's "no key at …" | `data/google_key.json` is missing. Backups do not hold it | Make a new key and connect again on Connections |
| "Google Calendar stopped letting the bot in" | Google refuses the key: it or its service account was deleted | Make a new key and connect again; the row clears when Google answers |
| On connecting: "cannot find that calendar", "can see that calendar but not change it", or "not turned on in the project" | The id is wrong or the calendar is not shared with the service account; it was shared read-only; or the Calendar API is off | Share it with "Make changes to events", or turn the API on and wait a minute |
| An event added on a phone is not on the page | The page keeps Google's answer for up to a minute | Wait, then reload |

`familydb google events` prints what the bot sees. With no calendar connected, plans stay inside FamilyDB: a choice, not a fault. More: [Connections](/wiki/controls/settings/connections#google-calendar).

## Lookups are not happening

Lookups run only in the long-running service. A new idea waits, by default, for the evening lookup at 21:00.

| You see | It usually means | Do this |
|---|---|---|
| Doctor "web lookups: off" | The setting is off | Turn on "Look ideas up on the web" on [Lookups](/wiki/controls/settings/lookups#looking-ideas-up) |
| Ideas stay "waiting to be looked up" | It is before the evening hour, or there is no key for the company that does lookups, or the day's limit is used up | Press **Look them up now** on Status, or send `/lookup` (parents and admins) |
| A lookup failed | The note on the idea says why | Open the idea and press **Look it up again** |
| A suggestion says "web discovery off", "waits for a model key" or "failed" | Lookups are off, no key, or that search failed | Fix as above; the next question searches again |

## Reminders or the weekend digest do not arrive

Reminders, follow-ups and plan checks ask no model, so a model outage does not stop them. A plan check says nothing when all is well.

| You see | It usually means | Do this |
|---|---|---|
| The wrong hour | The time zone: a rented server is usually on UTC | [General](/wiki/controls/settings/general#where-home-is) |
| A reminder waits a couple of minutes | Someone is chatting in that chat, so it rides the next reply | It goes after a hold of about two minutes |
| A group's reminder arrives in a private chat | "Send what's for one person to their own chat" is on | Intended; see [Connections](/wiki/controls/settings/connections#in-a-telegram-group) |
| The digest never comes | With no chat set the job is not scheduled (doctor: "no chat id") | Choose the chat on [Messages](/wiki/controls/settings/messages#weekend-ideas) |
| The digest was skipped | The log says why: "digest skipped: there is no model key yet", "nothing here can send to …", "no active admin to ask as", or "digest already sent today" | Fix that. A Telegram group needs the bot in it and able to see its messages |

## Costs are higher than expected

[Cost](/wiki/operations/cost) has the numbers and every lever.

| You see | It usually means | Do this |
|---|---|---|
| Lookups and discovery dominate "Where the money went" | Each search is billed on top of tokens | Turn lookups off, or leave them for the evening |
| The cache share stays near zero | Something changes in the front of the request, or on Claude `anthropic_cache_ttl` is 5m | Run `familydb debug prompt "hi"` twice: the system text and tool list must be identical |
| A model with an asterisk | Its price is unknown, so it is counted dear | Choose a listed model, or let the daily check run |
| "What the calls cost or do moved" | A kind of call changed against the four weeks before | Open [Recent activity](/wiki/controls/status/activity) |

## The server

| You see | It usually means | Do this |
|---|---|---|
| `failed`, or "started and then stopped" | A value the settings will not take, or a file it cannot write | The doctor names it. The usual three: `familydb` does not own `data/` and `.env`, the checkout is under `/home`, a bad value in `.env` |
| "a setting will not do" | A value in `.env` has the wrong type, such as `WEB_PORT=eighty`; quote any value with a space or `#` | The error names the setting |
| "stored settings are not usable" | A value saved on the page no longer validates; the bot keeps running on `.env` | Fix or empty that box on the settings page |
| `Permission denied: '.env'` | You ran a command as yourself; `.env` belongs to `familydb` | Run it as that user from `/opt/familydb` |
| "cannot write", or "attempt to write a readonly database" | `data/` belongs to someone else, often after a by-hand restore | `sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env`; on Docker `sudo chown -R 1000:1000 /opt/familydb/data` |
| "database is locked" | More than one `familydb run` is writing | Run one; the command line beside it is fine |
| No space left on device | The disk is full; the doctor warns below 500 MB free | Below |
| `Killed` | The kernel ran out of memory, usually while the virtualenv is built on a 512 MB or 1 GB machine | Below |
| "Could not get lock /var/lib/dpkg/lock-frontend" | Another program is installing packages | `sudo fuser -v /var/lib/dpkg/lock-frontend`, wait a minute, run the installer again. Do not delete the lock file |

A failed install is safe to repeat: paste the same block again. Its log is `/var/log/familydb-bootstrap.log`.

**A full disk.** The nightly job already prunes backups older than `--keep-days` ([Backup and restore](/wiki/operations/backup-and-restore)). Free the journal and package cache, and cap the journal with `SystemMaxUse=500M` in `/etc/systemd/journald.conf`. Docker caps each container's log at five files of 10 MB.

```bash
df -h /
sudo journalctl --vacuum-size=200M
sudo apt-get clean
sudo docker system prune -af     # Docker only: removes everything unused on the host
```

**Out of memory.** Confirm with `sudo dmesg -T | grep -i 'killed process' | tail`, add swap, and run the installer again:

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

The firewall and unattended updates are in [the host guide](/wiki/operations/host), and a bad upgrade in [Upgrade and rollback](/wiki/operations/upgrade-and-rollback).

Developer docs: `RUNBOOK.md`, "Troubleshooting"; `docs/INSTALL.md`, "Troubleshooting"; `familydb/doctor.py` (the checks); `familydb/alerts.py` and `familydb/web/status.py` (`attention`, `health`); `familydb/voice.py` (`EVENTS`).
