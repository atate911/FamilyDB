# Installing FamilyDB on a server

This is the long way round: a bare VPS at the start, the family messaging the bot at the end.
It assumes nothing is installed and nothing is configured, and it explains why each step is
there, because most of them are only obvious once you have been bitten by the alternative.

`scripts/bootstrap.sh` does most of the work, and asks one question on the way. Everything
else, from the model key to Telegram and Google Calendar, is set up afterwards on the bot's own
web page, which lists what is left to do; those steps are here too.

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

**A way into the repository.** FamilyDB is private (section 3). Only the repository's owner can
add a deploy key or make a token scoped to it; if that is not you, ask the owner for one of the
two, or for a `.tar.gz` of the code (option 3), before you start.

**An API key** from OpenAI, Anthropic or Google. One is enough. OpenAI's GPT-6 Luna answers by
default, because it is the cheapest capable model of the three; the others are a setting away.
Give more than one key and the others become spares for when the first is rate limited (RUNBOOK
section 11). You type it on the web page after the install, not during it. While you are in the
provider's console, set a monthly spending limit on the key: the bot keeps its own daily limit
($2.00 by default), but that is an estimate, and the provider's figure is the bill.

**Optionally, a Telegram bot** so the family can message it from their phones, and **a Google
account** with a shared calendar. Neither is needed to get it running and both can be added
later from the page; without Telegram the family talks to it on the page's Chat.

**A domain, if** you want the family to reach the web page from their phones and other
machines, over HTTPS (section 6). Without one the page stays on the server and you reach it
over an SSH tunnel. The bot itself makes outgoing connections only.

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

If the provider set the server up for key-only logins, `ssh-copy-id` cannot get in as `sam` (no
password to type). Copy root's key across instead, as root on the server:

```bash
install -d -m 700 -o sam -g sam /home/sam/.ssh
install -m 600 -o sam -g sam /root/.ssh/authorized_keys /home/sam/.ssh/
```

With that working, in `/etc/ssh/sshd_config` set `PasswordAuthentication no` and
`PermitRootLogin no`, then `sudo systemctl reload ssh`. Ubuntu cloud images often carry a file in
`/etc/ssh/sshd_config.d/` (such as `50-cloud-init.conf`) that says `PasswordAuthentication yes`
and wins over the main file; set it to `no` there too. `sudo sshd -T | grep -i passwordauth`
shows what is actually in force.

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

**The timezone.** The bot works out what "this weekend" means from the family's timezone,
which the installer takes from the machine, so it is worth setting the machine first. The
settings page changes it later if you get it wrong:

```bash
timedatectl list-timezones | grep Vancouver
sudo timedatectl set-timezone America/Vancouver
```

**If the page will have a domain** (section 6), point it at the server and open the web ports
now, before the install: the installer sets up HTTPS, and the certificate can only be fetched
once the name leads here and ports 80 and 443 are open.

```bash
dig +short familydb.example.com      # should print this server's address
sudo ufw allow 80,443/tcp
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

On the server, make a key that exists for this one purpose. It lives in `/root`, because
upgrades run as root and read it from there for as long as the install exists:

```bash
sudo ssh-keygen -t ed25519 -C "familydb deploy" -f /root/familydb_deploy -N ""
sudo cat /root/familydb_deploy.pub
```

The `-N ""` matters: it makes the key without a passphrase. Upgrades fetch with this key on
their own, with nobody there to type one, so a key with a passphrase works for the install and
then stops every upgrade. Bootstrap notices one and offers to remove it; to do it yourself,
`sudo ssh-keygen -p -f /root/familydb_deploy -N ""`.

Copy that public line. In GitHub, open the repository's own page (not your account settings,
whose "SSH and GPG keys" would give the key every repository you can reach), then its
**Settings** tab, **Deploy keys** in the sidebar, and **Add deploy key**. The Settings tab is
only there for the repository's owner and admins, and on a narrow window it hides under the
**…** at the end of the tab row. Title it after the machine, paste the key, and leave **Allow
write access** unticked: the server never needs to push. Check it from the server:

```bash
sudo ssh -T git@github.com -i /root/familydb_deploy
# "Hi atate911/FamilyDB! You've successfully authenticated, but GitHub does not provide shell
#  access." is the answer you want.
```

Then fetch a copy for the scripts with that key, on the server, and run bootstrap from it.
Bootstrap still clones its own copy into `/opt/familydb` with the key, so upgrades can fetch.
Paste these one block at a time: bootstrap asks questions, and anything pasted after it is
read as the answer to the first one.

```bash
sudo git -c core.sshCommand="ssh -i /root/familydb_deploy -o IdentitiesOnly=yes" \
  clone --depth 1 git@github.com:atate911/FamilyDB.git /root/familydb-scripts
```

```bash
sudo bash /root/familydb-scripts/scripts/bootstrap.sh --deploy-key /root/familydb_deploy
```

Once it has finished, and not before, remove the copy:

```bash
sudo rm -rf /root/familydb-scripts
```

(Or, if you have a clone of your own: `scp -r scripts sam@your-server:~/` from it, and
`sudo bash ~/scripts/bootstrap.sh --deploy-key /root/familydb_deploy` on the server.)

Bootstrap rewrites the repository URL to its SSH form, clones with that key, and then clears
the credential out of the saved remote so nobody reading `.git/config` later finds one.

### Option 2: a fine-grained personal access token

In GitHub, **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
Generate new token**. Give it the shortest expiry you can live with, set **Repository access**
to **Only select repositories** and pick FamilyDB, and under **Permissions → Repository
permissions** set **Contents** to **Read-only**. Nothing else.

On the server, read the token in without it landing in your shell history, fetch the scripts
with it, and run bootstrap. `sudo` drops the environment unless told to keep that one variable:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN        # paste the token, then Enter
git clone --depth 1 "https://x-access-token:${GITHUB_TOKEN}@github.com/atate911/FamilyDB.git" ~/familydb-scripts
sudo --preserve-env=GITHUB_TOKEN bash ~/familydb-scripts/scripts/bootstrap.sh
```

Answer its questions, and once it has finished: `rm -rf ~/familydb-scripts`.

The token is used for the clone and nothing else: it is never written to `.env`, never written
to the log, and the saved remote is reset to the plain HTTPS URL afterwards so it does not sit
in `.git/config`. That also means an upgrade needs it again (section 8); switching to a deploy
key later avoids that.

### Option 3: copy it from your own computer

No credential reaches the server at all. On a computer that can read the repository, make an
archive of the committed code (which leaves out the virtualenv, the database and any `.env`,
because none of them are committed) and copy it across:

```bash
git clone git@github.com:atate911/FamilyDB.git ~/FamilyDB     # if you have no clone yet
git -C ~/FamilyDB archive --format=tar.gz --prefix=FamilyDB/ -o ~/familydb.tar.gz HEAD
scp ~/familydb.tar.gz sam@your-server:~/
```

Then on the server, unpack the scripts and point bootstrap at the archive:

```bash
tar -xzf ~/familydb.tar.gz
sudo bash ~/FamilyDB/scripts/bootstrap.sh --from ~/familydb.tar.gz
```

Copy the archive rather than a working directory: a `.env` of your own landing on the server
would carry your keys there, and the installer would take it for this machine's configuration.
If bootstrap is run from inside a checkout and given no deploy key and no token, it installs that
checkout, so `sudo bash ~/FamilyDB/scripts/bootstrap.sh` on its own does the same thing.

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
sudo bash /root/familydb-scripts/scripts/bootstrap.sh --deploy-key /root/familydb_deploy
```

Useful flags, all in `--help`. `--dry-run` says what would happen and changes nothing, which
is worth one pass. `--mode docker` installs Docker Engine and the compose plugin and runs it
that way; the default is `venv`, the smaller install and the one the rest of this file assumes.
`--target DIR` and `--user NAME` move the install and rename the service account. `--ref NAME`
installs that tag, branch or commit, and `--repo URL` clones from somewhere else. Without
`--ref`, what it installs depends on `CHANGELOG.md`: while the newest version there is marked "in
progress", as v0.1.0 is now, it installs the default branch, where that version is being built;
once the version carries a date instead, it installs the newest release tag. `--no-packages`
installs nothing with apt, `--no-install` stops before the questions, `--no-start` leaves it
stopped, and `--yes` takes every default and asks nothing, for a scripted build.

### What it changes, and what a good run looks like

Before it touches anything it prints a plan with a reason against each line: the packages, the
`familydb` user, the directory, the `.env` and database it would write, the unit it would
enable, and what it will not touch — your firewall, your SSH configuration, the system Python,
other services, home directories and inbound ports. Then it asks.

After that it works through apt packages (`ca-certificates curl git tzdata`), uv or Docker, the
code into `/opt/familydb` and the `familydb` user, then hands over to `scripts/install.sh`,
which asks one thing:

- **the domain name or public IP address for the web page**. With a domain, the page is served
  over HTTPS with a real certificate (section 6), which is also what lets the chat page use
  your phone's location. With the server's IP address and no domain, it is served over HTTPS
  with a certificate Caddy signs itself, which each browser warns about once. Left empty, the
  page stays on the server and you reach it from your own computer over an SSH tunnel.

You add yourself afterwards, on the page's Family page: it is the first line of the page's
setup list. Beyond that one question it asks only yes-or-no questions before it changes the machine: whether to
install the service, whether to schedule backups, and, with a domain or an IP address, whether
to set up Caddy.
Everything else it decides for you, and all of it can be changed on the page later:

- The web page is on, with a family password of at least twelve characters. It makes one up and
  **prints it once**: write it down. If it scrolled past, `sudo grep WEB_PASSWORD
  /opt/familydb/.env` shows it; that file is the only other place it is. To choose your own,
  run `sudo WEB_PASSWORD='...' bash .../bootstrap.sh ...` instead, and to change it later, see
  "Changing the family password" in section 5.
- The timezone is the machine's.
- Web lookups are on, so new ideas get their address and opening hours filled in.
- The weekend digest goes to the chat on the web page, which needs no setting up.
- With a domain, it turns on HTTPS through Caddy. On this, the virtualenv path, it asks before
  installing Caddy with apt and writing `/etc/caddy/Caddyfile` for your domain.
- `data/` is made readable by the `familydb` user alone, and it asks before scheduling a nightly
  backup at 03:15 in root's crontab, keeping two weeks (installing cron if the machine has none).

It finishes by starting the service and running `familydb doctor`, which prints a line per
check. A `✓` is something that was looked at and is fine. A `!` is usually something not set up
yet, which is normal on a first install: Telegram and the calendar are `!` until you do section
5. On a first install the model key is a `✗` until you type one on the page; any other `✗` must
be fixed before anything works. The last thing it prints is the page's address.

A transcript of the whole run is at `/var/log/familydb-bootstrap.log`, and how far it got is
at `/var/log/familydb-bootstrap.progress`. Running it again is safe: it installs what is
missing, leaves an existing `/opt/familydb` alone, and says where the last run stopped.

## 5. Finish the setup

Everything in this section is done on the web page, and none of it needs a file edited or a
restart. The one exception is the laptop route for Google Calendar, kept as a fallback.

### Open the page

With a domain, go to `https://your.domain/` once the domain points at the server and ports 80
and 443 are open (section 6). With the server's IP address, go to `https://<the address>/` and
accept the certificate warning once.

Left empty, the page is bound to `127.0.0.1` on the server. That does not mean you have to sit
at the server: an SSH tunnel carries it to your own computer, from anywhere, without opening a
single port. Run this **on your own computer**, not in the server's terminal, with your user
and the server's address in place of `sam` and the example address (the installer's last lines
print the exact command):

```bash
ssh -L 8080:127.0.0.1:8080 sam@203.0.113.7
```

Leave that connected and go to `http://127.0.0.1:8080/` in a browser on the same computer. It
is the server's page. On Windows the same command works in PowerShell. To open the page by
address instead, with no tunnel, see section 6.

Sign in with the family password the installer printed. The home page has a **Finish setting
up** list of what is missing, most important first, and each line links to where it is done.
Work down it; it disappears when everything is done. The first line is adding yourself on the
Family page, as an admin; add the rest of the family there too. The rest of this section is
those lines in more detail.

### Changing the family password

It lives in `.env`, not on the settings page, so a form cannot change the lock on its own door:

```bash
sudoedit /opt/familydb/.env        # WEB_PASSWORD=, twelve characters or more
sudo systemctl restart familydb
cd /opt/familydb && sudo -u familydb .venv/bin/familydb doctor
```

Keep it to twelve characters or more. A shorter one is refused for a page anything but the
server can reach, and the refusal is quiet: the bot keeps running, the page does not, and
through Caddy the browser shows a 502. `familydb doctor` says so on its "web page" line, which
is why it is the third command. Changing it signs everybody out once.

### A model key

Settings, **API keys**. Paste the key for the company that answers (OpenAI, unless you changed
it) and press Save keys. It takes effect on the next message. One consequence worth knowing: a
key stored there lives in `data/familydb.sqlite3`, so it is in every backup, and a key in `.env`
is not. Either is fine on a machine you control; if the backups go somewhere you do not, put the
keys in `.env` instead and restart (RUNBOOK sections 7 and 11). The page never shows a key back
except through "See a key", which asks for the family password again.

Then check the daily spending limit under **What it may spend**: $2.00 a day by default, an
estimate across every model call. Once it is used up the bot says so and stops asking a model
until midnight. 0 turns it off.

### Where home is

Settings, **Home**. Type the home area as you would tell someone, such as `Vancouver, WA`, leave
latitude and longitude empty, and save. The page looks the place up on OpenStreetMap's map,
fills the coordinates in, and says what it found. If it finds nothing, or the wrong town, type
the coordinates yourself; typed ones win. Units and the timezone are in the same group.

### Google Calendar

The Google Cloud side is done once, in a browser. RUNBOOK section 5 has it step by step, and the
settings page repeats it: a project, the Google Calendar API turned on, the OAuth consent screen
set to External and **In production**, and an OAuth client of type **Desktop app**, whose JSON
you download. The "In production" part bites a week later if you miss it: left in Testing,
refresh tokens expire after seven days and the bot quietly stops writing to the calendar.

Then, on the settings page under **Google Calendar**:

1. Paste the client's JSON and press **Get the consent link**.
2. Open the link, sign in as the account that owns the family calendar, and allow access. Google
   may warn that the app is unverified; it is your own, so go on.
3. Google sends the browser to an address starting `http://127.0.0.1:53682/`, which **will not
   load**. That is expected. Copy the whole address from the address bar, paste it into the page,
   and press **Connect**. Do it within a quarter of an hour and without restarting the bot in
   between, or start again.
4. Choose the family calendar from the list. Calendars you can only read are marked, because
   plans cannot be added to them.

This way of connecting has not yet been tried against a live Google account, so try it first,
and if it will not connect, do the sign-in on a laptop instead:

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

Put the calendar id in the **Google calendar id** box (under Home) and restart
(`sudo systemctl restart familydb`). Either way, check it:

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb google events
```

### Telegram

RUNBOOK section 4 is the full version. In short: send `/newbot` to @BotFather, copy the token it
gives you, and paste it on the settings page under **API keys** as the Telegram bot token. It
takes effect within seconds. `/status` then says "connected as @yourbot"; if it says "the token
was refused by Telegram", the token was mistyped.

Then each person sends the bot a message. It will not answer them yet, but it notes who asked:
the **Family** page lists them under "Asked to talk to the bot", with their Telegram name and a
button to add them (it keeps who and when, never what they said, and forgets them after a
month). For someone already on the list, press Change beside their name instead and type the id
the bot's reply gave them. Their next message gets a real answer. Kids need no id: the kid role is enough for them to be named as
participants. For a family group, `/setprivacy` → Disable in BotFather, then add the bot to the
group.

### The weekend digest

The Thursday digest goes to the chat on the web page, which works from the first week. To send
it to the family's Telegram group instead, add the bot to the group and have somebody on the
family list mention it there once (`@yourbot hello`). Then the **Digest chat** box on the
settings page (under "When it speaks first") offers that group, by the time it was last written
in; pick it and save. The day and the hour are in the same place. `familydb digest` prints the schedule and `familydb digest --now` posts
one immediately. RUNBOOK section 9.

## 6. Putting the web page on the internet properly

The tunnel in section 5 is the safest way and costs nothing. A domain is what lets the family
use the page from their phones. Plain HTTP would send the family password in the clear, so with
a domain the page goes behind Caddy with a real certificate, and the installer sets that up.
With no domain, the server's IP address works too (below), at the cost of a certificate warning.

**DNS first.** An A record for `familydb.example.com` pointing at the server's address, and an
AAAA record if it has IPv6. Check it has propagated before Caddy asks for a certificate, or the
request fails: `dig +short familydb.example.com`. Then give that name when the installer asks
for a domain.

**The firewall.** Open 80 and 443, and nothing else:

```bash
sudo ufw allow 80,443/tcp
sudo ufw status
```

Do not open 8080. The page listens on `127.0.0.1` so that Caddy, and only Caddy, can reach it;
the firewall is the second lock on the same door.

**What the installer wrote.** In `.env`:

```
WEB_ENABLED=true
WEB_HOST=127.0.0.1
WEB_PASSWORD=...
WEB_TRUST_PROXY=true
WEB_DOMAIN=familydb.example.com
```

and, if you said yes, `/etc/caddy/Caddyfile` from `deploy/Caddyfile` with your domain in it.
Caddy fetches the certificate itself once the domain points at the server and the ports are
open; `sudo journalctl -u caddy -n 50` says how that went. On the Docker path it writes
`COMPOSE_PROFILES=tls` instead, so every `docker compose up -d` also starts a Caddy container.
If nginx is already on the machine, `deploy/nginx-familydb.conf` does the same job with a
certificate from certbot; the steps are at the top of that file.

`WEB_TRUST_PROXY=true` makes the page believe the forwarding headers from exactly one proxy
(Caddy on this machine, or the Caddy container on the Docker path), to learn the real visitor
address and that the connection was HTTPS, and marks the login cookie `Secure`. Behind a proxy
the page will not serve without a password at all.

**Adding a domain later.** If you installed without one, point the domain here and open the
ports (section 2), then `sudoedit /opt/familydb/.env` (the file is the service
user's alone) and fill in the two lines already there: `WEB_DOMAIN=your.domain` and
`WEB_TRUST_PROXY=true`. Set up Caddy as the top of `deploy/Caddyfile`
says (`sudo apt install caddy`, copy the file, put your domain in it, reload Caddy), open the
firewall as above, and `sudo systemctl restart familydb`. On the Docker path, add
`COMPOSE_PROFILES=tls` as well and run `docker compose up -d` instead of installing Caddy.

**No domain: the server's IP address.** Give the installer the server's public IPv4 address
instead of a domain (virtualenv path only). It writes `WEB_DOMAIN=<the address>` and
`WEB_TRUST_PROXY=true`, and a Caddyfile with `tls internal` in it:

```
203.0.113.7 {
	tls internal
	reverse_proxy 127.0.0.1:8080
}
```

`tls internal` has Caddy sign the certificate itself rather than ask a public authority, so the
connection is encrypted but every browser warns the first time, once per device: in Firefox
**Advanced → Accept the Risk and Continue**, in Chrome **Advanced → Proceed**. The error
Caddy logs about failing to install its root certificate is harmless; it only means the server
itself does not trust that certificate, which it never needs to. Open 80 and 443 as above. To
do this on an install made without it, write that Caddyfile to `/etc/caddy/Caddyfile` after
`sudo apt install caddy`, set the two lines in `.env`, `sudo systemctl reload caddy` and
`sudo systemctl restart familydb`. A domain later replaces the address on the first line, and
the `tls internal` line goes.

**Nothing answers from outside.** If `curl -skI https://<address>/` run on the server itself
gets an answer but the browser times out, the server is fine and something in between is
not. Most VPS providers have a firewall of their own, set in their control panel and called a
security group or cloud firewall, that `ufw` knows nothing about; open 80 and 443 there too. A
**502** is the other way round: Caddy is reached and the page behind it is not serving, which
is nearly always the password (section 5, "Changing the family password") and which
`sudo journalctl -u familydb -n 40 | grep 'not serving'` names.

**The warning worth reading twice.** One shared password is all that stands between a stranger
and your API bill. Signing in is the whole bot: chatting with it spends tokens, the forms add and
change ideas and put things on the family calendar, the Family page decides who may message the
bot on Telegram, and the settings page can change which model answers, raise the spending
limit, show a key to anyone who knows the password, and point the bot at a different calendar.
Make the password long, set a spending limit on the API key with the provider, and look at
`/status` now and then for a month that does not look like yours. RUNBOOK section 10 has what
else protects the page: lockouts, CSRF tokens and a content security policy. If a phone goes
missing, "Sign everyone out" on the settings page ends every sign-in on every device.

## 7. Check it works end to end

The one command that looks at everything:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

That runs `familydb doctor`, which checks the settings, `.env`'s permissions, the disk, the
database and its schema, who is in the family, the keys, the models, Telegram, the calendar,
the weather, the lookups, the digest, the web page and the service, and prints a fix under
anything that is wrong. `--online` also asks Telegram whether its token works, and asks Claude or
Gemini whether their key works by counting tokens, which is free. OpenAI, the default, has no
free way to ask, so there the first real message is the check:

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

Then a real message, on the page's Chat, from a phone over Telegram, or from the server:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb chat "we should try that new ramen place on Main St sometime"
sudo -u familydb .venv/bin/familydb chat "tell me about #1"
sudo -u familydb .venv/bin/familydb db status
```

`db status` should show `cache_read` greater than zero on the second call: the prompt cache is
working and most of each message is not being paid for twice. If it stays zero, section 10.

Finally `/status` in the browser: which model answers chat and which does the lookups, whether
each key is set and where it came from, whether Telegram is connected, what else is connected,
what today has cost against the daily limit, what the last thirty days cost per purpose and per
model, which part of each request the tokens went on, and what is waiting. It asks nothing of a model, so refreshing it is free.

## 8. Day to day

`scripts/maintain.sh` is the one to remember:

```bash
sudo /opt/familydb/scripts/maintain.sh status             # running? healthy? last backup?
sudo /opt/familydb/scripts/maintain.sh check              # the full check, with fixes
sudo /opt/familydb/scripts/maintain.sh logs 200           # follow the log
sudo /opt/familydb/scripts/maintain.sh restart
sudo /opt/familydb/scripts/maintain.sh backup
sudo /opt/familydb/scripts/maintain.sh restore FILE       # stops it, puts it back, starts it
sudo /opt/familydb/scripts/maintain.sh upgrade            # newer code, backup taken first
```

`restore` backs up the database it is about to replace, so a restore can itself be undone.
`upgrade` takes a backup, fetches, moves to the newer code, reinstalls the locked dependencies,
migrates and restarts, and prints the command to go back if it went badly. It follows the same
rule as bootstrap: the default branch while `CHANGELOG.md` marks the newest version "in
progress", and the newest release tag once that version has a date. It only ever moves forward:
if the target does not contain what is installed now, it refuses and changes nothing. Do not use
`git pull` instead; the checkout is on a detached commit, where it fails.

**Upgrades on a private repository.** `upgrade` fetches from `origin`, which needs a credential.

If you installed with `--deploy-key`, bootstrap already wired it up: it left the SSH remote in
place and recorded the key's path in the checkout's `core.sshCommand`, so upgrades work as long
as that key file stays where it is (`/root/familydb_deploy`, if you followed section 3).

If you installed with a token, bootstrap deliberately did not write it down, so give it again
for each upgrade; it is used for that fetch and not kept:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN
sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade
```

Tokens expire. To stop needing one, make a deploy key as in section 3 and point the checkout at
it once:

```bash
sudo git -C /opt/familydb remote set-url origin git@github.com:atate911/FamilyDB.git
sudo git -C /opt/familydb config core.sshCommand \
  "ssh -i /root/familydb_deploy -o IdentitiesOnly=yes"
sudo git -C /opt/familydb fetch --tags origin      # should now work
```

If you brought a copy yourself there is nothing to fetch from at all. Take a backup, make a new
archive as in section 3, copy it across, and unpack it over the install; `.env` and `data/` are
not in the archive, so they are left as they are. Then run the installer again, which
reinstalls the dependencies, migrates and restarts:

```bash
sudo /opt/familydb/scripts/maintain.sh backup
sudo tar -xzf ~/familydb.tar.gz -C /opt/familydb --strip-components=1 --no-same-owner
sudo bash /opt/familydb/scripts/install.sh
```
 `upgrade` says all of
this itself when a fetch fails, so you do not have to remember it. RUNBOOK section 8 says
which version an upgrade moves to.

**Backups, nightly and off the machine.** The database is one file and everything the family
has ever said is in it. If you said yes during the install, the nightly backup is already
scheduled; check, or schedule it now:

```bash
sudo crontab -u root -l
sudo /opt/familydb/scripts/maintain.sh schedule-backups --keep-days 14
```

That is one line in root's crontab, for either Docker or systemd: a safe SQLite online backup
at 03:15 into `/opt/familydb/backups/`, followed by pruning files older than `--keep-days` only
if the backup succeeds. Each backup is readable by its owner alone. An older schedule in the
`familydb` user's crontab is removed at the same time, so the two do not both run. A backup on
the same disk is not a backup, so copy them off as well. They are readable by root alone, so
hand yourself a bundle on the server and fetch that:

```bash
sudo tar -C /opt/familydb -czf ~/familydb-backups.tar.gz backups && sudo chown sam ~/familydb-backups.tar.gz
scp sam@your-server:familydb-backups.tar.gz .       # on your own computer
```

**The family password** lives in `.env`, not on the page, so that a stolen sign-in cannot change
it: `sudoedit /opt/familydb/.env`, change `WEB_PASSWORD`, then
`sudo systemctl restart familydb`. Everyone signs in again with the new one.

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
sudo ssh -T git@github.com -i /root/familydb_deploy   # names the repository if the key works
git ls-remote https://x-access-token:$GITHUB_TOKEN@github.com/atate911/FamilyDB.git | head -1
```

*How to fix:* a deploy key must be the **private** half (`/root/familydb_deploy`, not the
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
curl -sS -o /dev/null -w '%{http_code}\n' https://api.openai.com/v1/models   # 401 means reachable
sudo journalctl -u familydb -n 50 --no-pager | grep -i error
```

*How to fix:* a wrong key goes on `/settings`, where it takes effect immediately, or in `.env`.
If the reply is instead "Today's spending limit ... is used up", nothing is wrong: the daily
limit was reached, and RUNBOOK section 13 says what to do.
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
firewall through. On a machine facing the internet, give it a domain or its IP address behind
Caddy instead (section 6) and leave 8080 shut:
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
or pressing "Sign everyone out" ends every session, on purpose, so everybody signs in once after
that.

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
