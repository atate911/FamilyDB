# Installing FamilyDB on a server

This is the long way round: a bare VPS at the start, the family messaging the bot at the end.
It assumes nothing is installed and nothing is configured, and it explains why each step is
there, because most of them are only obvious once you have been bitten by the alternative.

`scripts/bootstrap.sh` does most of the work. What it cannot do are the parts that need a
browser, a phone, or a password only you know; those are here too.

Once it runs, [RUNBOOK.md](../RUNBOOK.md) is the reference. It has a section per integration
and per setting, and this file points at those sections by number rather than repeating them.

| Script | What it is for |
|---|---|
| `scripts/bootstrap.sh` | a bare server to a running bot: packages, code, a service user, the service |
| `scripts/install.sh` | the questions and the configuration; bootstrap hands over to it |
| `scripts/maintain.sh` | afterwards: status, backups, restores, upgrades, logs |
| `scripts/uninstall.sh` | taking it off again, with or without the data |
| `familydb doctor` | what is wrong with this install, and what to do about each thing |

Every one takes `--help` and `--dry-run`; a dry run before the real one is never wasted.

## 1. What you need before you start

**A server.** Any VPS will do. The bot uses about 200 MB of memory; building the install wants
more, so 1 GB is the sensible minimum and 512 MB only works with swap (section 2) — bootstrap
warns below 900 MB and says the same. Two gigabytes of free disk: the install is roughly 600 MB
and the database grows by a few MB a year.

**Debian 12, or Ubuntu 22.04 or 24.04.** Those are what is tested. On anything else bootstrap
refuses to install packages with apt and tells you to bring `git`, `curl` and either Docker or
Python 3.11+ yourself, then run it again with `--no-packages`. x86_64 and arm64 are both fine.

**A non-root user with sudo, reachable over SSH with a key.** Do not do this as root. The
scripts ask for root only where they need it, and say what for each time.

**An API key** from one of Anthropic, OpenAI or Google. One is enough. Give more than one and
the others become spares for when the first is rate limited (RUNBOOK section 11).

**Optionally, a Telegram bot** so the family can message it from their phones, and **a Google
account** with a shared calendar. Neither is needed to get it running and both can be added
later; without Telegram you talk to it with `familydb repl` on the server, which is fine for a
first look and no use to anyone else in the house.

**A domain, only if** you want the web page reachable from the internet (section 6). The bot
itself makes outgoing connections only: no inbound ports, no domain, no reverse proxy.

## 2. Prepare the server

Everything here is ordinary server hygiene, not FamilyDB. Skip what you have already done.

**A user that is not root.** From root, once:

```bash
adduser sam
usermod -aG sudo sam
```

**SSH keys, from your own computer,** and then check you can still get in from a second
terminal before you turn passwords off:

```bash
ssh-copy-id sam@your-server
ssh sam@your-server 'echo in'
```

With that working, in `/etc/ssh/sshd_config` set `PasswordAuthentication no` and
`PermitRootLogin no`, then `sudo systemctl reload ssh`.

**A firewall.** The order matters more than the rules:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH        # BEFORE enabling. Skip this line and you lock yourself out.
sudo ufw enable
sudo ufw status
```

`ufw enable` takes effect immediately, including on the connection you are typing over. If
`allow OpenSSH` is not already in place when you enable it, your session dies and you cannot
open another; the only way back in is your provider's console. Do not leave that line out.

**Unattended security updates.** This is the piece of maintenance that matters most:

```bash
sudo apt update && sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades    # answer yes
```

**The timezone.** The bot works out what "this weekend" means from `FAMILYDB_TZ`, which the
installer offers to take from the machine, so it is worth setting the machine first:

```bash
timedatectl list-timezones | grep Vancouver
sudo timedatectl set-timezone America/Vancouver
```

**Swap, if memory is tight.** On a 1 GB box the install step that builds the virtualenv is the
one that gets killed. Swap makes it slow rather than fatal:

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -m
```

## 3. Getting the code onto the box

FamilyDB lives in a private repository, `github.com/atate911/FamilyDB`. A private repository
cannot simply be cloned, and this is the step that actually stops people. There are three ways
to do it, and they differ in what credential ends up on the server:

| Way | What is on the server | Best for |
|---|---|---|
| Deploy key | one SSH key, read-only, valid for this repository alone | a server you keep, and the default choice |
| Token | a token that can read every repository it was scoped to | getting going quickly |
| Copy it yourself | nothing at all | a server you do not want to trust with anything |

A deploy key is the best default because it is the narrowest: it is per-repository, it is
read-only if you leave the write box unticked, and revoking it is one click that affects
nothing else. A token is easier to set up and broader in what it can reach, so it is worth
deleting once the install is done. Copying the code yourself puts no credential on the machine
at all; the price is that upgrades mean copying again.

Whichever you pick, `scripts/bootstrap.sh` has to exist on the server before it can run, so
each of these starts by getting at least the `scripts/` folder there.

### Option 1: a deploy key

On the server, make a key that exists for this one purpose:

```bash
ssh-keygen -t ed25519 -C "familydb deploy" -f ~/.ssh/familydb_deploy -N ""
cat ~/.ssh/familydb_deploy.pub
```

Copy that public line. In GitHub, open the repository, then **Settings → Deploy keys → Add
deploy key**. Title it after the machine, paste the key, and leave **Allow write access**
unticked: the server never needs to push. Check it from the server:

```bash
ssh -T git@github.com -i ~/.ssh/familydb_deploy
# "Hi atate911/FamilyDB! You've successfully authenticated, but GitHub does not provide shell
#  access." is the answer you want.
```

Then put the scripts on the box and run bootstrap with the key. From your own computer, in
your own clone:

```bash
scp -r scripts sam@your-server:~/
```

And on the server:

```bash
sudo bash ~/scripts/bootstrap.sh --deploy-key ~/.ssh/familydb_deploy
```

Bootstrap rewrites the repository URL to its SSH form, clones with that key, and then clears
the credential out of the saved remote so nobody reading `.git/config` later finds one.

### Option 2: a fine-grained personal access token

In GitHub, **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
Generate new token**. Give it the shortest expiry you can live with, set **Repository access**
to **Only select repositories** and pick FamilyDB, and under **Permissions → Repository
permissions** set **Contents** to **Read-only**. Nothing else.

```bash
scp -r scripts sam@your-server:~/                      # from your own computer
```

```bash
sudo GITHUB_TOKEN=github_pat_... bash ~/scripts/bootstrap.sh
```

The token is used for the clone and nothing else: it is never written to `.env`, never written
to the log, and the saved remote is reset to the plain HTTPS URL afterwards so it does not sit
in `.git/config`. It does go into your shell history, though, so clear that line out
(`history -d`), or read it in with `read -rs GITHUB_TOKEN` first and `export` it.

### Option 3: copy it from your own computer

No credential reaches the server at all. Clone locally, then copy it across without the
virtualenv, the database or your own `.env`:

```bash
git clone git@github.com:atate911/FamilyDB.git ~/FamilyDB
rsync -a --exclude .venv --exclude data --exclude .env ~/FamilyDB/ sam@your-server:~/FamilyDB/
# or, without rsync:  scp -r ~/FamilyDB sam@your-server:~/
```

Then on the server:

```bash
sudo bash ~/FamilyDB/scripts/bootstrap.sh --from ~/FamilyDB
```

`--from` also takes a `.tar.gz` of a checkout, which is easier to move around than a directory
tree. Excluding `.env` matters: yours holds your own keys, and a copy of it landing on the
server means the installer finds a configuration that was never meant for that machine.

If bootstrap is run from inside a checkout and given nothing else, it installs that checkout,
so `sudo bash ~/FamilyDB/scripts/bootstrap.sh` on its own does the same thing.

## 4. Run the bootstrap

### Why /opt and not your home directory

The bot runs as its own system user, `familydb`, with no password and no login shell, so that
a mistake in it cannot reach the rest of the machine. Home directories are mode 0750 on Debian
and Ubuntu, which means that user cannot enter `/home/sam` at all. A systemd unit pointing at a
checkout in there starts into a directory it cannot read and stops immediately.

So the install goes in `/opt/familydb`, which is the default and what the unit ships with.
`scripts/install.sh` checks this before it writes a unit: if the service user cannot reach the
checkout it says so, skips the unit rather than leaving you one that cannot start, and tells
you to move the checkout. That is a refusal, not a failure — everything else is still
installed.

### The run itself

```bash
sudo bash ~/scripts/bootstrap.sh --deploy-key ~/.ssh/familydb_deploy
```

Useful flags, all in `--help`. `--dry-run` says what would happen and changes nothing, which
is worth one pass. `--mode docker` installs Docker Engine and the compose plugin and runs it
that way; the default is `venv`, the smaller install and the one the rest of this file assumes.
`--target DIR` and `--user NAME` move the install and rename the service account. `--ref v0.1.0`
installs that tag, branch or commit, where the default is the newest release tag and the default
branch only if there are no tags, and `--repo URL` clones from somewhere else. `--no-packages`
installs nothing with apt, `--no-install` stops before the questions, `--no-start` leaves it
stopped, and `--yes` takes every default and asks nothing, for a scripted build.

### What it changes, and what a good run looks like

Before it touches anything it prints a plan with a reason against each line: the packages, the
`familydb` user, the directory, the `.env` and database it would write, the unit it would
enable, and what it will not touch — your firewall, your SSH configuration, the system Python,
other services, home directories and inbound ports. Then it asks.

After that it works through apt packages (`ca-certificates curl git tzdata`), uv or Docker, the
code into `/opt/familydb` and the `familydb` user, then hands over to `scripts/install.sh`,
which asks:

- which model answers: Claude, OpenAI or Gemini, and a key for each one you have
- the timezone, offered from the machine's own setting
- your town or area, which it geocodes into `HOME_LAT`/`HOME_LON` for the forecast
- metric or imperial
- a Telegram bot token, if you have one already
- whether to turn web lookups on
- whether to turn the web page on, and on which address and port, with a generated password
- your name, as the family says it, which becomes the first admin

Three things are left deliberately empty, because nobody can know them before the bot is
running: `DIGEST_CHAT_ID`, `GOOGLE_CALENDAR_ID` and the Google token. Section 5 fills them in.

It finishes by starting the service and running `familydb doctor`, which prints a line per
check. A `✓` is something that was looked at and is fine. A `!` is usually something not set up
yet, which is normal on a first install; Telegram, the calendar and the digest are all `!`
until you do section 5. A `✗` must be fixed before anything works.

A transcript of the whole run is at `/var/log/familydb-bootstrap.log`, and how far it got is
at `/var/log/familydb-bootstrap.progress`. Running it again is safe: it installs what is
missing, leaves an existing `/opt/familydb` alone, and says where the last run stopped.

## 5. Finish the setup

### The web page, over an SSH tunnel

If you turned the page on, it is bound to `127.0.0.1` and reaches nothing but the server
itself. That is the right default, and you can still use it from your own computer without
opening a single port. From your own computer:

```bash
ssh -L 8080:127.0.0.1:8080 sam@your-server
```

Leave that open and go to `http://127.0.0.1:8080/` in a browser. Sign in with the family
password the installer printed. Everything below can be done on `/settings` instead of in
`.env`, and most settings changed there take effect on the next message; adding or changing the Telegram bot token requires restarting FamilyDB
(RUNBOOK section 11).

### The keys

If you skipped the keys during the install, `/settings` is where to type them. One consequence
worth knowing: a key stored there lives in `data/familydb.sqlite3`, so it is in every backup you
take, and a key in `.env` is not. Either is fine on a machine you control; if the backups go
somewhere you do not, keep the keys in `.env` (RUNBOOK sections 7 and 11).

### Telegram

RUNBOOK section 4 is the full version. In short: `/newbot` to @BotFather, copy the token into
`TELEGRAM_BOT_TOKEN` in `.env` or onto `/settings`, then restart, because the Telegram
connection is opened once when the service starts:

```bash
sudo systemctl restart familydb
```

Then each person messages the bot. The reply tells them their id on that channel, and you add
them with it:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb members add "Jo" --role member \
  --channel telegram --channel-user-id 12345678
```

Kids need no channel: `--role kid` is enough for them to be named as participants. For a family
group, `/setprivacy` → Disable in BotFather, then add the bot to the group.

### Google Calendar

RUNBOOK section 5 has the Google Cloud side, and one detail there is worth repeating because
it bites a week later: set the OAuth consent screen to **In production**. Left in Testing,
refresh tokens expire after seven days and the bot quietly stops writing to the calendar every
week.

The sign-in needs a browser, so it happens on your laptop and not on the server:

```bash
uv run familydb google auth --client-secrets ~/Downloads/client_secret_XXX.json
uv run familydb google calendars          # find the family calendar's id
```

Then copy the token over and give it to the service user, which is the bit people forget:

```bash
scp data/google_token.json sam@your-server:/tmp/
sudo install -o familydb -g familydb -m 600 /tmp/google_token.json /opt/familydb/data/
rm /tmp/google_token.json
```

Put the calendar id in `GOOGLE_CALENDAR_ID` (`.env` or `/settings`), restart, and check:

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb google events
```

### The chat id for the digest

The Thursday digest needs the family group's chat id, which only exists once the group does.
Group ids are negative numbers. Once somebody has written in the group:

```bash
sudo -u familydb sqlite3 /opt/familydb/data/familydb.sqlite3 \
  "select distinct chat_id from messages where channel = 'telegram'"
```

Put it in `DIGEST_CHAT_ID` and check with `familydb digest`, which prints the schedule, or
`familydb digest --now`, which posts one immediately. RUNBOOK section 9.

## 6. Putting the web page on the internet properly

Only do this if you want it: the tunnel in section 5 is safer and costs nothing. If you do,
plain HTTP would send the family password in the clear, so it goes behind Caddy with a real
certificate.

**DNS.** An A record for `familydb.example.com` pointing at the server's address, and an AAAA
record if it has IPv6. Check it has propagated before you start Caddy, or the certificate
request fails: `dig +short familydb.example.com`.

**`.env`:**

```
WEB_ENABLED=true
WEB_HOST=0.0.0.0
WEB_PASSWORD=a-long-random-password
WEB_TRUST_PROXY=true
WEB_DOMAIN=familydb.example.com
```

**Caddy.** The `tls` profile is part of `docker-compose.yml`, so this is the Docker path:

```bash
cd /opt/familydb
sudo docker compose --profile tls up -d
sudo docker compose logs -f caddy
```

On the virtualenv path there is no profile to start; install Caddy or nginx yourself, proxy to
`127.0.0.1:8080`, and leave `WEB_HOST=127.0.0.1` so nothing but the proxy can reach the page.

**The firewall.** Open 80 and 443, and nothing else:

```bash
sudo ufw allow 80,443/tcp
sudo ufw status
```

Do not open 8080. Compose publishes the page to `127.0.0.1` so that Caddy, and only Caddy, can
reach it; the firewall is the second lock on the same door.

`WEB_TRUST_PROXY=true` makes the page read the real visitor address and the HTTPS scheme from
Caddy's headers, and marks the login cookie `Secure`. Only turn it on with a proxy actually in
front, because it means trusting those headers.

**The warning worth reading twice.** One shared password is all that stands between a stranger
and your API bill. Signing in allows editing ideas and restaurants, changing calendar plans, and using
the AI assistant. The settings page can also change which model answers, read the API keys back, and point the bot at a different
calendar. Make the password long, and look at `/status` now and then for a month that does not
look like yours. RUNBOOK section 10 has what else protects the page: rate limits, lockouts,
CSRF tokens and a content security policy.

## 7. Check it works end to end

The one command that looks at everything:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

That runs `familydb doctor`, which checks the settings, `.env`'s permissions, the disk, the
database and its schema, who is in the family, the keys, the models, Telegram, the calendar,
the weather, the lookups, the digest, the web page and the service, and prints a fix under
anything that is wrong. `--online` also asks the model API and Telegram whether the keys
actually work, which costs nothing but a token count:

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

Then a real message, either from a phone over Telegram or from the server:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb chat "we should try that new ramen place on Main St sometime"
sudo -u familydb .venv/bin/familydb chat "tell me about #1"
sudo -u familydb .venv/bin/familydb db status
```

`db status` should show `cache_read` greater than zero on the second call: the prompt cache is
working and most of each message is not being paid for twice. If it stays zero, section 10.

Finally `/status` in the browser: which model answers chat and which does the lookups, whether
each key is set and where it came from, what is connected, what the last thirty days cost, and
what is waiting. It asks nothing of a model, so refreshing it is free.

## 8. Day to day

`scripts/maintain.sh` is the one to remember:

```bash
sudo /opt/familydb/scripts/maintain.sh status             # running? healthy? last backup?
sudo /opt/familydb/scripts/maintain.sh check              # the full check, with fixes
sudo /opt/familydb/scripts/maintain.sh logs 200           # follow the log
sudo /opt/familydb/scripts/maintain.sh restart
sudo /opt/familydb/scripts/maintain.sh backup
sudo /opt/familydb/scripts/maintain.sh restore FILE       # stops it, puts it back, starts it
sudo /opt/familydb/scripts/maintain.sh upgrade            # newest release, backup taken first
```

`restore` backs up the database it is about to replace, so a restore can itself be undone.
`upgrade` takes a backup, fetches the newest release tag, reinstalls the locked dependencies,
migrates and restarts, and prints the command to go back to the previous release if it went
badly.

**Upgrades on a private repository.** `upgrade` fetches from `origin`, which needs a credential.

If you installed with `--deploy-key`, bootstrap already wired it up: it left the SSH remote in
place and recorded the key's path in the checkout's `core.sshCommand`, so upgrades work as long
as that key file stays where it is. Keep it somewhere durable, such as `/root/familydb_deploy`,
rather than in the home directory of an account you might remove.

If you installed with a token, bootstrap deliberately did not write it down, so there is no
credential to fetch with. Either point the checkout at a deploy key once:

```bash
sudo install -m 600 -o root -g root ~/.ssh/familydb_deploy /root/familydb_deploy
sudo git -C /opt/familydb remote set-url origin git@github.com:atate911/FamilyDB.git
sudo git -C /opt/familydb config core.sshCommand \
  "ssh -i /root/familydb_deploy -o IdentitiesOnly=yes"
sudo git -C /opt/familydb fetch --tags origin      # should now work
```

or fetch once with the token, without storing it:

```bash
sudo git -C /opt/familydb -c http.extraheader="AUTHORIZATION: bearer $TOKEN" fetch --tags origin
```

If you brought a copy yourself there is nothing to fetch from at all: copy a newer checkout over
the top, keeping `.env` and `data/`, then run `scripts/install.sh` again. `upgrade` says all of
this itself when a fetch fails, so you do not have to remember it. RUNBOOK section 8 covers
upgrading by hand.

**Backups, nightly and off the machine.** The database is one file and everything the family
has ever said is in it:

```bash
sudo /opt/familydb/scripts/maintain.sh schedule-backups --keep-days 14
sudo crontab -u root -l
```

That adds one line to root's crontab, for either Docker or systemd: a safe SQLite online
backup at 03:15 followed by pruning files older than `--keep-days` only if the backup succeeds.
When replacing an older schedule, remove its two FamilyDB lines from the `familydb` user's
crontab. A backup on the same disk is not a backup, so copy them off as well, from your
own computer:

```bash
rsync -av sam@your-server:/opt/familydb/backups/ ~/familydb-backups/
```

RUNBOOK section 7 covers restoring by hand and what is and is not inside a backup; section 12
covers journald limits, disk, and what to do when a secret gets out.

## 9. Removing it

Two modes, and the difference is the database.

```bash
sudo /opt/familydb/scripts/uninstall.sh
```

Stops the service, removes the unit, the virtualenv, the containers and the image. It keeps
`.env`, `data/` (the database, the Google token, the login key), `backups/` and `caddy/`.
This is what you want before reinstalling: running `scripts/install.sh` over it picks up where
it left off.

```bash
sudo /opt/familydb/scripts/uninstall.sh --purge
```

Removes all of that as well: the database, the configuration, the backups and the service user.
Before it does, it writes a backup to `/var/backups/familydb` (`--backup-to DIR` to put it
somewhere else, `--no-backup` to skip it, which you should say deliberately), and then asks you
to type `remove everything` in full. It refuses to touch a directory that does not contain a
FamilyDB `pyproject.toml`, and refuses system directories outright. `--keep-user` leaves the
system account alone; `--force` skips the question, which with `--purge` deletes the database
at once.

If the script is inside the directory it is deleting it will not remove that directory itself,
and tells you to finish with `cd / && sudo rm -rf /opt/familydb`.

What it deliberately leaves alone, because they are not its to remove:

- Docker, and uv
- the Telegram bot: delete it with `/deletebot` in @BotFather
- the Google Cloud project and its OAuth client
- the API keys at each provider, which stay live until you revoke them at Anthropic, OpenAI or
  Google yourself
- the deploy key on the repository, which is one click under Settings → Deploy keys

## 10. Troubleshooting

### Where the logs are

```bash
less /var/log/familydb-bootstrap.log         # the whole bootstrap run, step by step
sudo journalctl -u familydb -n 100 --no-pager
sudo journalctl -u familydb -f               # follow it
cd /opt/familydb && sudo docker compose logs -f bot    # the Docker path
```

`maintain.sh` and `uninstall.sh` keep their own transcripts at
`/var/log/familydb-maintain.log` and `/var/log/familydb-uninstall.log`. Every failure message
from these scripts names the file to send if you want somebody to look. Nothing in FamilyDB
writes a log file of its own: with systemd it all goes to journald, and with Docker the compose
file caps each container at five files of 10 MB.

### The clone fails: authentication

*Symptom:* `could not clone https://github.com/atate911/FamilyDB.git`, or
`Permission denied (publickey)`, or `could not read Username for 'https://github.com'`.

*What it means:* the repository is private and GitHub did not accept what it was given, so
nothing was fetched. Bootstrap removes the half-made directory, so there is nothing to clean up.

*How to check:*

```bash
ssh -T git@github.com -i ~/.ssh/familydb_deploy     # names the repository if the key works
git ls-remote https://x-access-token:$GITHUB_TOKEN@github.com/atate911/FamilyDB.git | head -1
```

*How to fix:* a deploy key must be the **private** half (`~/.ssh/familydb_deploy`, not the
`.pub`) and its public half must be on **this** repository's deploy keys, not on your account.
A token must not have expired and must have Contents: Read on this repository. If neither can
be made to work from the server, fall back to option 3 in section 3 and copy the code across
yourself; no credential is needed for that.

### "The familydb user cannot get into ..."

*Symptom:* the installer prints that the `familydb` user cannot get into the checkout, and does
not install the systemd unit. Or, after installing one by hand, `systemctl status familydb`
shows a permission error on the working directory.

*What it means:* the checkout is inside somebody's home directory. Home directories are mode
0750, so the service account cannot enter one, and no amount of unit hardening changes that.

*How to check:*

```bash
sudo -u familydb test -x /home/sam && echo reachable || echo "cannot enter /home/sam"
stat -c '%U:%G %a' /home/sam
```

*How to fix:* move it to `/opt/familydb`, which is where the unit expects it anyway:

```bash
sudo mkdir -p /opt/familydb
sudo cp -a /home/sam/FamilyDB/. /opt/familydb/
cd /opt/familydb && sudo scripts/install.sh
```

If you really want it under `/home`, the directory above it has to be traversable
(`chmod o+x /home/sam`) and the unit needs `ProtectHome=read-only` instead of
`ProtectHome=true`; the installer makes that substitution for you, but the traversal is yours
to fix. RUNBOOK section 2b.

### The service starts and then stops

*Symptom:* bootstrap says "The service started and then stopped", or
`systemctl is-active familydb` says `failed`.

*What it means:* almost always a setting it will not accept, or a file it cannot write.

*How to check, in this order:*

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb doctor
sudo systemctl status familydb
sudo journalctl -u familydb -n 50 --no-pager
```

*How to fix:* doctor names the thing and prints the fix under it. The three that bite are the
`familydb` user not owning `data/` and `.env`, a checkout in a home directory (above), and a
value in `.env` the settings will not take (below). Then `sudo systemctl restart familydb`.

### "a setting will not do"

*Symptom:* that line at startup, or from `familydb config`, naming one setting.

*What it means:* a value in `.env` is not of the type that setting takes. An empty line is
fine and means "not set"; it is a value like `WEB_PORT=eighty` that stops it.

*How to check:*

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb config
```

That prints every resolved setting and says where each came from.

*How to fix:* correct the line. Quote anything containing a space or a `#`, because a bare
value loses everything from the `#` onwards. A related line, `stored settings are not usable`,
means the offending value is in the database rather than `.env`, usually after an upgrade
narrowed what a setting takes: the bot keeps running on what `.env` says, and emptying that box
on `/settings` fixes it.

### "familydb could not start: Permission denied: '.env'"

*Symptom:* any `familydb` command run as yourself fails like that.

*What it means:* the installer handed `.env` and `data/` to the `familydb` user at the end, on
purpose, so the database stays owned by the account that writes it. You are not that user.

*How to fix:* run it as that user, from the install directory:

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb doctor
```

The working directory matters as well as the user: `.env` is read from the current directory.

### "cannot write" on the database, or database permission denied

*Symptom:* doctor reports `database writable: cannot write`, or the log shows
`attempt to write a readonly database`.

*What it means:* `data/` or the database file belongs to somebody other than the user running
the bot. Common after restoring a backup by hand, or after `familydb db migrate` was run as
root and left a root-owned file behind.

*How to check:*

```bash
ls -l /opt/familydb/data
```

*How to fix:*

```bash
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo systemctl restart familydb
```

On the Docker path the container runs as uid 1000 instead: `sudo chown -R 1000:1000
/opt/familydb/data`.

### No space left on device

*Symptom:* a step fails with that message, or doctor warns about free space, or the bot stops
being able to write.

*What it means:* the disk is full. SQLite cannot write, and neither can anything else.

*How to check:*

```bash
df -h /
sudo du -xh --max-depth=1 /var | sort -h | tail
```

*How to fix, biggest wins first:*

```bash
sudo journalctl --vacuum-size=200M
sudo apt-get clean
sudo docker system prune -af           # if Docker is installed
find /opt/familydb/backups -name 'familydb-*.sqlite3' -mtime +14 -delete
```

Then cap the journal for good: `SystemMaxUse=500M` in `/etc/systemd/journald.conf`, and
schedule the backup prune with `maintain.sh schedule-backups --keep-days 14`.

### "Could not get lock" from apt

*Symptom:* bootstrap stops with `Could not get lock /var/lib/dpkg/lock-frontend`.

*What it means:* another program is installing packages right now, and only one may at a time.
On a server that has just booted this is usually unattended-upgrades doing its first run.

*How to check:*

```bash
sudo fuser -v /var/lib/dpkg/lock-frontend
```

*How to fix:* wait a minute and run bootstrap again; it picks up where it stopped. If a
previous install was interrupted rather than merely busy, `sudo dpkg --configure -a` first.
Never delete the lock file by hand.

### Killed, or out of memory

*Symptom:* a step ends with `Killed` and no other explanation, usually while the virtualenv is
being built.

*What it means:* the kernel ran out of memory and stopped the command. On a 512 MB or 1 GB box
this is the single most likely failure.

*How to check:*

```bash
free -m
sudo dmesg -T | grep -i 'killed process' | tail
```

*How to fix:* add swap and run bootstrap again (section 2). Nothing is lost: everything that
had already worked is still in place.

### Cannot reach the model API

*Symptom:* "Saved your message, but I couldn't process it right now", or doctor's
`model reachable` says the API refused.

*What it means:* either the key is wrong or unpaid, or the machine cannot get out to the
internet at all. The message itself is safe: it is stored and retried every
`RETRY_INTERVAL_MINUTES` up to `RETRY_MAX_ATTEMPTS` times, and the answer is delivered when one
of those succeeds.

*How to check:*

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
curl -sS -o /dev/null -w '%{http_code}\n' https://api.anthropic.com/v1/models
sudo journalctl -u familydb -n 50 --no-pager | grep -i error
```

*How to fix:* a wrong key goes in `.env` or on `/settings`, where it takes effect immediately.
A network failure is usually DNS on a freshly booted VPS (`ping -c1 1.1.1.1`, then
`cat /etc/resolv.conf`) or a clock more than a day out, which breaks every certificate
(`date -u`, then `sudo timedatectl set-ntp true`). Retry the backlog by hand with
`familydb db retry-failed`, and `--reset` re-arms messages that gave up over a configuration
problem you have since fixed.

### The web page is unreachable from another machine

*Symptom:* the tunnel works, the browser on another device times out.

*What it means:* the page is bound to the loopback, which is the default and deliberate.

*How to check:*

```bash
sudo ss -ltnp | grep 8080
grep -E '^WEB_(ENABLED|HOST|PORT)=' /opt/familydb/.env
```

`127.0.0.1:8080` in that output means this machine only; `0.0.0.0:8080` means the network.

*How to fix:* on the virtualenv path, set `WEB_HOST=0.0.0.0` and a password of at least twelve
characters, then restart. On the Docker path change the `ports` line in `docker-compose.yml`
from `"127.0.0.1:8080:8080"` to `"8080:8080"` as well — both have to change. Then let the
firewall through. On a machine facing the internet, do section 6 instead and leave 8080 shut:
the page refuses to serve off the loopback with no password at all, unless you set
`WEB_ALLOW_NO_PASSWORD=true` on purpose.

### The page asks for the password again and again

*Symptom:* signing in works, and the next click asks again.

*What it means:* the login cookie is not coming back. Either the signing key cannot be stored,
so it changes on every start, or the cookie is marked `Secure` and the connection is not HTTPS,
or the reverse.

*How to check:*

```bash
ls -l /opt/familydb/data/web_secret
sudo journalctl -u familydb -n 50 --no-pager | grep -i web
```

*How to fix:* make sure `data/` is writable by the bot's user, or set `WEB_SECRET_KEY` in
`.env`, which is also what to do if you run the page in more than one process. Behind Caddy,
`WEB_TRUST_PROXY` must be `true` or the `Secure` cookie is never set. Changing `WEB_PASSWORD`
ends every session opened with the old one, on purpose, so everybody signs in once after that.

### `cache_read` stays 0

*Symptom:* `familydb db status` shows no cache reads however many messages go through, and
`familydb debug cost` says every message is paid for in full.

*What it means:* something volatile is in the cached prompt prefix, so the cache never matches.
Tokens are the running cost here, and this roughly doubles it.

*How to check:*

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb debug prompt "hi" > /tmp/a
sudo -u familydb .venv/bin/familydb debug prompt "hi" > /tmp/b
diff /tmp/a /tmp/b        # the system blocks and the tools list must be byte-identical
```

*How to fix:* if they differ, something with a date, a name or a per-request id has got into
the prefix, which is a bug worth reporting with that diff. If they match, check
`ANTHROPIC_CACHE_TTL` is still `1h`: at `5m` a family's gaps between messages are longer than
the cache. On OpenAI and Gemini the caching happens their side and this counter behaves
differently. RUNBOOK section 13.

### Port already in use

*Symptom:* `the web page is not serving: address already in use` in the log, and the bot keeps
running without a page.

*What it means:* something else already has that port. Often an older `familydb web` left in
the foreground, or a second copy of the bot.

*How to check:*

```bash
sudo ss -ltnp | grep ':8080'
```

*How to fix:* stop whatever holds it, or set `WEB_PORT` in `.env` to a free port. It must stay
above 1024: the service runs unprivileged in both Docker and systemd and cannot bind a low one.
A related symptom, `database is locked`, is the same mistake one layer down — two processes
writing at once. Only one `familydb run` may exist at a time; the CLI alongside it is fine.

### Everything looks right and it still does not answer

Work down doctor's list rather than guessing:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

`✗` first, then `!`. The usual answers are that nobody is in the `members` table for the
channel they are writing from ("Sorry, I only talk to the family", and the reply carries the id
to add), that there is no key for the chosen provider so another is standing in, or that the
bot is simply not running. RUNBOOK section 13 lists the rest, with the log line each one prints.
