# Break glass: when the usual fixes are not enough

For the day the program will not start, an upgrade broke something badly, the database is damaged, the disk is full, or nobody can get in. Two commands on the server, and both work when FamilyDB does not:

```bash
sudo /opt/familydb/scripts/maintain.sh doctor
sudo /opt/familydb/scripts/maintain.sh rescue
```

**`doctor` is where to start.** It answers "it is broken and I do not know why": it works out what is wrong, tells you, and fixes what it can. `rescue` has the larger remedies one at a time, for when the doctor is not enough or you already know which you want. [Diagnostics](/wiki/operations/diagnostics) is the look alone: `maintain.sh check` only reads, and when it finds something that must be fixed it ends by naming the ways that suit what it found.

## The doctor

It works in five steps, and asks you only where only you can answer.

1. **It looks at everything**, the same sweep as `check`: the files and who owns them, git, `.env`, Python, the database file, the service, the web server and HTTPS, the host, and then the program's own check. When the service is unwell it also reads its log, because a traceback often names a cause no check could.
2. **It says what is wrong and why**, from the bottom up, in plain words: "the service runs as familydb and no such account exists, so it cannot start". The first line says what you would notice (the page is down; it answers but crashes when drawn).
3. **It shows what it will do** about each thing, which steps download something, and which will ask you again; and, apart, **what only you can do** with the command or the place to do it (an A record at your registrar, a deploy key on GitHub, a line in `.env` it cannot guess). It carries on with the rest meanwhile.
4. **It does the safe steps on one Enter**, in the order a page comes up, each with a line saying it worked, and then starts FamilyDB and waits for the page. A step that fails is said, and the others go on. Anything that can lose data (putting a database back, deleting backups) is one step that asks for a typed `yes` at its own turn, and `--yes` never answers it.
5. **It looks again**, and tells you what came right, what is still wrong and why, and what to try next. It ends `[ OK ] Restored` when every check that must pass does, and `[FAIL] Not fully restored` otherwise, with the commands that go on from there. Then it offers the optional things, such as the nightly backup, one at a time.

What it can put right by itself:

| Found | What it does |
|---|---|
| The service account is missing | Creates it as a system account that cannot sign in |
| Files belong to someone else (what a command run as root leaves, and the cause of "attempt to write a readonly database") | Gives `data/` and `.env` back to the service account, private |
| `.env`, the database or the code are readable or writable by other users | Sets the modes the install should have |
| Program files are gone | Asks git for each file that is gone; files you changed on purpose are left alone |
| `.env` is missing, or has a byte-order mark or Windows line ends | Starts a new one from the example (you enter your keys again), or cleans it and keeps the old file beside it |
| The Python environment, a package or the Docker image is missing | Builds it again from the lock file (downloads packages); installs `uv` first if that is missing |
| The database is behind the code | Takes a backup, then applies the migrations |
| The database is damaged or missing | The [database](#the-database-is-damaged) step: tests the backups, keeps the damaged file aside, restores the one you pick |
| The service file points at something that is gone, or its sandbox leaves the database read-only | Writes it again as the installer would, keeping the old one |
| systemd has not read the file, gave up after failed starts, or the service is not enabled; Docker is not running | Reloads, resets, enables, starts |
| Caddy is not running, or passes the page to the wrong port; ufw blocks the ports | Restarts it; points it at the right port, or puts the old Caddyfile back if it will not load; opens the ports |
| The clock is not synchronised | Turns on time synchronisation |
| The disk is full | The [space](#the-disk-is-full) step |

What it leaves to you, and says so: DNS, a deploy key, lines of `.env` it cannot read or that repeat, a port another program holds, the model key and the family list on the page, an upgrade that stopped part-way, FamilyDB running twice, a disk that went read-only.

What it never does: spend money (it makes no model call), send a message, change a setting saved on the page, replace or delete data without a typed `yes`, or change anything under `--dry-run`, which shows the plan and stops. Without a terminal and without `--yes` it prints the plan, changes nothing and exits 1. It exits 0 when it ends restored.

## How it keeps you safe

- **It looks first and says what it found**, in the same words as the check, before it offers anything.
- **It asks before each change**, one change at a time. Enter means yes for a change that can be undone by running something; the question that costs data (putting a database back, deleting backups, signing everyone out) needs a typed `yes` at a terminal, and `--yes` never answers it. Without a terminal it says so and does nothing, and prints the command to run from a terminal.
- **It backs the database up before it touches it**, and what it replaces is kept beside the backups, not thrown away: a damaged database goes to a `set-aside-…` folder, and the database as it was before a rollback is a backup you can `restore`.
- **`--dry-run` shows what it would do** and changes nothing.
- **It uses the program only where it has to** (making a password), so it does not depend on the thing that is broken. Everything it does is in `/var/log/familydb-maintain.log`.

## Nobody can get in

`rescue locked-out`. It shows whether the service runs, whether the page answers, whether the page is switched on in `.env`, the address, and who can sign in. Then it offers, in order:

1. **Switch the page on** and restart, if `WEB_ENABLED` is off. A page that is off has nothing to sign in to.
2. **Restart the bot**, which clears "Too many tries": the counts are kept in memory. A message being answered is interrupted.
3. **A new password** for a person you name (or the first admin, or the family password while everyone still shares one). It is printed once, as with `maintain.sh password`, and you pass it on. This needs a terminal.
4. **Sign everyone out**, on every device, by deleting the key their sign-ins are signed with. Typed `yes` only. It cannot be used while `WEB_SECRET_KEY` is set in `.env`; change that value instead.

It ends with the way in when the address itself does not open (a certificate, DNS or the firewall): an SSH tunnel from your own computer to the page, which needs none of them. See also [Recovery](/wiki/operations/recovery).

## It will not start, or keeps stopping

`rescue wont-start`. It runs the checks that bear on starting (files, git, `.env`, Python, the database file and the service), shows what is wrong and the last lines of its log, and offers the remedy for each thing it found:

- **Give the service its files back**, when the data folder, the database or `.env` belongs to someone else. A command run as root makes files the service cannot then write.
- **Put back the program files** that are gone or changed (a `git checkout` of every tracked file; changes to them are lost).
- **Build the Python environment again** from the lock file, when the interpreter is gone (after an operating system upgrade, say) or a package is missing. On Docker, build the image again. Nothing in `data/` is touched.
- **Apply the migrations** a database that is behind is missing, after a backup.
- **Read a changed unit file**, and clear systemd's "too many failed starts".
- **Forget one setting saved on the settings page**, when a saved value is what stops it starting. It asks which, takes a backup, and the setting falls back to `.env` or its default. You then set it again from the page.

Then it restarts the bot and says whether it came back. If it still does not, it points at the log, at `rescue rollback` and at `rescue database`.

## An upgrade broke it

`rescue rollback`. `maintain.sh upgrade` records what it moved from and to, so the way back is known even after it finished. The rollback shows the version you are on and the one it goes back to, and then decides what has to go back:

- **If no migration ran**, only the code goes back. Nothing saved is lost, and it asks with Enter for yes.
- **If the upgrade migrated the database**, the old code cannot read it, so the database from before the upgrade goes back too. Everything saved since is lost: it says so, shows the backup and when it was made, and wants a typed `yes`.

It takes a copy of the database as it is now first, checks out the earlier version, installs the packages that version used (or rebuilds the image), puts the old database back if it must, and starts the bot. The copy is named at the end, with the command that undoes the data part. An upgrade that stopped part-way is undone the same way. With nothing recorded it says so and prints the commands to do it by hand.

## The database is damaged

`rescue database`. It asks SQLite whether the file is sound. If it is, it stops there: the trouble is elsewhere. If not, it lists the newest backups and tests each, then offers:

- **Restore one.** Pick from the list (Enter takes the newest sound one). The damaged database is kept, the backup validated and put in place, the schema brought up to date, and the bot started. Typed `yes`, because everything saved after the backup is lost.
- **Salvage** what can be read of the damaged file into a new file beside the backups, using the `sqlite3` program (`sudo apt-get install sqlite3`) when it is installed. It never touches the original. If the result is sound it prints the `restore` command to put it in place, so you can look first.

## The disk is full

`rescue space`. A full disk stops every write, messages included. It shows the free space and what can be freed, with sizes: the system journal (cut to 200 MB), apt's download cache, uv's cache, Docker's unused images and build cache, and backups older than the keep time (14 days unless `--keep-days` says otherwise). Everything except the old backups is a normal Enter-for-yes question; deleting backups needs a typed `yes` and always leaves the newest ones. It ends with the free space before and after. The other large thing is the model-call texts the program keeps: lower **keep_ai_text_days** on the [Troubleshooting card](/wiki/controls/settings/troubleshooting).

## When even the script will not run

If `maintain.sh` itself fails, these are what it would do:

```bash
sudo systemctl status familydb --no-pager
sudo journalctl -u familydb -n 100 --no-pager
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor
sudo git -C /opt/familydb status
sudo git -C /opt/familydb log --oneline --decorate -10
ls -la /opt/familydb/data /opt/familydb/backups
df -h /opt/familydb; free -h
```

[Backup and restore](/wiki/operations/backup-and-restore) has the by-hand restore, and `/opt/familydb/RUNBOOK.md` on the server does not need the page. Save the log `/var/log/familydb-maintain.log` and the output of `maintain.sh check --all` if you need someone else to look.
