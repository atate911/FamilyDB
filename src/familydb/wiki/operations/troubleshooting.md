# Troubleshooting

Run the three commands under "Start here", then jump to your symptom.

## Start here

```bash
sudo /opt/familydb/scripts/maintain.sh check
sudo /opt/familydb/scripts/maintain.sh status
sudo journalctl -u familydb -n 100 --no-pager
```

The check looks at the files, git, `.env`, Python, the database file, the service, the web server and the host before it asks the program anything, so it names the cause even when the program will not start. It prints a fix under each finding: `✗` must be fixed, `!` is worth a look, and **Start here** names the first thing to fix. If you would rather it worked it out and fixed it, `sudo /opt/familydb/scripts/maintain.sh doctor` explains what is wrong and does the safe repairs on one Enter. If the usual fixes are not enough, [Break glass](/wiki/operations/break-glass) has a way out for a program that will not start, an upgrade that broke it, a damaged database, a full disk and a lockout. On Docker the log is `sudo docker compose --project-directory /opt/familydb logs --tail 100 bot`, and `maintain.sh check` runs in a fresh container, so **web page answering** can warn while the page is up (`docker compose ps` is the truth). [Logs](/wiki/operations/diagnostics#logs) says how to follow and read them. To restart on either install, run `sudo /opt/familydb/scripts/maintain.sh restart`.

Jump to: [the page will not open](#the-page-will-not-open), [sign-in](#somebody-cannot-sign-in), [a message got no reply](#a-message-got-no-reply), [Telegram](#telegram-is-silent-or-its-buttons-do-nothing), [calendar](#calendar-problems), [lookups](#lookups-are-not-happening), [reminders and weekend ideas](#reminders-or-weekend-ideas-do-not-arrive), [the server](#the-server). For money, see [Cost](/wiki/operations/cost#if-costs-are-higher-than-expected). The web page keeps its own list of recent warnings and errors and the words of failed model calls on the [Troubleshooting card](/wiki/controls/settings/troubleshooting).

## A message got no reply

Work down this list until you find the cause.

1. Check that FamilyDB is running with `maintain.sh status`, then open [Status](/wiki/controls/status). The pill and **Needs a look** say when the assistant cannot answer anyone.
2. **Messages that did not go through**, under Waiting on Status, lists each failed message with its text, its error and a note: "N tries, will try again", or "given up on after N tries" with the words to send again. A failed message is retried; a given-up one is not ([the numbers](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)).
3. If it is not listed and the person got nothing, a restart may have interrupted it. Its 5-minute lease must run out, then the retry job picks it up at its next run (every 5 minutes by default), after Telegram's 4-second pause. Allow about 10 minutes.
4. Find the message in the log. Its lines name it, as in `message 42`:

   ```bash
   sudo journalctl -u familydb --since "1 hour ago" --no-pager | grep -E 'message [0-9]+'
   ```

   On Docker, use the Docker log command above with `--since 1h` and the same `grep`. An admin can then open `/status/activity/m42` (use your number) to see what was asked and why there was no reply.
5. Match what the family saw, or the log line, in the table below.
6. When the cause is fixed, retry what failed:

   ```bash
   cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb db retry-failed
   ```

   On Docker:

   ```bash
   sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb db retry-failed
   ```

> **Adding `--reset` gives failed messages with no tries left new tries, so old messages can be answered late and billed again.** Check **Messages that did not go through** first. A message given up on purpose (a person taken off, a kid over the day's limit, a missing key) stays given up.

| You see | It means | Do this |
|---|---|---|
| "Sorry, I only talk to the family. Ask one of them to add you; your id here is 123456789." | The sender is not on the family list. No model was asked. Log: `unknown sender` | Add them from **Waiting to be let in** on [Family](/wiki/controls/family#link-a-telegram) |
| "I can't answer yet: nobody has given me a model key. An admin can add one on the settings page." | No key for any model company. The message is given up. Log: `message 42 saved, but there is no model key to answer it with` | Add a key on [AI model](/wiki/controls/settings/ai-model#keys), then ask again |
| "Got it, but I can't get to it right now. I'll try again shortly." | The call failed in a way worth retrying: the company is busy, the server cannot reach it, or something unexpected broke. Log: `agent error on message 42: ... (retryable=True)` or `unexpected error on message 42` | The retry job tries again; the family hears nothing more. Check the network (`ping -c1 1.1.1.1`) and the clock (`date -u`; a day off breaks certificates). A traceback is a bug, not a setting |
| "Got it, but I can't reach my model at the moment. Someone should look at the logs." | The company refused for a reason retrying will not fix: a bad key, no credit, or a refused request. The message is given up. Log: `agent error on message 42: ... (retryable=False)` | **Needs a look** names a bad key or no credit. Fix it, then retry as in step 6 |
| "I've reached today's spending limit ($2.00), so I'm stopping here until tomorrow. It can be raised on the settings page." | The day's estimate reached the limit. The message is given up. Log: `daily spending limit reached` | Raise it on [Spending](/wiki/controls/settings/spending#the-daily-limit), or wait for midnight in home time |
| "I went around in circles on that one and stopped before it got expensive. Could you ask it a simpler way?" or "That part is saved, but I ran out of steps before the rest. Check what's there before asking again, so nothing is done twice." | The turn used all its steps (8 by default); the second wording means something was already written. Log: `turn on message 42 ran out of steps; not retrying it` | Ask more simply, or raise **Steps per message** on Spending. Check what is saved first |
| "That part is saved. The spending limit stopped me before the rest; check what's there before asking again, so nothing happens twice." | The day's limit was reached after something was already written | Wait for midnight or raise the limit, then check what is saved |
| An answer cut short | The model hit the output limit. Status lists it under Worth a look | Raise **Longest answer (tokens)** on Spending |
| A voice note or photo is not read ("I can't hear voice notes yet: ...", "I'm not listening to voice notes at the moment, ...", "I'm not looking at photos at the moment, ...") | Hearing needs an OpenAI or Gemini key, the setting is off, or the file is too long or large. Nothing is kept, so nothing is retried | [Voice notes and photos](/wiki/controls/settings/ai-model#voice-notes-and-photos). Ask again, or typed |

With no persona, or when the family rewrote the lines on [Personality and family](/wiki/controls/settings/personality), the words differ and the cause is the same; the plain retry line is "Saved your message, but I couldn't process it right now. I'll retry later." A kid whose limit is used up gets a plain line to come back tomorrow, with no word about money ([Kids](/wiki/model/family-and-roles#kids)). The troubles only an admin can fix are also sent to each admin with a Telegram id; [When something needs fixing](/wiki/controls/settings/messages#when-something-needs-fixing) lists them.

## The page will not open

| You see | It means | Do this |
|---|---|---|
| The browser waits, then times out | The hosting provider's firewall closes the page's ports | Allow incoming TCP on 80 and the page's port (443 unless moved) in the provider's panel; see [HTTPS and the firewall](/wiki/operations/https-and-firewall). If the `curl` command below answers on the server, the server is fine |
| A 502 from Caddy | FamilyDB behind Caddy is not serving | The first command below names why |
| Log: "the web page is not serving" | The page faces the network, but nobody has their own password and there is no shared password of 12 or more characters | Choose a password for an admin ([Recovery](/wiki/operations/recovery)), or set `WEB_PASSWORD` in `.env`, then restart. The assistant keeps running without a page |
| Log: "could not serve the web page on http://127.0.0.1:8080/: [Errno 98] Address already in use" | Another program, or a second copy of FamilyDB, has the port (the address is your `WEB_HOST` and `WEB_PORT`) | Find the holder with the second command below, or move FamilyDB's port with the third. On Docker the failure shows at `docker compose up`, not in the log |
| No page and no log line; the doctor says the page is "off" | `WEB_ENABLED` is false | Set `WEB_ENABLED=true` in `.env`, then restart |
| It opens on the server only | The page listens on this machine, and Caddy reaches it. On Docker the compose `ports` line starts `127.0.0.1:` | Use the HTTPS address, or an SSH tunnel if you installed with `--local-only` |

```bash
sudo journalctl -u familydb -n 40 | grep -E 'not serving|could not serve'
sudo ss -ltnp | grep ':8080'
sudo /opt/familydb/scripts/maintain.sh port random
curl -skI https://127.0.0.1 -H 'Host: <server address>'
```

Use your `WEB_PORT` in place of 8080 if you moved it.

## Somebody cannot sign in

[Recovery](/wiki/operations/recovery) covers forgotten passwords, the shared password, "Too many tries" and a lost phone. What else shows up:

| You see | It means | Do this |
|---|---|---|
| "That request did not come from this page." | The address in the browser does not match what the server saw, such as http against https. Behind a proxy, `WEB_TRUST_PROXY` is off | The doctor warns "web page behind a proxy". Set `WEB_TRUST_PROXY=true` in `.env`, then restart |
| "That form was too old to use. Here it is again." | The page was open from before a sign-out | Send the form again |
| Asked for the password again and again | The cookie does not come back: `data/` is not writable, so the signing key changes at each start, or `WEB_TRUST_PROXY` is off over HTTPS | Fix the owner of `data/`, set `WEB_SECRET_KEY` (also needed with more than one process), or turn the proxy setting on, then restart |

## Telegram is silent, or its buttons do nothing

The full failure table is [If Telegram changes or is down](/wiki/boundaries/telegram#if-telegram-changes-or-is-down). These rows come first.

| You see | It means | Do this |
|---|---|---|
| Status or Connections: "the token was refused by Telegram" (the log says "Telegram refused the bot token") | The token is wrong or revoked, and is not retried until it changes | Paste the current one on [Connections](/wiki/controls/settings/connections#telegram) |
| Status or Connections: "cannot reach Telegram; trying again" | The server cannot get out; it tries every 30 seconds | Check the network and DNS |
| Nothing from a group | **Answer only when mentioned** is on, or Telegram's privacy setting for bots is on | The Connections card says which. For privacy, send BotFather `/setprivacy`, choose Disable, then remove the Telegram bot from the group and add it again |
| The log says "delivery pending for message 42" | The send failed; the retry job sends the stored reply again | Fix the connection if it repeats |
| A reply arrived twice | Telegram cannot tell FamilyDB whether a send arrived | Nothing. A resend never runs the model or repeats a calendar change |
| "That button's gone stale; tell me in words instead.", "That one's already taken care of.", "That didn't go through. Could you tell me in words?" | The thing is gone, was already done, or the action was refused | Say it in words |
| "Sorry, only the family can use these." | The person who tapped is not on the list | Add them on Family |

## Calendar problems

| You see | It means | Do this |
|---|---|---|
| Status: "A calendar is named but not connected yet." Doctor: "no key at ..." | `data/google_key.json` is missing, and backups do not hold it | Make a new key and connect again on [Connections](/wiki/controls/settings/connections#google-calendar) |
| Status: "Google Calendar refused the bot's key, or it has none" | Google refuses the key, or the key or its service account was deleted | Make a new key and connect again. The row clears when Google answers |
| Status: "Google Calendar is no longer showing the bot its calendar" | The calendar is no longer shared with the service account, or was deleted. A plan you moved was left as it is, not canceled | Share it again with **Make changes to events**, or connect another calendar. The row clears when Google answers |
| On connecting: "cannot find that calendar", "can see that calendar but not change it", or "not turned on in the project" | The id is wrong, the calendar is not shared with the service account or only read-only, or the Calendar API is off | Share it with **Make changes to events**, or turn the API on and wait a minute |
| Plans stop reaching the calendar and nothing is flagged | The calendar was unshared or made read-only after connecting, or its Calendar API was switched off. Only an unshared or deleted calendar, found when one plan's event is looked up, raises a row; see [An unshared calendar raises an alert only when one event is looked up](/wiki/reference/known-limits#an-unshared-calendar-raises-an-alert-only-when-one-event-is-looked-up) | Share it again with **Make changes to events** |
| An event added on a phone is not on the page | The page keeps Google's answer for up to 1 minute | Wait, then reload |

`familydb google events` lists what the assistant can see on the calendar; run it as in [The command line](/wiki/operations/command-line#how-to-run-it).

## Lookups are not happening

Lookups run only in the long-running service. A new idea waits, by default, for the evening lookup at 21:00.

| You see | It means | Do this |
|---|---|---|
| Doctor: "web lookups: off" | The setting is off | Turn on **Look ideas up on the web** on [Lookups](/wiki/controls/settings/lookups#looking-ideas-up) |
| Ideas stay "waiting to be looked up" | It is before the evening hour, there is no key for the lookup company, or the day's limit is used up | Press **Look them up now** on Status, or send `/lookup` (parents and admins) |
| A lookup failed | The note on the idea says why | Open the idea and press **Look it up again** |

## Reminders or weekend ideas do not arrive

Reminders, follow-ups and plan checks ask no model, so a model outage does not stop them.

| You see | It means | Do this |
|---|---|---|
| A reminder at the wrong hour | The time zone; a rented server is nearly always on UTC | [General](/wiki/controls/settings/general#where-home-is) |
| A reminder waits | Somebody is chatting in that chat, so it rides the next reply | It goes after up to 2 minutes if nobody replies |
| Weekend ideas never come | No chat is set, so the job is not scheduled. Doctor: "no chat id" | Choose the chat on [Messages](/wiki/controls/settings/messages#weekend-ideas) |
| Weekend ideas were skipped | The log says "digest skipped: there is no model key yet", "digest skipped: nothing here can send to ...", "digest skipped: no active admin to ask as" or "digest already sent today" | Fix that cause. A Telegram group needs the Telegram bot in it |

## The server

| You see | It means | Do this |
|---|---|---|
| `failed`, or "started and then stopped" | A value the settings will not take, or a file FamilyDB cannot write | The doctor names it. The cause is one of three: `familydb` does not own `data/` and `.env`, the checkout is under `/home`, or `.env` has a bad value |
| "a setting will not do" | A value in `.env` has the wrong type, such as `WEB_PORT=eighty` (quote any value with a space or `#`), or a value saved on the page no longer validates | The message names the setting. Fix or empty it, then restart |
| `Permission denied: '.env'` | You ran a command as yourself, and `.env` belongs to `familydb` | Run it as that user from `/opt/familydb`, as [The command line](/wiki/operations/command-line#how-to-run-it) shows |
| "cannot write", or "attempt to write a readonly database" | `data/` belongs to someone else, often after a by-hand restore | Run the first command below, then restart |
| "database is locked" | More than one `familydb run` is writing | Run one. A command-line command beside it is fine |
| "No space left on device" or `Killed` | The disk is full, or memory ran out while the virtualenv was built on a 512 MB or 1 GB machine | [The server](/wiki/operations/host#disk-and-memory) has the fixes, including swap |
| "Could not get lock /var/lib/dpkg/lock-frontend" | Another program is installing packages | Run the second command below, wait a minute, and run the installer again. After an interrupted install, run the third first. Do not delete the lock file |

```bash
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo fuser -v /var/lib/dpkg/lock-frontend
sudo dpkg --configure -a
```

On Docker, give `data/` to `1000:1000` instead; there is no `.env` to give. A failed install is safe to repeat: paste the same block again. For a bad upgrade, see [Upgrade and rollback](/wiki/operations/upgrade-and-rollback).

## Asking for help

Collect these first:

- the version, from `maintain.sh status`;
- the output of `maintain.sh check`;
- the output of `familydb config`, which shows every key, token and password as `****`;
- the log lines around the time, from `journalctl` with `--since` and `--until`;
- for an install that did not finish, `/var/log/familydb-bootstrap.log`.

Read the log before you paste it anywhere. FamilyDB replaces a Telegram token in a log line with `bot<token>`, but not inside a traceback.
