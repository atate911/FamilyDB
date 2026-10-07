# Install and first run

Installing FamilyDB is three steps: paste one block into the server's terminal, open the web page it prints, and follow the setup on the web page. The block lives in `docs/INSTALL.md`, step 1, in the repository, and is deliberately not copied here, so the commands cannot drift apart.

This guide is served by a running FamilyDB, so you read it after a first install, for a second server, or when restoring.

## Before you start

- You are signed in to GitHub as the owner of the FamilyDB repository. The code is in a private repository.
- You can reach the server's terminal over SSH. Root is fine.
- You have a key for a model company: Anthropic, OpenAI or Google. The setup says where to get one.
- If you have a domain, its DNS record points at the server. You can add this later.

## What you need

| Need | Minimum | Who checks | What happens |
|---|---|---|---|
| Operating system | Ubuntu 24.04 or 26.04, or Debian 12 | `bootstrap.sh` | On any other system it warns and installs nothing with apt, so you install git, curl and Docker or Python 3.11 yourself |
| Memory | 1 GB (FamilyDB itself needs about 200 MB; building the install needs more) | `bootstrap.sh` | Warns under 900 MB. A step that ends with only `Killed` ran out of memory; add [swap](/wiki/operations/host#disk-and-memory) |
| Free disk | 900 MB where `/opt` lives | `bootstrap.sh` | Stops under 900 MB |
| Free disk, `install.sh` run alone | 600 MB | `install.sh` | Warns under 600 MB and asks whether to carry on |
| Free disk for the database | 500 MB | `familydb doctor` | Warns below 500 MB |

## The three steps

### 1. Paste the block

The block does the one thing the installer cannot do alone. It makes a [deploy key](/wiki/reference/glossary#deploy-key), an SSH key that can read this one repository and nothing else, and shows you a link and a line of text. On GitHub, paste the line under the repository's **Settings → Deploy keys** and press **Add key**, then press Enter on the server.

Then the installer lists what it will change on the server and asks whether to go ahead, and whether the web page has a domain name (press Enter if not).

The key stays at `/root/familydb_deploy` so that [upgrades](/wiki/operations/upgrade-and-rollback) can fetch new versions. To use an installer option, add it to the end of the `bootstrap.sh` line in the block before you paste it.

### 2. Open the page

The installer ends with an address and a password. Open the address in any browser and sign in with that password. It is the [shared password](/wiki/reference/glossary#shared-password): the setup's second step has you choose your own, and until then everybody shares this one. If you lose it, see [Recovery](/wiki/operations/recovery).

If the browser says the connection is not private, see [HTTPS and the firewall](/wiki/operations/https-and-firewall#the-browser-says-the-connection-is-not-private). If the web page does not open at all, see [Troubleshooting](/wiki/operations/troubleshooting#the-page-will-not-open).

### 3. Follow the setup

The web page opens on [Setup](/wiki/controls/setup): seven short steps, each saying why it matters. You can skip any step and come back, and Home lists what is left.

## Choices you can make

- HTTPS: The installer puts HTTPS in front of the web page unless you pass `--local-only`, or you install on Docker without a domain. [HTTPS and the firewall](/wiki/operations/https-and-firewall) covers the certificate, ports and the firewall.
- A domain name: Add an A record at your registrar pointing at the server, then type the name when the installer asks, or later run `sudo /opt/familydb/scripts/maintain.sh https family.example.com`.
- Keep the web page off the internet: Add `--local-only` to the `bootstrap.sh` line. You then reach the web page through an SSH tunnel, opened from your own computer and not the server: `ssh -L 8080:127.0.0.1:8080 you@server`, then `http://127.0.0.1:8080/` in a browser on that computer. `maintain.sh https` moves you to a public link later.
- Docker instead of a virtualenv: Add `--mode docker`. Docker is installed for you, and FamilyDB and Caddy run as containers instead of a [systemd](/wiki/reference/glossary#systemd) service. Without a domain the web page is reachable from the server only. [The server](/wiki/operations/host#docker-instead) lists what runs.
- Other options: `--dry-run` changes nothing and says what would happen. `--ref` installs a particular tag, branch or commit. `--yes` takes every default. `bootstrap.sh --help` lists them all.

Without `--ref`, the version depends on `CHANGELOG.md`; see [Which version it moves to](/wiki/operations/upgrade-and-rollback#which-version-it-moves-to).

## What the installer changes, and why

It lists every change and asks before it makes any, apart from the key and `git` in step 1. In short, it:

- installs the packages it needs (git, curl, ca-certificates, tzdata, and uv, Caddy, cron or Docker when you need them);
- creates a `familydb` account with no password and no login, so FamilyDB runs without root;
- puts the program, `.env` and the database in `/opt/familydb`;
- writes and enables the systemd service, so FamilyDB starts at boot;
- adds a nightly backup at 03:15 to root's crontab;
- sets up HTTPS with Caddy and opens ports 80 and 443 if `ufw` is on, unless you chose otherwise.

It leaves your SSH configuration, the system Python and every other service alone, and running it again is safe: it installs only what is missing and keeps `.env` and the database. [The server](/wiki/operations/host#everything-the-install-put-on-the-server) lists every path with its owner and the reason.

## Check that it worked

1. Run the check:

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

Each line starts with `✓` (fine), `!` (worth reading), `✗` (must be fixed) or `·` (skipped), and a fix follows anything that is not fine. Before the setup is finished the last line reads `It will run. 2 thing(s) are not set up yet, which is normal on a first install.` Afterward it reads `Everything is set up.` A `✗` ends with `thing(s) must be fixed before this will work`. On Docker the report also carries two warnings that mean nothing; see [How to run it](/wiki/operations/command-line#how-to-run-it).

2. Look at the service:

```bash
sudo /opt/familydb/scripts/maintain.sh status
```

A virtualenv install shows `Service: active, enabled at boot` and `Scheduled: a nightly backup is in root's crontab`; Docker shows `Runs as: Docker containers`. `Last backup` reads `No backups` until the first run at 03:15; `maintain.sh backup` takes one now.

3. After setup steps 1 and 3 (you, and a model), open Chat on the web page and send `hello`. The assistant answers. If nothing comes back, see [A message got no reply](/wiki/operations/troubleshooting#a-message-got-no-reply).

4. Check the clock. Open **Settings**, then **General**, and look at **Time zone** (`family_tz`). The installer copies the server's time zone, and a new rented server is set to UTC, so until you choose your own, reminders and weekend ideas arrive at the wrong hour.

## If it goes wrong

The installer stops and says what went wrong and what to do. Fix that, then paste the same block again: it carries on where it stopped. Everything it did is in `/var/log/familydb-bootstrap.log`; send that file if you need someone to look. `docs/INSTALL.md` has a symptom-by-symptom section for the server side, and [Troubleshooting](/wiki/operations/troubleshooting) covers FamilyDB itself.
