# Installing FamilyDB

Three steps, about twenty minutes. No Linux knowledge is needed: the installer does the server side and says what it is doing, and the web page walks you through the rest.

**You need**

- A server with Ubuntu 24.04 or 26.04, or Debian 12, and at least 1 GB of memory (the smallest plan at most VPS providers). You must be able to log in to it; as root is fine.
- To be signed in to GitHub as the owner of the FamilyDB repository.
- A card for the AI company, which charges a few dollars a month for a family. Step 3 says where.

<details>
<summary>Do I need to create a user, set up SSH keys, open ports or edit any files?</summary>

No. The installer creates FamilyDB's own account (`familydb`, which runs the bot and owns its data; nobody logs in as it), makes the one key it needs to read the code, puts HTTPS in front of the page, opens ports 80 and 443 if the server's firewall is on, and schedules a nightly backup. [What the installer changes](#what-the-installer-changes-and-why) lists each with its reason. Keeping the server itself up to date is ordinary server care: [Looking after the server itself](#looking-after-the-server-itself).
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
First it deals with the one thing it cannot do by itself, letting the server read the code: it shows a link and a line of text. On GitHub, paste the line and press **Add key**, then press Enter on the server. After that it installs everything, asking only whether to go ahead (once it has listed what it will change) and whether you have a domain name for the page (Enter if not).

<details>
<summary>What if something goes wrong?</summary>

It stops and says what went wrong and what to do. Once that is sorted, paste the same block again: it keeps what already worked and carries on. Everything it did is in `/var/log/familydb-bootstrap.log`, the file to send if you need someone to look.

If the terminal says `sudo: command not found`, you are root: paste the block again without its first word, `sudo`.
</details>

<details>
<summary>Why a key, and what can it do?</summary>

The code is in a private repository, so GitHub needs proof that this server may read it. The key can read that one repository and nothing else: it cannot change anything or see your other repositories or account. It stays in `/root/familydb_deploy` so upgrades can fetch new versions. To take the server's access away, delete it on GitHub under the repository's **Settings → Deploy keys**.
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

FamilyDB could not get a certificate from a public authority, so it made its own. The connection is still encrypted. Choose **Advanced**, then **continue** (or **Accept the risk**); each browser asks once. To get rid of the warning, give it a domain: [A domain name instead of the address](#a-domain-name-instead-of-the-address). If the installer said nothing outside could reach the server, fix that first (next question).
</details>

<details>
<summary>The page does not open at all</summary>

Almost always your provider's own firewall (control panel; called a firewall, security group or networking). Allow incoming TCP on ports **80** and **443**, then on the server:

```bash
sudo /opt/familydb/scripts/maintain.sh https
```

That also gets the page a real certificate if the first try could not. More in [Troubleshooting](#the-page-does-not-open).
</details>

## 3. Follow the setup on the page (10 to 15 minutes)

The page opens on its setup, seven short steps, each saying why it matters and what to do. The first two put you on the family list and give you a password of your own, replacing the one above: from then on everybody signs in as themselves, with a starting password from you on the Family page.

| Step | | What you will need |
|---|---|---|
| Yourself | needed | your name |
| Your own password | recommended | |
| An AI model | needed | an account with OpenAI (the cheapest), Anthropic or Google |
| Where home is | recommended | your town |
| Telegram | optional | Telegram on your phone |
| The rest of the family | optional | |
| Google Calendar | optional, 10 minutes | any Google account, to make a service account and share the family calendar with it |

Skip any step and come back later; the home page lists what is left. That is the whole install.

---

# Reference

Everything below is for doing something differently, or for when something goes wrong.

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

Before it changes anything, it lists these and asks. In order:

| What | Why |
|---|---|
| Installs `git`, `curl`, `ca-certificates` and `tzdata` if missing | to fetch the code, check HTTPS certificates, and know what "this weekend" means where you live |
| Installs `uv` into `/usr/local/bin` | it fetches the Python this program needs and builds its virtualenv; the system Python is not changed |
| Creates a system account, `familydb`, no password, no login | the bot runs as this, not root or you, so a mistake in it cannot reach the rest of the machine |
| Puts the code in `/opt/familydb` | one directory holds program, configuration and database, which keeps backing up and removing simple |
| Writes `/opt/familydb/.env`, readable only by `familydb` | the first password and the page's address; everything else is set on the page |
| Creates the database, `/opt/familydb/data/familydb.sqlite3` | everything the family tells it lives in that one file |
| Writes and enables `/etc/systemd/system/familydb.service` | so it starts at boot and restarts if it stops |
| Adds a nightly backup to root's crontab, kept two weeks, in `/opt/familydb/backups` | so a bad day can be undone |
| Installs Caddy and writes `/etc/caddy/Caddyfile`; for a public address with no domain, Caddy 2.10 or newer, from Caddy's apt repository when the system's is older | Caddy puts HTTPS in front of the page and renews its certificate, so the password never crosses the network in the clear. An older Caddy cannot get a certificate for an address alone |
| Opens ports 80 and 443 in `ufw`, if on | so browsers can reach the page; the bot needs nothing else inbound |
| Records each change in `/var/lib/familydb-install` as it makes it | so `uninstall.sh --from-zero` can put the server back as it was |

It does not touch your SSH configuration, the system Python, any other service, or anything in a home directory. Running it again is safe: it installs only what is missing, keeps `.env` and the database, and picks up where a failed run stopped.

<details>
<summary>Why /opt, and not a home directory?</summary>

The bot runs as its own account, which on Debian and Ubuntu cannot enter anyone's home directory, so a service pointed at `/home/sam` would stop the moment it started. The installer refuses to install a service it knows cannot run.
</details>

<details>
<summary>The installer's options</summary>

`bootstrap.sh --help` lists them all:

- `--dry-run` says what would happen and changes nothing.
- `--local-only` keeps the page off the internet ([below](#keeping-the-page-off-the-internet)).
- `--mode docker` runs it in Docker instead of a virtualenv.
- `--target DIR` and `--user NAME` move the install and rename its account. The name is used for the account, the files it owns and the service unit, and is kept in `/var/lib/familydb-install/service-user`, so `maintain.sh` and `uninstall.sh` find it later (pass `--user` to them if that file is gone).
- `--ref NAME` installs a particular tag, branch or commit.
- `--yes` takes every default, for a scripted build.

Without `--ref`, the version depends on `CHANGELOG.md`: while the newest version is marked "in progress" it installs the default branch; once that has a date, the newest release tag.
</details>

## A domain name instead of the address

A domain removes the certificate warning for good.

1. Where you bought the name, add an **A record** (such as `family.example.com`) pointing at the server's address. `dig +short family.example.com` on the server prints that address once it has taken effect (minutes, sometimes an hour).
2. On the server:

   ```bash
   sudo /opt/familydb/scripts/maintain.sh https family.example.com
   ```

That points Caddy at the name, gets its certificate, and restarts FamilyDB to match. Typing the name when the installer asks does the same at install time.

<details>
<summary>What it sets</summary>

In `/opt/familydb/.env`: `WEB_DOMAIN` (the name, or the address when there is none), `WEB_PUBLIC_PORT` (443 unless moved, below), `WEB_TRUST_PROXY=true` and `WEB_HOST=127.0.0.1`. The page then listens only to Caddy on the same machine and believes it about who is visiting and that the connection was HTTPS, which keeps the lockout per visitor and marks the sign-in cookie `Secure`. Caddy's configuration is `/etc/caddy/Caddyfile`; `sudo journalctl -u caddy -n 50` says how getting the certificate went. Port 8080 is never opened to the outside.

On the Docker path, set `WEB_DOMAIN`, `WEB_TRUST_PROXY=true` and `COMPOSE_PROFILES=tls` in `.env` and run `docker compose up -d`, which starts a Caddy container too. With nginx already on the machine, `deploy/nginx-familydb.conf` does Caddy's job with a certbot certificate (steps at the top of the file).
</details>

<details>
<summary>A port that scans rarely try</summary>

A scan of the server finds Caddy on 443, the port every internet sweep looks at, never 8080. To serve on another port:

```bash
sudo /opt/familydb/scripts/maintain.sh https --port random
```

It prints the new address, `https://your.domain:PORT/` (bookmark it), and opens that port in `ufw`; allow it in your provider's firewall too. Port 80 stays open for the certificate authority's check but points nobody at the page. `--port 443` moves it back. This keeps the page out of scans of the usual ports; a scan of every port would still find it, so it is no substitute for good passwords. RUNBOOK section 10 has the mechanics.
</details>

<details>
<summary>The warning worth reading twice</summary>

The family's passwords are all that stand between a stranger and your API bill: a parent's is most of the bot, an admin's is all of it, keys and spending limit included. Keep admins few and passwords long, set a spending limit on the API key with the company too, and look at `/status` now and then for a month that does not look like yours. If a phone goes missing, make its owner a new starting password on the Family page, which signs them out everywhere. RUNBOOK section 10 says what each role can reach and what else protects the page.
</details>

## Keeping the page off the internet

Add `--local-only` to the installer (at the end of the `bootstrap.sh` line in the block). You then reach the page over an SSH tunnel. On your own computer, not the server:

```bash
ssh -L 8080:127.0.0.1:8080 you@203.0.113.7
```

While that stays connected, `http://127.0.0.1:8080/` in a browser on the same computer is the server's page (the same command works in Windows PowerShell). To move to a link anyone can open later: `sudo /opt/familydb/scripts/maintain.sh https`.

## Other ways to get the code onto the server

The step 1 block makes a deploy key and uses it. These are the by-hand alternatives, or ways to put no credential on the server at all.

| Way | What is on the server | Best for |
|---|---|---|
| Deploy key | one read-only SSH key, valid for this repository alone | a server you keep; the default |
| Token | a token that can read every repository it was scoped to | getting going quickly |
| Copy it yourself | nothing | a server you do not want to trust with anything |

### A deploy key, by hand

Make a key for this one purpose. It lives in `/root` because upgrades run as root and read it for as long as the install exists:

```bash
sudo ssh-keygen -t ed25519 -C "familydb deploy" -f /root/familydb_deploy -N ""
sudo cat /root/familydb_deploy.pub
```

`-N ""` (no passphrase) matters: upgrades fetch unattended, so a passphrase works for the install and then breaks every upgrade. Bootstrap notices one and offers to remove it; yourself: `sudo ssh-keygen -p -f /root/familydb_deploy -N ""`.

Copy the public line to [github.com/atate911/FamilyDB/settings/keys/new](https://github.com/atate911/FamilyDB/settings/keys/new) (the repository's **Settings → Deploy keys → Add deploy key**; only owner and admins can open it). Your account's own "SSH and GPG keys" is a different place and a key there would reach every repository you can. Give it a title, paste the key, leave **Allow write access** unticked. Check from the server:

```bash
sudo ssh -T git@github.com -i /root/familydb_deploy
# "Hi atate911/FamilyDB! You've successfully authenticated, but GitHub does not provide shell
#  access." is the answer you want.
```

Then fetch a copy for the scripts and run bootstrap from it (bootstrap still clones its own copy into `/opt/familydb` with the key, so upgrades can fetch). Paste these one block at a time: bootstrap asks questions, and anything pasted after it is read as the answer to the first.

```bash
sudo git -c core.sshCommand="ssh -i /root/familydb_deploy -o IdentitiesOnly=yes" \
  clone --depth 1 git@github.com:atate911/FamilyDB.git /root/familydb-scripts
```

```bash
sudo bash /root/familydb-scripts/scripts/bootstrap.sh --deploy-key /root/familydb_deploy
```

Once it has finished, and not before: `sudo rm -rf /root/familydb-scripts`. (Or from a clone of your own: `scp -r scripts sam@your-server:~/`, then `sudo bash ~/scripts/bootstrap.sh --deploy-key /root/familydb_deploy` on the server.)

Bootstrap rewrites the repository URL to its SSH form, clones with that key, and writes the key's path (never the key) into the checkout's `core.sshCommand`, so upgrades fetch with it.

### A fine-grained personal access token

GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**: the shortest expiry you can live with, **Repository access** set to **Only select repositories** (FamilyDB), **Permissions → Repository permissions → Contents: Read-only**, nothing else.

On the server, read the token in without it landing in shell history, fetch the scripts, run bootstrap. `sudo` drops the environment unless told to keep that variable:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN        # paste the token, then Enter
git clone --depth 1 "https://x-access-token:${GITHUB_TOKEN}@github.com/atate911/FamilyDB.git" ~/familydb-scripts
sudo --preserve-env=GITHUB_TOKEN bash ~/familydb-scripts/scripts/bootstrap.sh
```

Answer its questions, then `rm -rf ~/familydb-scripts`. The token is used for the clone only: never written to `.env` or the log, and the saved remote is reset to the plain HTTPS URL so it is not in `.git/config`. So an upgrade needs it again ([Day to day](#day-to-day)); a deploy key later avoids that.

### Copy it from your own computer

No credential reaches the server. On a computer that can read the repository, archive the committed code (leaving out the virtualenv, database and any `.env`, none being committed) and copy it across:

```bash
git clone git@github.com:atate911/FamilyDB.git ~/FamilyDB     # if you have no clone yet
git -C ~/FamilyDB archive --format=tar.gz --prefix=FamilyDB/ -o ~/familydb.tar.gz HEAD
scp ~/familydb.tar.gz sam@your-server:~/
```

On the server, unpack the scripts and point bootstrap at the archive:

```bash
tar -xzf ~/familydb.tar.gz
sudo bash ~/FamilyDB/scripts/bootstrap.sh --from ~/familydb.tar.gz
```

Copy the archive, not a working directory: your own `.env` would carry your keys to the server and be taken for this machine's configuration. Bootstrap run from inside a checkout with no deploy key and no token installs that checkout, so `sudo bash ~/FamilyDB/scripts/bootstrap.sh` alone does the same.

## Check it works end to end

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

That runs `familydb doctor` (settings, `.env` permissions, disk, database and schema, family, keys, models, Telegram, calendar, weather, lookups, digest, web page, service) and prints a fix under anything wrong. `--online` also asks Telegram whether its token works and asks Claude or Gemini whether key and tools work by counting tokens, which is free. OpenAI, the default, cannot count tokens without answering, so the first real message checks it (the page checks a key with its company, free, when the company is chosen there):

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

Then a real message, on the page's Chat, over Telegram, or from the server:

```bash
cd /opt/familydb
sudo -u familydb .venv/bin/familydb chat "we should try that new ramen place on Main St sometime"
sudo -u familydb .venv/bin/familydb chat "tell me about #1"
sudo -u familydb .venv/bin/familydb db status
```

`db status` should show `cache_read` above zero on the second call; if not, RUNBOOK section 13. `/status` in the browser says who answers, what is connected, what it has cost and what is waiting, asking nothing of a model.

## Day to day

```bash
sudo /opt/familydb/scripts/maintain.sh status             # running? healthy? last backup?
sudo /opt/familydb/scripts/maintain.sh check              # the full check, with fixes
sudo /opt/familydb/scripts/maintain.sh logs 200           # follow the log
sudo /opt/familydb/scripts/maintain.sh restart
sudo /opt/familydb/scripts/maintain.sh backup
sudo /opt/familydb/scripts/maintain.sh restore FILE       # stops it, puts it back, starts it
sudo /opt/familydb/scripts/maintain.sh upgrade            # newer code, backup taken first
```

`restore` and `upgrade` each take a backup first, so either can be undone. Use `upgrade`, not `git pull` (which fails on the detached commit an upgrade leaves). RUNBOOK section 8 says what it does and which version it moves to.

**Upgrades on a private repository.** `upgrade` fetches from `origin`, which needs a credential.

- Installed with `--deploy-key`: already wired (SSH remote, key path in the checkout's `core.sshCommand`); it works while the key file stays at `/root/familydb_deploy`.
- Installed with a token: bootstrap deliberately did not keep it, so give it for each upgrade (used for that fetch only):

  ```bash
  read -rs GITHUB_TOKEN && export GITHUB_TOKEN
  sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade
  ```

  Tokens expire. To stop needing one, make a deploy key ([A deploy key, by hand](#a-deploy-key-by-hand)) and point the checkout at it once:

  ```bash
  sudo git -C /opt/familydb remote set-url origin git@github.com:atate911/FamilyDB.git
  sudo git -C /opt/familydb config core.sshCommand \
    "ssh -i /root/familydb_deploy -o IdentitiesOnly=yes"
  sudo git -C /opt/familydb fetch --tags origin      # should now work
  ```

- Brought a copy yourself: nothing to fetch from. Back up, make a new archive ([Copy it from your own computer](#copy-it-from-your-own-computer)), copy it across, unpack over the install (`.env` and `data/` are not in the archive), rerun the installer (reinstalls dependencies, migrates) and restart:

  ```bash
  sudo /opt/familydb/scripts/maintain.sh backup
  sudo tar -xzf ~/familydb.tar.gz -C /opt/familydb --strip-components=1 --no-same-owner
  sudo bash /opt/familydb/scripts/install.sh
  sudo /opt/familydb/scripts/maintain.sh restart
  ```

`upgrade` says all of this itself when a fetch fails.

**Backups.** A nightly one, kept two weeks, is scheduled (`sudo crontab -u root -l`; `maintain.sh schedule-backups` puts it back). RUNBOOK section 7: copying off the machine, restoring by hand, what is inside.

**Passwords** are chosen on the page, each person their own, stored only as hashes. Somebody who forgot theirs gets a new starting password from an admin on the Family page. If the only admin forgot theirs, `sudo /opt/familydb/scripts/maintain.sh password` prints one (`password NAME` for somebody else). `WEB_PASSWORD` in `.env` is only the installer's first-time password and opens nothing once an admin has their own.

RUNBOOK section 12: journald limits, disk, and what to do when a secret gets out.

## Removing it

| Command | Removes | Keeps |
|---|---|---|
| `sudo /opt/familydb/scripts/uninstall.sh` | the service and the installed program | `.env`, the database, the backups: reinstalling picks up where it left off |
| `... uninstall.sh --purge` | all of FamilyDB, including the database and its `familydb` account | a backup of the database, in `/var/backups/familydb` |
| `... uninstall.sh --from-zero` | all of that, and everything the install did around it | nothing, unless `--backup-to DIR` is given |

`--from-zero` puts the server back as it was before FamilyDB, for trying the install again from the beginning. It undoes exactly what the installer recorded in `/var/lib/familydb-install` (each package it added, not ones already there; each file, folder and link; the accounts, cron line and firewall rule; a copy of any file it replaced, which it puts back). An install with no record, or part of one, gets a wider search: Caddy when it serves nothing but FamilyDB, uv and the line its installer added to root's shell profiles, the deploy key, code copies and backups in home directories, GitHub in root's `known_hosts`, the logs.

Like `--purge`, it asks twice: a yes-or-no after listing by name everything it will remove (Enter means no), then typing `remove everything` in full. `--dry-run` shows the list and removes nothing.

<details>
<summary>The details</summary>

- It removes Caddy only when Caddy serves nothing but FamilyDB; otherwise it says which site to take out of `/etc/caddy/Caddyfile`.
- It refuses a directory without FamilyDB's `pyproject.toml` and refuses system directories outright. It runs from a copy of itself so it can remove `/opt/familydb` with the script inside it.
- `--backup-to DIR` puts the backup elsewhere; `--no-backup` skips it (only deliberately); `--keep-user` leaves the `familydb` account; `--force` skips both questions, for scripts.
- It never touches git, curl, other system packages, Docker, your users, or how you log in.

Yours to remove if you are done with FamilyDB: the deploy key on GitHub (Settings → Deploy keys; it names the page); the Telegram bot (`/deletebot` in @BotFather); the Google Cloud project and service account; the API keys at each company, which work until revoked. A new install can reuse the bot, service account and keys as they are.
</details>

## Troubleshooting

App-level problems (model API, `cache_read`, sign-in loops, Google, Telegram, settings) are in RUNBOOK section 13. Below: install and server failures, each with symptom, meaning, check and fix.

### Where the logs are

```bash
less /var/log/familydb-bootstrap.log         # the whole bootstrap run, step by step
less /var/log/familydb-install.log           # the configuration step it hands over to
sudo journalctl -u familydb -n 100 --no-pager
sudo journalctl -u familydb -f               # follow it
cd /opt/familydb && sudo docker compose logs -f bot    # the Docker path
```

`maintain.sh` and `uninstall.sh` keep transcripts at `/var/log/familydb-maintain.log` and `/var/log/familydb-uninstall.log`. Every failure message from these scripts names the file to send. Nothing in FamilyDB writes a log file of its own: systemd sends it to journald; Docker caps each container at five files of 10 MB.

### The clone fails: authentication

*Symptom:* `could not clone https://github.com/atate911/FamilyDB.git`, `Permission denied (publickey)`, or `could not read Username for 'https://github.com'`.

*Meaning:* the repository is private and GitHub did not accept what it was given; nothing was fetched. Bootstrap removes the half-made directory.

*Check:*

```bash
sudo ssh -T git@github.com -i /root/familydb_deploy   # names the repository if the key works
git ls-remote https://x-access-token:$GITHUB_TOKEN@github.com/atate911/FamilyDB.git | head -1
```

*Fix:* a deploy key must be the **private** half (`/root/familydb_deploy`, not `.pub`) with its public half on **this** repository's deploy keys, not your account. A token must be unexpired with Contents: Read on this repository. If neither works from the server, [copy it yourself](#copy-it-from-your-own-computer); no credential is needed.

### "The familydb user cannot get into ..."

*Symptom:* the installer says the `familydb` user cannot get into the checkout and skips the systemd unit; or `systemctl status familydb` shows a permission error on the working directory.

*Meaning:* the checkout is in a home directory (mode 0750 or 0700), which the service account cannot enter; no unit hardening changes that.

*Check:*

```bash
sudo -u familydb test -x /home/sam && echo reachable || echo "cannot enter /home/sam"
stat -c '%U:%G %a' /home/sam
```

*Fix:* move it to `/opt/familydb`, where the unit expects it:

```bash
sudo mkdir -p /opt/familydb
sudo cp -a /home/sam/FamilyDB/. /opt/familydb/
cd /opt/familydb && sudo scripts/install.sh
```

To keep it under `/home`: `chmod o+x /home/sam`, and the unit needs `ProtectHome=read-only` instead of `true` (the installer substitutes it; the traversal is yours). RUNBOOK section 2b.

### The service starts and then stops

*Symptom:* bootstrap says "The service started and then stopped", or `systemctl is-active familydb` says `failed`.

*Meaning:* almost always a setting it will not accept, or a file it cannot write.

*Check, in order:*

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb doctor
sudo systemctl status familydb
sudo journalctl -u familydb -n 50 --no-pager
```

*Fix:* doctor names the thing and prints the fix. The three that bite: `familydb` not owning `data/` and `.env`, a checkout in a home directory (above), a value in `.env` the settings will not take (RUNBOOK section 13, "a setting will not do"). Then `sudo systemctl restart familydb`.

### "familydb could not start: Permission denied: '.env'"

*Symptom:* any `familydb` command run as yourself fails like that.

*Meaning:* the installer gave `.env` and `data/` to the `familydb` user, on purpose, so the database stays owned by the account that writes it.

*Fix:* run as that user, from the install directory (`.env` is read from the current directory):

```bash
cd /opt/familydb && sudo -u familydb .venv/bin/familydb doctor
```

### "cannot write" on the database, or database permission denied

*Symptom:* doctor reports `database writable: cannot write`, or the log shows `attempt to write a readonly database`.

*Meaning:* `data/` or the database file belongs to somebody other than the bot's user: common after a by-hand restore, or `familydb db migrate` run as root.

*Check:* `ls -l /opt/familydb/data`

*Fix:*

```bash
sudo chown -R familydb:familydb /opt/familydb/data /opt/familydb/.env
sudo systemctl restart familydb
```

Docker runs as uid 1000 instead: `sudo chown -R 1000:1000 /opt/familydb/data`.

### No space left on device

*Symptom:* a step fails with that message, doctor warns about free space, or the bot cannot write.

*Meaning:* the disk is full; SQLite cannot write, nor anything else.

*Check:*

```bash
df -h /
sudo du -xh --max-depth=1 /var | sort -h | tail
```

*Fix, biggest wins first:*

```bash
sudo journalctl --vacuum-size=200M
sudo apt-get clean
sudo docker system prune -af           # if Docker is installed
find /opt/familydb/backups -name 'familydb-*.sqlite3' -mtime +14 -delete
```

Then cap the journal for good (`SystemMaxUse=500M` in `/etc/systemd/journald.conf`) and schedule the prune with `maintain.sh schedule-backups --keep-days 14`.

### "Could not get lock" from apt

*Symptom:* bootstrap stops with `Could not get lock /var/lib/dpkg/lock-frontend`.

*Meaning:* another program is installing packages (on a freshly booted server, usually unattended-upgrades' first run).

*Check:* `sudo fuser -v /var/lib/dpkg/lock-frontend`

*Fix:* wait a minute and rerun bootstrap. If a previous install was interrupted rather than busy, `sudo dpkg --configure -a` first. Never delete the lock file by hand.

### Killed, or out of memory

*Symptom:* a step ends with `Killed` and nothing else, usually while the virtualenv is built.

*Meaning:* the kernel ran out of memory. On a 512 MB or 1 GB box this is the most likely failure.

*Check:*

```bash
free -m
sudo dmesg -T | grep -i 'killed process' | tail
```

*Fix:* add swap ([Looking after the server itself](#looking-after-the-server-itself)) and paste the install block again; everything that worked is still in place.

### The page does not open

*Symptom:* the browser waits, then says the site cannot be reached or took too long.

*Meaning:* nothing gets through to ports 80 and 443; nearly always the provider's own firewall, which the server cannot see or change.

*Check:* on the server, `curl -skI https://127.0.0.1 -H 'Host: 203.0.113.7'` (your address). An answer means the server is fine and something in between is not.

*Fix:* in the provider's control panel allow incoming TCP on 80 and 443, then `sudo /opt/familydb/scripts/maintain.sh https` (which also gets a real certificate if the first try could not). A **502** is the other way round: Caddy is reached, FamilyDB behind it is not serving; `sudo journalctl -u familydb -n 40 | grep 'not serving'` names why.

### Port already in use

*Symptom:* `the web page is not serving: address already in use` in the log; the bot keeps running without a page.

*Meaning:* something else has the port, often an older `familydb web` left in the foreground or a second copy of the bot.

*Check:* `sudo ss -ltnp | grep ':8080'`

*Fix:* stop what holds it, or move FamilyDB, which also repoints Caddy or Docker and restarts it (the port must stay above 1024, the service being unprivileged):

```bash
sudo /opt/familydb/scripts/maintain.sh port 9090    # or port random
```

`database is locked` is the same mistake one layer down: two processes writing; only one `familydb run` may exist (the CLI alongside is fine).

### Everything looks right and it still does not answer

Work down doctor's list rather than guessing (`✗` first, then `!`):

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

Usual answers: nobody in `members` for the channel they write from ("Sorry, I only talk to the family"; the reply carries the id to add), no key for the chosen provider so another stands in, or the bot is not running. RUNBOOK section 13 lists the rest, with the log line each prints.

## Looking after the server itself

None of this is FamilyDB's or needed to install it; it is the ordinary care any server on the internet deserves.

**A user that is not root.** From root, once:

```bash
adduser sam
usermod -aG sudo sam
```

**SSH keys, from your own computer.** Check you can still get in from a second terminal before turning passwords off:

```bash
ssh-copy-id sam@your-server
ssh sam@your-server 'echo in'
```

If the provider set up key-only logins, `ssh-copy-id` cannot get in as `sam`; copy root's key across as root on the server:

```bash
install -d -m 700 -o sam -g sam /home/sam/.ssh
install -m 600 -o sam -g sam /root/.ssh/authorized_keys /home/sam/.ssh/
```

Then in `/etc/ssh/sshd_config` set `PasswordAuthentication no` and `PermitRootLogin no`, and `sudo systemctl reload ssh`. Ubuntu cloud images often carry a file in `/etc/ssh/sshd_config.d/` (such as `50-cloud-init.conf`) saying `PasswordAuthentication yes` that wins over the main file; set it to `no` there too. `sudo sshd -T | grep -i passwordauth` shows what is in force.

**A firewall.** The order matters more than the rules:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH        # BEFORE enabling. Skip this line and you lock yourself out.
sudo ufw allow 80,443/tcp     # the page (80 and its own port instead, if it was moved)
sudo ufw enable
sudo ufw status
```

`ufw enable` takes effect at once, including on the connection you are typing over. Without `allow OpenSSH` first, your session dies and you cannot open another; the only way back is the provider's console.

**Unattended security updates.** The maintenance that matters most:

```bash
sudo apt update && sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades    # answer yes
```

**Swap, if memory is tight.** On a 1 GB box the virtualenv build is what gets killed; swap makes it slow rather than fatal:

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -m
```
