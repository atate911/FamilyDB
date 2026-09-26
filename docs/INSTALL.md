# Installing FamilyDB

Three steps, about twenty minutes. No Linux knowledge is needed: the installer does the server
side and says what it is doing as it goes, and the web page walks you through the rest.

**You need**

- A server with Ubuntu 24.04 or 26.04, or Debian 12, and at least 1 GB of memory. The smallest
  plan at most VPS providers will do. You need to be able to log in to it; as root is fine.
- To be signed in to GitHub as the owner of the FamilyDB repository.
- A card for the AI company, which charges a few dollars a month for a family. Step 3 says where.

<details>
<summary>Do I need to create a user, set up SSH keys, open ports or edit any files?</summary>

No. The installer:

- creates FamilyDB's own account, `familydb`, which runs the bot and owns its data and nothing
  else. Nobody logs in as it.
- makes the one key it needs to read the code.
- puts HTTPS in front of the page.
- opens ports 80 and 443 if the server's own firewall is on.
- schedules a nightly backup.

The list, with the reason for each, is under
[What the installer changes](#what-the-installer-changes-and-why). Keeping the server itself up to
date is ordinary server care rather than part of FamilyDB:
[Looking after the server itself](#looking-after-the-server-itself) has it.
</details>

## 1. Install it (about 10 minutes)

Log in to the server. Copy this whole block, paste it into the terminal, and press Enter:

```bash
sudo bash -c 'set -e
key=/root/familydb_deploy; code=/root/familydb-code; notes=/var/lib/familydb-install
bold() { printf "\n\033[1m%s\033[0m\n" "$*"; }
mkdir -p $notes && chmod 700 $notes
bold "FamilyDB, step 1: letting this server read the code"
echo "The code is in a private GitHub repository. This makes a key that can read that one"
echo "repository and nothing else, and shows you where to give it to GitHub."
if ! command -v git >/dev/null; then
  before=$(dpkg -l | awk "/^ii/ {print \$2}")
  apt-get update -qq && apt-get install -y -qq git
  dpkg -l | awk "/^ii/ {print \$2}" | grep -vxF "$before" | sed "s/^/package\t/" >> $notes/ledger || true
fi
if [ ! -f $key ]; then
  ssh-keygen -q -t ed25519 -N "" -C "familydb@$(hostname)" -f $key
  printf "file\t%s\n" $key $key.pub >> $notes/ledger
fi
bold "On GitHub, signed in as the owner of the repository:"
echo "  1. Open https://github.com/atate911/FamilyDB/settings/keys/new"
echo "  2. Title: familydb"
echo "  3. Key: copy the whole line below and paste it in"
echo
cat $key.pub
echo
echo "  4. Leave Allow write access unticked, and press Add key."
ssh="ssh -i $key -o IdentitiesOnly=yes -o UserKnownHostsFile=$notes/known_hosts -o StrictHostKeyChecking=accept-new"
tries=0
until out=$(rm -rf $code && git -c core.sshCommand="$ssh" clone -q --depth 1 git@github.com:atate911/FamilyDB.git $code 2>&1); do
  if [ $tries -gt 0 ]; then
    case "$out" in
      *"Could not resolve"*|*"timed out"*|*"Network is unreachable"*)
        echo "  This server cannot reach GitHub: check its internet connection." ;;
      *)
        echo "  GitHub did not take the key yet. Check that the whole line was pasted (it starts"
        echo "  with ssh-ed25519) and that Add key was pressed. It can take a few seconds." ;;
    esac
  fi
  tries=$((tries + 1))
  read -r -p "  When that is done, press Enter here (Ctrl-C to stop): " _ </dev/tty
done
bold "GitHub took the key. Installing FamilyDB: about five minutes."
FAMILYDB_AGAIN="paste the same block again" bash $code/scripts/bootstrap.sh --deploy-key $key </dev/tty
rm -rf $code'
```

First it deals with the one thing it cannot do by itself, which is letting the server read the
code. It shows a link and a line of text. On GitHub, paste the line and press **Add key**, then
press Enter on the server. After that it installs everything, and asks only two things:

- whether to go ahead, once it has listed what it will change;
- whether you have a domain name for the page. Press Enter if you don't.

<details>
<summary>What if something goes wrong?</summary>

It stops, and says what went wrong and what to do about it. Once that is sorted, paste the same
block again: it keeps what already worked and carries on from where it stopped.
Everything it did is written to `/var/log/familydb-bootstrap.log`, which is the file to send if
you need someone to look.

If the terminal says `sudo: command not found`, you are logged in as root: paste the block again
without its first word, `sudo`.
</details>

<details>
<summary>Why a key, and what can it do?</summary>

The code is in a private repository, so GitHub needs proof that this server may read it. This
key can read that one repository and nothing else. It cannot change anything, and it cannot see
your other repositories or your account. It stays in `/root/familydb_deploy` so that upgrades can
fetch new versions. To take the server's access away, delete it on GitHub under the repository's
**Settings → Deploy keys**.
</details>

## 2. Open the page (1 minute)

The installer ends with an address and a password:

```
FamilyDB is running. Open this in any browser, on any computer or phone:

    https://203.0.113.7/
    password: Ji8N03YVMvRQ7qk8N2ga
```

Open the address and sign in with that password.

<details>
<summary>The browser says the connection is not private</summary>

FamilyDB could not get a certificate from a public authority, so it made its own. The
connection is still encrypted. Choose **Advanced**, then **continue** (or **Accept the risk**).
Each browser asks once.

To get rid of the warning, give it a domain name: see
[A domain name instead of the address](#a-domain-name-instead-of-the-address). If the installer
said nothing outside could reach the server, fix that first (the next question).
</details>

<details>
<summary>The page does not open at all</summary>

Almost always, your server provider has a firewall of its own that blocks the page. It lives in
the provider's control panel, and may be called a firewall, a security group or networking.
Allow incoming TCP on ports **80** and **443**. Then, on the server:

```bash
sudo /opt/familydb/scripts/maintain.sh https
```

That also gets the page a real certificate, if the first try could not. More in
[Troubleshooting](#the-page-does-not-open).
</details>

## 3. Follow the setup on the page (10 to 15 minutes)

The page opens on its setup, which has seven short steps in order. Each step says why it matters
and what to do, with links straight to the right place. The first two put you on the family list
and give you a password of your own, which replaces the one above: from then on everybody signs
in as themselves, and you give each of them a starting password on the Family page.

| Step | | What you will need |
|---|---|---|
| Yourself | needed | your name |
| Your own password | recommended | |
| An AI model | needed | an account with OpenAI (the cheapest), Anthropic or Google |
| Where home is | recommended | your town |
| Telegram | optional | Telegram on your phone |
| The rest of the family | optional | |
| Google Calendar | optional, 15 minutes | the Google account that has the family calendar |

You can skip any step and come back to it later; the home page lists what is left. That is the
whole install.

---

# Reference

Everything below is for doing something differently, or for when something goes wrong. None of
it is needed for the three steps above.

- [What the installer changes, and why](#what-the-installer-changes-and-why)
- [A domain name instead of the address](#a-domain-name-instead-of-the-address)
- [Keeping the page off the internet](#keeping-the-page-off-the-internet)
- [Other ways to get the code onto the server](#other-ways-to-get-the-code-onto-the-server)
- [Check it works end to end](#check-it-works-end-to-end)
- [Day to day](#day-to-day)
- [Removing it](#removing-it)
- [Troubleshooting](#troubleshooting)
- [Looking after the server itself](#looking-after-the-server-itself)

## What the installer changes, and why

Before it changes anything, it lists these and asks. In the order it does them:

| What | Why |
|---|---|
| Installs `git`, `curl`, `ca-certificates` and `tzdata` if they are missing | to fetch the code, to check HTTPS certificates, and to know what "this weekend" means where you live |
| Installs `uv` into `/usr/local/bin` | it fetches the Python this program needs and builds its virtualenv. The system Python is not changed |
| Creates a system account, `familydb`, with no password and no login | the bot runs as this account, not as root or as you. A mistake in it cannot reach the rest of the machine |
| Puts the code in `/opt/familydb` | one directory holds the program, its configuration and the database, which keeps backing it up and removing it simple |
| Writes `/opt/familydb/.env`, readable only by `familydb` | the first password and the page's address are kept there. Everything else is set on the page |
| Creates the database, `/opt/familydb/data/familydb.sqlite3` | everything the family tells it lives in that one file |
| Writes and enables `/etc/systemd/system/familydb.service` | so it starts when the machine boots, and restarts if it ever stops |
| Installs Caddy and writes `/etc/caddy/Caddyfile` | Caddy puts HTTPS in front of the page and renews its certificate, so the password never crosses the network in the clear |
| Opens ports 80 and 443 in `ufw`, if `ufw` is on | so browsers can reach the page. The bot needs nothing else inbound |
| Adds a nightly backup to root's crontab, kept for two weeks, in `/opt/familydb/backups` | so a bad day can be undone |

It does not touch your SSH configuration, the system Python, any other service, or anything in a
home directory. Running it again is safe: it installs only what is missing, keeps `.env` and the
database, and picks up where a failed run stopped.

<details>
<summary>Why /opt, and not a home directory?</summary>

The bot runs as its own account, and on Debian and Ubuntu that account cannot enter anyone's home
directory. A service pointed at a copy in `/home/sam` would stop the moment it started. The
installer checks for this and refuses to install a service it knows cannot run.
</details>

<details>
<summary>The installer's options</summary>

`bootstrap.sh --help` lists them all:

- `--dry-run` says what would happen and changes nothing.
- `--local-only` keeps the page off the internet (see
  [Keeping the page off the internet](#keeping-the-page-off-the-internet)).
- `--mode docker` runs it in Docker instead of a virtualenv.
- `--target DIR` and `--user NAME` move the install and rename its account.
- `--ref NAME` installs a particular tag, branch or commit.
- `--yes` takes every default, for a scripted build.

Which version it installs without `--ref` depends on `CHANGELOG.md`. While the newest version
there is marked "in progress", as v0.1.0 is now, it installs the default branch; once that
version has a date, it installs the newest release tag.
</details>

## A domain name instead of the address

A domain name gets rid of the certificate warning for good, and is easier to remember than an
address.

1. Where you bought the name, add an **A record** for it, such as `family.example.com`, that
   points at the server's address. On the server, `dig +short family.example.com` prints that
   address once it has taken effect: usually minutes, sometimes an hour.
2. On the server:

   ```bash
   sudo /opt/familydb/scripts/maintain.sh https family.example.com
   ```

That points Caddy at the name, gets its certificate, and restarts FamilyDB to match. Typing the
name when the installer asks for one does the same thing at install time.

<details>
<summary>What it sets</summary>

In `/opt/familydb/.env`: `WEB_DOMAIN` (the name, or the address when there is none),
`WEB_PUBLIC_PORT` (443 unless moved, below), `WEB_TRUST_PROXY=true` and `WEB_HOST=127.0.0.1`. The page then listens only to Caddy on the same
machine, and believes Caddy about who is visiting and that the connection was HTTPS, which is what
keeps the lockout per visitor and marks the sign-in cookie `Secure`. Caddy's configuration is
`/etc/caddy/Caddyfile`; `sudo journalctl -u caddy -n 50` says how getting the certificate went.
Port 8080 is never opened to the outside.

On the Docker path, set `WEB_DOMAIN` and `COMPOSE_PROFILES=tls` in `.env` and run
`docker compose up -d`, which starts a Caddy container as well. If nginx is already on the
machine, `deploy/nginx-familydb.conf` does Caddy's job with a certificate from certbot; the steps
are at the top of that file.
</details>

<details>
<summary>A port that scans rarely try</summary>

Port 8080 is never what a scan of the server finds: the page listens only to Caddy, on the same
machine. What a scan finds is Caddy on 443, the port every sweep of the internet looks at. To
serve the page on another port instead:

```bash
sudo /opt/familydb/scripts/maintain.sh https --port random
```

It prints the new address, `https://your.domain:PORT/`, which is the one to bookmark from then
on, and opens that port in `ufw`; allow it in your provider's own firewall too, if it has one.
Port 80 stays open, because that is where a certificate authority checks the server, but nothing
there points anyone at the page. `--port 443` moves it back. This keeps the page out of the scans
that try the usual ports; a scan of every port on your server would still find it, so it is no
substitute for good passwords. RUNBOOK section 10 says more, and how to keep the page off the
internet altogether.
</details>

<details>
<summary>The warning worth reading twice</summary>

The family's passwords are all that stand between a stranger and your API bill. Signing in as a
parent (or, for now, a kid) is most of the bot: chatting spends tokens, and the forms change ideas and put things on the
family calendar. Signing in as an admin is all of it: the Family page decides who may message the
bot on Telegram and who signs in, and the settings page can change which model answers, raise the
spending limit, show a key to that admin, and point the bot at a different calendar. Keep the
admins few and their passwords long, set a spending limit on the API key with the company too,
and look at `/status` now and then for a month that does not look like yours. If a phone goes
missing, make its owner a new starting password on the Family page, which signs them out on every
device; **Sign everyone out** on the settings page ends every sign-in there is. RUNBOOK section 10
has what else protects the page: lockouts, CSRF tokens and a content security policy.
</details>

## Keeping the page off the internet

To have the page reachable only from the server itself, add `--local-only` to the installer
(at the end of the `bootstrap.sh` line in the block). You then reach it from your own computer over
an SSH tunnel, from anywhere you can log in to the server. On your own computer, not on the server:

```bash
ssh -L 8080:127.0.0.1:8080 you@203.0.113.7
```

While that stays connected, `http://127.0.0.1:8080/` in a browser on the same computer is the
server's page. On Windows the same command works in PowerShell. To move to a link anyone can
open later: `sudo /opt/familydb/scripts/maintain.sh https`.

## Other ways to get the code onto the server

The block in step 1 makes a deploy key and uses it. These are the ways to do the same by hand,
or without putting any credential on the server at all.

| Way | What is on the server | Best for |
|---|---|---|
| Deploy key | one SSH key, read-only, valid for this repository alone | a server you keep, and the default choice |
| Token | a token that can read every repository it was scoped to | getting going quickly |
| Copy it yourself | nothing at all | a server you do not want to trust with anything |

### A deploy key, by hand

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

Copy that public line and open
[github.com/atate911/FamilyDB/settings/keys/new](https://github.com/atate911/FamilyDB/settings/keys/new),
which is the repository's **Settings → Deploy keys → Add deploy key**. Only the repository's
owner and admins can open it. Your account's own "SSH and GPG keys" is a different place, and a
key there would reach every repository you can. Give it a title, paste the key, and leave
**Allow write access** unticked: the server never needs to push. Check it from the server:

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

### A fine-grained personal access token

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
in `.git/config`. That also means an upgrade needs it again ([Day to day](#day-to-day)); switching to a deploy
key later avoids that.

### Copy it from your own computer

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

## Check it works end to end

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
working and most of each message is not being paid for twice. If it stays zero, see [Troubleshooting](#troubleshooting).

Finally `/status` in the browser: which model answers chat and which does the lookups, whether
each key is set and where it came from, whether Telegram is connected, what else is connected,
what today has cost against the daily limit, what the last thirty days cost per purpose and per
model, which part of each request the tokens went on, and what is waiting. It asks nothing of a model, so refreshing it is free.

## Day to day

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
as that key file stays where it is (`/root/familydb_deploy`).

If you installed with a token, bootstrap deliberately did not write it down, so give it again
for each upgrade; it is used for that fetch and not kept:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN
sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade
```

Tokens expire. To stop needing one, make a deploy key as in [A deploy key, by hand](#a-deploy-key-by-hand) and point the checkout at
it once:

```bash
sudo git -C /opt/familydb remote set-url origin git@github.com:atate911/FamilyDB.git
sudo git -C /opt/familydb config core.sshCommand \
  "ssh -i /root/familydb_deploy -o IdentitiesOnly=yes"
sudo git -C /opt/familydb fetch --tags origin      # should now work
```

If you brought a copy yourself there is nothing to fetch from at all. Take a backup, make a new
archive as in [Copy it from your own computer](#copy-it-from-your-own-computer), copy it across, and unpack it over the install; `.env` and `data/` are
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

**Passwords** are chosen on the page, each person their own, and stored only as hashes. Somebody
who forgot theirs gets a new starting password from an admin on the Family page. If the only admin
forgot theirs, `sudo /opt/familydb/scripts/maintain.sh password` prints a new starting password
for them (`password NAME` does it for somebody else). `WEB_PASSWORD` in `.env` is only the
installer's, for signing in the first time; it opens nothing once an admin has their own.

RUNBOOK section 7 covers restoring by hand and what is and is not inside a backup; section 12
covers journald limits, disk, and what to do when a secret gets out.

## Removing it

Three levels, from gentle to everything.

| Command | Removes | Keeps |
|---|---|---|
| `sudo /opt/familydb/scripts/uninstall.sh` | the service and the installed program | `.env`, the database, the backups: reinstalling picks up where it left off |
| `... uninstall.sh --purge` | all of FamilyDB, including the database and its `familydb` account | a backup of the database, in `/var/backups/familydb` |
| `... uninstall.sh --from-zero` | all of that, and everything the install did around it | nothing, unless `--backup-to DIR` is given |

`--from-zero` puts the server back as it was before FamilyDB, for trying the install again from
the beginning. The installer writes down every change it makes as it makes it, in
`/var/lib/familydb-install`: each package it added (not ones that were there already), each file,
folder and link, the accounts, the cron line and the firewall rule, and a copy of any file it
replaced. `--from-zero` undoes exactly that, and puts replaced files back. For an install made
before that record existed, it also looks for everything older versions and the older guide's
steps by hand could leave: Caddy when it serves nothing but FamilyDB, uv and the line its
installer added to root's shell profiles, the deploy key, copies of the code and backups in home
directories, GitHub in root's `known_hosts`, and the logs.

Like `--purge`, it asks twice before removing anything: a yes-or-no question after listing,
by name, everything it will remove (Enter means no), then typing `remove everything` in full.
`--dry-run` shows the list and removes nothing.

<details>
<summary>The details</summary>

- It removes Caddy only when Caddy serves nothing but FamilyDB. Otherwise Caddy stays, and it
  says which site to take out of `/etc/caddy/Caddyfile`.
- It refuses to touch a directory that does not contain FamilyDB's `pyproject.toml`, and refuses
  system directories outright. It runs from a copy of itself, so it can remove `/opt/familydb`
  along with the script inside it.
- `--backup-to DIR` puts the backup somewhere else. `--no-backup` skips it, which you should
  only say deliberately. `--keep-user` leaves the `familydb` account alone. `--force` skips both
  questions, for scripts.
- It never touches git, curl or the other system packages, Docker, your users, or how you log
  in to the server.

It cannot reach these, so they are yours to remove if you are done with FamilyDB:

- the deploy key on GitHub, under the repository's Settings → Deploy keys (it names the page);
- the Telegram bot: `/deletebot` in @BotFather;
- the Google Cloud project and its OAuth client;
- the API keys at each company, which work until you revoke them.

A new install can reuse the bot, the Google client and the keys as they are.
</details>

## Troubleshooting

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
be made to work from the server, fall back to [copying it yourself](#copy-it-from-your-own-computer)
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

*How to fix:* add swap (see [Looking after the server itself](#looking-after-the-server-itself)) and paste the install block again. Nothing is lost: everything that
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

### The page does not open

*Symptom:* the browser waits and then says the site cannot be reached, or took too long.

*What it means:* nothing is getting through to the server on ports 80 and 443. Nearly always the
server provider's own firewall, which the server cannot see or change.

*How to check:* on the server, `curl -skI https://127.0.0.1 -H 'Host: 203.0.113.7'` (with your
address). An answer there means the server is fine and something in between is not.

*How to fix:* in the provider's control panel, find the firewall (it may be called a security
group or networking) and allow incoming TCP on ports 80 and 443. Then:

```bash
sudo /opt/familydb/scripts/maintain.sh https
```

which also gets a real certificate if the first try could not. A **502** from the browser is the
other way round: Caddy is reached, and FamilyDB behind it is not serving. `sudo journalctl -u
familydb -n 40 | grep 'not serving'` names why.

### Google will not connect from the page

Connecting Google Calendar from the page has not yet been tried against a live Google account. If
it will not connect, do the sign-in on a computer with a browser instead, from a copy of the code:

```bash
uv run familydb google auth --client-secrets ~/Downloads/client_secret_XXX.json
uv run familydb google calendars          # find the family calendar's id
```

Copy the token to the server and give it to the service account:

```bash
scp data/google_token.json you@203.0.113.7:/tmp/
sudo install -o familydb -g familydb -m 600 /tmp/google_token.json /opt/familydb/data/
rm /tmp/google_token.json
```

Put the calendar id in the **Google calendar id** box on the settings page (Connections), and
restart:
`sudo systemctl restart familydb`. Check with
`cd /opt/familydb && sudo -u familydb .venv/bin/familydb google events`.

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

## Looking after the server itself

None of this is FamilyDB's, and none of it is needed to install it. It is the ordinary care any
server on the internet deserves, for when you have a minute.

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
sudo ufw allow 80,443/tcp     # the page
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

**Swap, if memory is tight.** On a 1 GB box the install step that builds the virtualenv is the
one that gets killed. Swap makes it slow rather than fatal:

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -m
```
