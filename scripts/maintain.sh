#!/usr/bin/env bash
# Looking after a running FamilyDB: backups, restores, upgrades, logs and status.
#
#   scripts/maintain.sh status          is it running, and is it healthy?
#   scripts/maintain.sh backup          take a backup now
#   scripts/maintain.sh restore FILE    put a backup back
#   scripts/maintain.sh upgrade         fetch the newest release and restart
#   scripts/maintain.sh logs            follow the log
#   scripts/maintain.sh schedule-backups   a nightly backup in cron
#
# Every one of these says what it is about to change before it changes it, and explains any
# failure in terms of what to do next. Nothing here ever deletes a backup.
set -euo pipefail

# shellcheck disable=SC2034  # read by lib/common.sh when it opens the transcript.
SCRIPT_ARGS="$*"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -r "${HERE}/lib/common.sh" ]; then
  # shellcheck source=lib/common.sh
  . "${HERE}/lib/common.sh"
else
  printf 'This script needs scripts/lib/common.sh beside it.\n' >&2
  exit 1
fi

TARGET="$(cd -- "${HERE}/.." && pwd -P)"
SERVICE_USER="familydb"
BACKUP_DIR=""
KEEP_DAYS=14
ASSUME_YES=0
DRY_RUN=0
COMMAND=""

usage() {
  cat <<'USAGE'
Look after a running FamilyDB.

  scripts/maintain.sh COMMAND [options]

Commands
  status               Is it running, is it healthy, how big is the database, when was the
                       last backup. Changes nothing.
  check                The full check (familydb doctor), with every finding and its fix.
  backup               Take a backup now, using SQLite's online backup, safe while it runs.
  restore FILE         Stop the bot, put that backup in place, start it again. The database
                       being replaced is itself backed up first.
  upgrade              Fetch the newest release, reinstall the dependencies, migrate and
                       restart. Takes a backup first.
  logs [N]             Follow the log, starting with the last N lines (default 50).
  restart              Restart it, and say whether it came back.
  schedule-backups     Add a nightly backup to cron, and prune ones older than --keep-days.

Options
  --target DIR         Which install. Default: the checkout this script lives in.
  --user NAME          The account that owns the data. Default: familydb.
  --backup-dir DIR     Where backups go. Default: <target>/backups.
  --keep-days N        How long scheduled backups are kept. Default: 14.
  --yes                Do not ask.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Examples
  scripts/maintain.sh status
  sudo scripts/maintain.sh backup --backup-dir /mnt/backups
  sudo scripts/maintain.sh restore /mnt/backups/familydb-2026-09-14.sqlite3
  sudo scripts/maintain.sh upgrade
USAGE
}

[ $# -gt 0 ] || { usage; exit 0; }
COMMAND="$1"; shift
RESTORE_FILE=""
LOG_LINES=50
case "$COMMAND" in
  restore) RESTORE_FILE="${1:-}"; [ -n "$RESTORE_FILE" ] && shift ;;
  logs) case "${1:-}" in ''|-*) ;; *) LOG_LINES="$1"; shift ;; esac ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --user) SERVICE_USER="${2:-}"; shift 2 ;;
    --user=*) SERVICE_USER="${1#*=}"; shift ;;
    --backup-dir) BACKUP_DIR="${2:-}"; shift 2 ;;
    --backup-dir=*) BACKUP_DIR="${1#*=}"; shift ;;
    --keep-days) KEEP_DAYS="${2:-}"; shift 2 ;;
    --keep-days=*) KEEP_DAYS="${1#*=}"; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done
export ASSUME_YES DRY_RUN

TARGET="$(cd -- "$TARGET" 2>/dev/null && pwd -P || echo "$TARGET")"
[ -f "${TARGET}/pyproject.toml" ] && grep -q 'name = "familydb"' "${TARGET}/pyproject.toml" 2>/dev/null \
  || die "${TARGET} is not a FamilyDB install" \
         "Point at one with --target, or run this from inside the checkout."

BACKUP_DIR="${BACKUP_DIR:-${TARGET}/backups}"
DB="${TARGET}/data/familydb.sqlite3"
FAMILYDB="${TARGET}/.venv/bin/familydb"
DOCKER_MODE=0
[ -x "$FAMILYDB" ] || { [ -f "${TARGET}/docker-compose.yml" ] && have docker && DOCKER_MODE=1; }

log_to "/var/log/familydb-maintain.log"
enable_failure_reporting
on_failure_hint "RUNBOOK section 13 lists what each failure usually means. Nothing was half-done: each step here either finished or was not started."

# familydb, however this install runs it.
familydb_cmd() {
  if [ "$DOCKER_MODE" = 1 ]; then
    as_root docker compose --project-directory "$TARGET" run --rm -T bot familydb "$@"
  elif [ "$(id -un)" = "$SERVICE_USER" ]; then
    (cd "$TARGET" && "$FAMILYDB" "$@")
  else
    (cd "$TARGET" && as_root sudo -u "$SERVICE_USER" env HOME="$TARGET" "$FAMILYDB" "$@")
  fi
}

service_installed() { [ -f /etc/systemd/system/familydb.service ]; }
service_active() { have systemctl && systemctl is-active --quiet familydb; }

stop_bot() {
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Stopping the containers" as_root docker compose --project-directory "$TARGET" stop bot
  elif service_installed; then
    step "Stopping the service" as_root systemctl stop familydb
  else
    note "Nothing to stop: no service and no containers."
  fi
}

start_bot() {
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Starting the containers" as_root docker compose --project-directory "$TARGET" up -d
  elif service_installed; then
    step "Starting the service" as_root systemctl start familydb
    sleep 3
    if service_active; then
      ok "It came back up."
    else
      warn "It did not come back up. The last 20 lines:"
      as_root journalctl -u familydb -n 20 --no-pager >&2 || true
      note ""
      note "What to try, in order:"
      note "  sudo -u ${SERVICE_USER} ${FAMILYDB} doctor     # names what is wrong"
      note "  sudo systemctl status familydb"
      note "  sudo journalctl -u familydb -n 100 --no-pager"
    fi
  else
    note "No service to start. Run it in the foreground: sudo -u ${SERVICE_USER} ${FAMILYDB} run"
  fi
}

# Sets LAST_BACKUP to the file it wrote. It cannot return the path on stdout, because it also
# prints for a person to read, and the two would arrive mixed together.
LAST_BACKUP=""
take_backup() { # take_backup DEST_DIR "why"
  local dir="$1" why="$2" dest stamp owner
  stamp="$(date +%Y%m%d%H%M%S%N)"
  dest="${dir}/familydb-${stamp}.sqlite3"
  LAST_BACKUP="$dest"
  [ -f "$DB" ] || die "there is no database at ${DB}, so there is nothing to back up" \
    "If the bot has never run, that is expected. Otherwise check FAMILYDB_PATH in .env."
  system_change "Write a backup to ${dest}" "$why"
  if [ "$DRY_RUN" = 1 ]; then return 0; fi
  as_root mkdir -p "$dir"
  dir="$(cd -- "$dir" && pwd -P)"
  dest="${dir}/familydb-${stamp}.sqlite3"
  LAST_BACKUP="$dest"
  owner="${SERVICE_USER}:${SERVICE_USER}"
  if [ "$DOCKER_MODE" = 1 ]; then owner="$(stat -c '%u:%g' "$DB")"; fi
  # The online backup runs as the service account, so the folder has to be its to write.
  try_step "Making sure ${SERVICE_USER} can write to ${dir}" \
    as_root chown "$owner" "$dir"
  require_free_mb "$dir" \
    "$(( $(stat -c %s "$DB" 2>/dev/null || echo 10000000) / 1000000 + 50 ))" "this backup"
  local success=0
  if [ "$DOCKER_MODE" = 1 ]; then
    if as_root docker compose --project-directory "$TARGET" run --rm -T --no-deps \
      --user "$owner" -v "${dir}:/backup" bot familydb db backup \
      "/backup/$(basename "$dest")" >>"${LOG_FILE:-/dev/null}" 2>&1; then success=1; fi
  elif familydb_cmd db backup "$dest" >>"${LOG_FILE:-/dev/null}" 2>&1; then
    success=1
  fi
  if [ "$success" = 1 ] && [ -s "$dest" ]; then
    ok "Backup written with SQLite's online backup, which is safe while the bot is running."
  else
    # An incomplete backup must not look usable to restore, upgrade, or an operator.
    as_root rm -f -- "$dest"
    die "SQLite online backup failed; no backup was created" \
      "The database was not copied or replaced. See ${LOG_FILE:-the transcript} and fix the error before continuing."
  fi
  as_root chmod 600 "$dest"
  as_root chown "$owner" "$dest"
}

# ---------------------------------------------------------------- status ----
cmd_status() {
  head2 "FamilyDB at ${TARGET}"

  local version="unknown"
  if [ -d "${TARGET}/.git" ]; then
    version="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo 'unknown')"
  fi
  say "Version:    ${version}"

  if [ "$DOCKER_MODE" = 1 ]; then
    say "Runs as:    Docker containers"
    as_root docker compose --project-directory "$TARGET" ps 2>/dev/null | tail -n +1 || true
  elif service_installed; then
    local active enabled
    active="$(systemctl is-active familydb 2>/dev/null || true)"
    enabled="$(systemctl is-enabled familydb 2>/dev/null || true)"
    active="${active:-unknown}"
    enabled="${enabled:-unknown}"
    say "Service:    ${active}, ${enabled} at boot"
    if [ "$active" = active ]; then
      say "Since:      $(systemctl show familydb -p ActiveEnterTimestamp --value 2>/dev/null || echo '?')"
      say "Memory:     $(systemctl show familydb -p MemoryCurrent --value 2>/dev/null | awk '{if ($1 ~ /^[0-9]+$/) printf "%.0f MB", $1/1048576; else print "?"}')"
    fi
  else
    say "Service:    not installed; started by hand"
  fi

  if [ -f "$DB" ]; then
    say "Database:   ${DB} ($(du -h "$DB" 2>/dev/null | cut -f1))"
  else
    warn "No database at ${DB} yet."
  fi
  local free
  free="$(df -Ph "$TARGET" 2>/dev/null | awk 'NR==2 {print $4 " free of " $2}')"
  say "Disk:       ${free:-unknown}"

  local newest
  newest="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -printf '%T@ %p\n' 2>/dev/null \
            | sort -rn | head -1 | cut -d' ' -f2- || true)"
  if [ -n "$newest" ]; then
    say "Last backup: $(as_root stat -c '%y' "$newest" 2>/dev/null | cut -d. -f1) — ${newest}"
  else
    warn "No backups in ${BACKUP_DIR}."
    note "Take one now:  sudo ${0} backup"
    note "Or nightly:    sudo ${0} schedule-backups"
  fi
  if as_root crontab -u root -l 2>/dev/null | grep -q 'familydb-maintain-backup'; then
    say "Scheduled:  a nightly backup is in root's crontab"
  elif as_root crontab -u "$SERVICE_USER" -l 2>/dev/null | grep -q 'familydb db backup'; then
    say "Scheduled:  a nightly backup is in ${SERVICE_USER}'s crontab"
  fi
  say ""
  note "For the full check, with every finding and its fix:  ${0} check"
}

cmd_check() {
  head2 "Checking the install"
  familydb_cmd doctor || true
}

# ---------------------------------------------------------------- backup ----
cmd_backup() {
  head2 "Taking a backup"
  take_backup "$BACKUP_DIR" "so today's state can be put back if something goes wrong"
  say ""
  say "Backup: ${B}${LAST_BACKUP}${OFF}"
  say "Copy it somewhere that is not this machine. A backup on the same disk is not a backup:"
  say "  scp ${LAST_BACKUP} you@your-computer:~/"
}

cmd_restore() {
  [ -n "$RESTORE_FILE" ] || die "which backup?" "Usage: ${0} restore /path/to/familydb-....sqlite3"
  [ -f "$RESTORE_FILE" ] || die "no such file: ${RESTORE_FILE}" \
    "Look in ${BACKUP_DIR}:" "  ls -lh ${BACKUP_DIR}"
  # Always validate before stopping or replacing anything. A successful sqlite3 exit
  # code alone does not mean quick_check returned 'ok'.
  local validate target_owner
  validate='import sqlite3,sys; from pathlib import Path; c=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+"?mode=ro",uri=True); assert c.execute("pragma quick_check").fetchone()[0]=="ok"; c.execute("select id from members limit 1"); c.close()'
  target_owner="${SERVICE_USER}:${SERVICE_USER}"
  if [ "$DOCKER_MODE" = 1 ]; then
    RESTORE_FILE="$(cd -- "$(dirname -- "$RESTORE_FILE")" && pwd -P)/$(basename -- "$RESTORE_FILE")"
    as_root docker compose --project-directory "$TARGET" run --rm -T --no-deps \
      --user 0:0 -v "${RESTORE_FILE}:/restore.sqlite3:ro" bot python -c "$validate" /restore.sqlite3 \
      || die "backup validation failed; nothing was restored"
    target_owner="$(stat -c '%u:%g' "$DB" 2>/dev/null || echo 1000:1000)"
  else
    as_root "${TARGET}/.venv/bin/python" -c "$validate" "$RESTORE_FILE" \
      || die "backup validation failed; nothing was restored"
  fi

  head2 "Putting a backup back"
  say "From: ${RESTORE_FILE} ($(du -h "$RESTORE_FILE" | cut -f1), $(stat -c '%y' "$RESTORE_FILE" | cut -d. -f1))"
  say "Over: ${DB}"
  say ""
  say "The bot stops while this happens. Everything it has been told since that backup was"
  say "taken will be gone. The database being replaced is itself backed up first, so this"
  say "can be undone."
  approve "Replace the database with that backup?" || { say "Nothing was changed."; exit 0; }

  local safety=""
  if [ -f "$DB" ]; then
    take_backup "$BACKUP_DIR" "so this restore itself can be undone"
    safety="$LAST_BACKUP"
  fi
  stop_bot
  step "Putting ${RESTORE_FILE} in place" as_root cp "$RESTORE_FILE" "$DB"
  # The write-ahead files belong to the database that was just replaced.
  try_step "Clearing the write-ahead files" as_root rm -f "${DB}-wal" "${DB}-shm"
  step "Restoring database ownership" as_root chown "$target_owner" "$DB"
  step "Protecting the restored database" as_root chmod 600 "$DB"
  step "Bringing the schema up to date" familydb_cmd db migrate
  start_bot
  head2 "Done"
  say "Restored from ${RESTORE_FILE}."
  [ -n "$safety" ] && say "What was there before is at ${safety}, if you need it back."
}

# --------------------------------------------------------------- upgrade ----
cmd_upgrade() {
  head2 "Upgrading"
  [ -d "${TARGET}/.git" ] || die "${TARGET} is not a git checkout, so there is nothing to pull" \
    "Upgrade by unpacking a new copy over it, keeping .env and data/."

  local current
  current="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)"
  say "Currently on: ${current}"

  plan_item "Fetch the newest release from the git remote" \
    "this is the code the bot runs; nothing about your configuration or data changes"
  plan_item "Reinstall the dependencies at their locked versions" \
    "a new release may need a library version this machine does not have"
  plan_item "Apply any new database migrations" \
    "they are applied in order and never rewrite what is already there"
  plan_item "Restart the bot" \
    "the new code only takes effect once the process restarts"
  plan_untouched ".env, your keys, and everything the family has told it"
  show_plan "What upgrading does"
  approve "Upgrade now?" || { say "Nothing was changed."; exit 0; }

  take_backup "$BACKUP_DIR" "so a bad upgrade can be undone"

  # A private repository needs a credential here. bootstrap.sh leaves the deploy key wired up
  # when one was used, and deliberately does not write a token down, so say which case this is.
  # shellcheck disable=SC2034  # lib/common.sh names this in its failure report.
  FAILED_STEP="fetching the newest code"
  if ! as_root git -C "$TARGET" fetch --tags --quiet origin 2>>"${LOG_FILE:-/dev/null}"; then
    local remote sshcmd
    remote="$(as_root git -C "$TARGET" remote get-url origin 2>/dev/null || echo unknown)"
    sshcmd="$(as_root git -C "$TARGET" config core.sshCommand 2>/dev/null || true)"
    die "could not fetch from ${remote}" \
        "What this means: this is a private repository, and this checkout has no credential" \
        "it can use. Nothing was changed." \
        "" \
        "What to try, depending on how the code got here:" \
        "  · with a deploy key — point the checkout at it:" \
        "      sudo git -C ${TARGET} remote set-url origin git@github.com:atate911/FamilyDB.git" \
        "      sudo git -C ${TARGET} config core.sshCommand 'ssh -i /path/to/key -o IdentitiesOnly=yes'" \
        "      sudo git -C ${TARGET} fetch --tags origin       # should now work" \
        "  · with a token — fetch once with it, without writing it down:" \
        "      sudo git -C ${TARGET} -c http.extraheader=\"AUTHORIZATION: bearer \$TOKEN\" fetch --tags origin" \
        "  · with a copy you made yourself — there is nothing to fetch from. Copy the new" \
        "    version over the top, keeping .env and data/, then run: sudo ${0} restart" \
        "" \
        "Currently configured: ${sshcmd:-no core.sshCommand set}" \
        "docs/INSTALL.md, 'Getting the code onto the box', covers all three."
  fi
  # shellcheck disable=SC2034  # cleared so a later failure does not name this step.
  FAILED_STEP=""
  ok "Fetched the newest code"
  local latest
  latest="$(as_root git -C "$TARGET" tag -l 'v*' --sort=-v:refname 2>/dev/null | head -1 || true)"
  if [ -z "$latest" ]; then
    warn "No release tags found; staying on the current branch and pulling it instead."
    step "Pulling" as_root git -C "$TARGET" pull --ff-only --quiet
  elif [ "$latest" = "$current" ]; then
    ok "Already on ${latest}, the newest release. Nothing to do."
    return 0
  else
    say "Upgrading to: ${latest}"
    step "Checking out ${latest}" as_root git -C "$TARGET" checkout --quiet "$latest"
  fi

  stop_bot
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Rebuilding the image" as_root docker compose --project-directory "$TARGET" build
  else
    retry 2 "Installing the dependencies" \
      as_root env PATH="$SYSTEM_PATH" uv sync --frozen --no-dev --project "$TARGET"
    try_step "Keeping the code owned by root" as_root chmod -R go-w "$TARGET"
  fi
  step "Applying any new migrations" familydb_cmd db migrate
  start_bot

  head2 "Done"
  say "Now on $(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)."
  say "If something is wrong, go back to the previous release:"
  say "  sudo git -C ${TARGET} checkout ${current} && sudo ${0} restart"
  familydb_cmd doctor || true
}

# ------------------------------------------------------------------ logs ----
cmd_logs() {
  if [ "$DOCKER_MODE" = 1 ]; then
    as_root docker compose --project-directory "$TARGET" logs -f --tail "$LOG_LINES" bot
  elif service_installed; then
    as_root journalctl -u familydb -n "$LOG_LINES" -f
  else
    die "there is no service and no container here, so there is no log to follow" \
        "If you run it by hand, the log is wherever you sent that command's output."
  fi
}

cmd_restart() {
  head2 "Restarting"
  stop_bot
  start_bot
}

# ------------------------------------------------------ scheduled backups ----
cmd_schedule_backups() {
  head2 "Nightly backups"
  case "$KEEP_DAYS" in ''|*[!0-9]*) die "--keep-days must be a nonnegative integer" ;; esac
  case "${TARGET}${BACKUP_DIR}" in *$'\n'*|*%*) die "cron paths cannot contain newlines or percent signs" ;; esac
  local line command quoted target_q dir_q
  printf -v target_q '%q' "$TARGET"
  printf -v dir_q '%q' "$BACKUP_DIR"
  command="/bin/bash ${target_q}/scripts/maintain.sh backup --target ${target_q} --backup-dir ${dir_q} --yes && find ${dir_q} -maxdepth 1 -name 'familydb-*.sqlite3' -mtime +${KEEP_DAYS} -delete"
  printf -v quoted '%q' "$command"
  line="15 3 * * * /bin/bash -c ${quoted} # familydb-maintain-backup"
  plan_item "Add a line to root's crontab" \
    "takes a backup at 03:15 and prunes old backups only after a successful backup; supports Docker and systemd"
  plan_item "Create ${BACKUP_DIR}" \
    "where those backups are written"
  plan_item "Remove the older schedule from ${SERVICE_USER}'s crontab, if it is there" \
    "the two lines earlier versions added; this one line replaces them"
  plan_untouched "any backup that already exists"
  show_plan "What scheduling backups does"
  say "The lines themselves:"
  say "  ${line}"
  say ""
  note "It runs this script rather than familydb itself, so a Docker install and a systemd one"
  note "back up the same way, and a backup that fails is never followed by the prune."
  say ""
  approve "Add them to the crontab?" || { say "Nothing was changed."; exit 0; }

  if [ "$DRY_RUN" = 1 ]; then note "[dry run] would install the crontab"; return 0; fi
  as_root mkdir -p "$BACKUP_DIR"
  local existing
  existing="$(as_root crontab -u root -l 2>/dev/null | grep -v 'familydb-maintain-backup' || true)"
  printf '%s\n%s\n' "$existing" "$line" \
    | sed '/^$/d' \
    | as_root crontab -u root - \
    || die "could not write root's crontab" \
           "Check that cron is installed: sudo apt-get install cron"
  # Earlier versions put a backup line and a prune line in the service account's crontab. Left
  # there, they would keep pruning on their own schedule whether or not the backup worked.
  local older
  older="$(as_root crontab -u "$SERVICE_USER" -l 2>/dev/null || true)"
  if printf '%s\n' "$older" | grep -q -e 'familydb db backup' -e 'familydb-\*\.sqlite3'; then
    printf '%s\n' "$older" \
      | grep -v -e 'familydb db backup' -e 'familydb-\*\.sqlite3' \
      | sed '/^$/d' \
      | as_root crontab -u "$SERVICE_USER" - \
      && ok "Removed the older schedule from ${SERVICE_USER}'s crontab." \
      || warn "Could not remove the older schedule; see: sudo crontab -u ${SERVICE_USER} -l"
  fi
  ok "Scheduled. Check it with: sudo crontab -u root -l"
  say ""
  say "A backup on the same disk is only half a backup. Copy them off the machine too, for"
  say "example from your own computer:"
  say "  rsync -av ${SERVICE_USER}@$(hostname -I 2>/dev/null | awk '{print $1}'):${BACKUP_DIR}/ ~/familydb-backups/"
}

case "$COMMAND" in
  status)           cmd_status ;;
  check)            cmd_check ;;
  backup)           cmd_backup ;;
  restore)          cmd_restore ;;
  upgrade)          cmd_upgrade ;;
  logs)             cmd_logs ;;
  restart)          cmd_restart ;;
  schedule-backups) cmd_schedule_backups ;;
  -h|--help|help)   usage ;;
  *) usage >&2; die "unknown command: ${COMMAND}" ;;
esac
