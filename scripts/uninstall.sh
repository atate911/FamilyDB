#!/usr/bin/env bash
# Take FamilyDB off this machine, either keeping what the family said or removing that too.
#
#   scripts/uninstall.sh              stop it, remove the service and the installed code, and
#                                     keep .env, data/ and the backups. This is what you want
#                                     before reinstalling.
#   scripts/uninstall.sh --purge      remove all of that as well, including the database.
#
# It prints what it is about to remove, and what it is leaving, before removing anything.
#
# The database is the only copy of everything the family has ever said, so --purge takes a
# backup first unless told not to, will not run without a typed confirmation, and refuses to
# touch a directory that does not look like a FamilyDB install.
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

TARGET=""
SERVICE_USER="familydb"
PURGE=0
FORCE=0
DRY_RUN=0
ASSUME_YES=0
BACKUP=1
BACKUP_DIR=""
REMOVE_USER=1

usage() {
  cat <<'USAGE'
Remove FamilyDB from this machine.

  scripts/uninstall.sh [options]

What is removed
  (default)            The service and the unit, the virtualenv, the containers and the image.
                       Kept: .env, data/ (the database, the Google token, the login key),
                       backups/ and caddy/. Reinstalling over this picks up where it left off.
  --purge              All of the above, and everything that was kept: the database, the
                       configuration, the backups and the service user. Nothing is left.

Options
  --target DIR         The install to remove. Default: the checkout this script is in.
  --user NAME          The system user to remove on --purge. Default: familydb.
  --keep-user          Leave the system user alone on --purge.
  --backup-to DIR      Where --purge writes its backup. Default: /var/backups/familydb.
  --no-backup          Do not back the database up before --purge. Say this deliberately.
  --force              Do not ask. For scripts; with --purge this deletes the database at once.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Examples
  scripts/uninstall.sh                          # clean slate for a reinstall
  scripts/uninstall.sh --purge                  # remove it and everything it knows
  scripts/uninstall.sh --purge --backup-to /mnt/usb
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --user) SERVICE_USER="${2:-}"; shift 2 ;;
    --user=*) SERVICE_USER="${1#*=}"; shift ;;
    --keep-user) REMOVE_USER=0; shift ;;
    --backup-to) BACKUP_DIR="${2:-}"; shift 2 ;;
    --backup-to=*) BACKUP_DIR="${1#*=}"; shift ;;
    --no-backup) BACKUP=0; shift ;;
    --purge) PURGE=1; shift ;;
    --force|--yes|-y) FORCE=1; ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done
export ASSUME_YES DRY_RUN

log_to "/var/log/familydb-uninstall.log"
enable_failure_reporting
on_failure_hint "Nothing is removed until the step that removes it runs, so a failure here leaves the install as it was. docs/INSTALL.md, 'Removing it', covers the rest."

# --------------------------------------------------------------- safety ----
if [ -z "$TARGET" ]; then
  TARGET="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
fi
[ -d "$TARGET" ] || die "no such directory: ${TARGET}"
TARGET="$(cd -- "$TARGET" && pwd -P)"

# Deleting the wrong directory is the one mistake this script must not be able to make.
case "$TARGET" in
  /|/usr|/usr/*|/etc|/etc/*|/var|/var/*|/home|/root|/bin|/sbin|/lib|/lib64|/boot|/opt|/srv|/tmp)
    die "refusing to touch ${TARGET}: that is a system directory, not a FamilyDB install"
    ;;
esac
if [ ! -f "${TARGET}/pyproject.toml" ] || ! grep -q 'name = "familydb"' "${TARGET}/pyproject.toml"; then
  die "${TARGET} does not look like a FamilyDB install (no familydb pyproject.toml). Use --target."
fi

head2 "Removing FamilyDB from ${TARGET}"
[ "$DRY_RUN" = 1 ] && note "Dry run: nothing will actually be removed."

if [ "$PURGE" = 1 ]; then
  plan_item "Stop the bot, and remove the systemd unit or the containers" \
    "so nothing starts it again at boot"
  plan_item "Delete ${TARGET}/data" \
    "the database with every idea, plan and message, the Google token, and the web login key"
  plan_item "Delete ${TARGET}/.env" \
    "the API keys, the page password and the rest of the configuration"
  plan_item "Delete ${TARGET} itself, and any backups inside it" \
    "nothing of the install is left behind"
  [ "$REMOVE_USER" = 1 ] && plan_item "Remove the '${SERVICE_USER}' system user" \
    "it exists only to run this"
  [ "$BACKUP" = 1 ] && plan_item "Take one last backup of the database first" \
    "so a change of mind is still possible; it is written outside ${TARGET} and left there"
else
  plan_item "Stop the bot, and remove the systemd unit or the containers" \
    "so nothing starts it again at boot"
  plan_item "Delete the virtualenv and the caches inside ${TARGET}" \
    "these are rebuilt by an install, and nothing in them is yours"
  plan_untouched "${TARGET}/data — the database, the Google token and the login key"
  plan_untouched "${TARGET}/.env — your keys and configuration"
  plan_untouched "any backups, inside ${TARGET} or outside it"
fi
plan_untouched "Docker and uv, which other things may be using"
plan_untouched "your Telegram bot, your Google project, and your API keys at each provider"
show_plan "What this will remove"

if [ "$PURGE" = 0 ] && [ "$DRY_RUN" = 0 ] && ! approve "Remove the service and the installed files?"; then
  say "Nothing was removed."
  exit 0
fi

# ------------------------------------------------------------- the service ----
head2 "Stopping it"
UNIT=/etc/systemd/system/familydb.service
if have systemctl && [ -f "$UNIT" ]; then
  system_change "Stop familydb, remove its unit, and tell systemd to forget it" \
    "otherwise it would start again at the next boot"
  try_step "Stopping and disabling the service" as_root systemctl disable --now familydb
  step "Removing ${UNIT}" as_root rm -f "$UNIT"
  try_step "Reloading systemd" as_root systemctl daemon-reload
elif have systemctl && systemctl list-unit-files 2>/dev/null | grep -q '^familydb.service'; then
  try_step "Stopping and disabling the service" as_root systemctl disable --now familydb
else
  note "No systemd unit here."
fi

if have docker && [ -f "${TARGET}/docker-compose.yml" ]; then
  if docker compose --project-directory "$TARGET" ps >/dev/null 2>&1; then
    system_change "Stop and remove the containers" "so nothing restarts them"
    step "Stopping the containers" as_root docker compose --project-directory "$TARGET" down --remove-orphans
    if [ "$PURGE" = 1 ]; then
      try_step "Removing the familydb:local image" as_root docker image rm familydb:local
    fi
  fi
fi

# Anything still running from this checkout would rewrite files after they are removed.
if pgrep -af "${TARGET}/.venv/bin/familydb" >/dev/null 2>&1; then
  warn "Something is still running from ${TARGET}:"
  pgrep -af "${TARGET}/.venv/bin/familydb" >&2 || true
  [ "$FORCE" = 1 ] || die "stop it first, or re-run with --force"
fi

# ---------------------------------------------------------------- backup ----
DB="${TARGET}/data/familydb.sqlite3"
if [ "$PURGE" = 1 ] && [ "$BACKUP" = 1 ] && [ -f "$DB" ]; then
  head2 "Backing the database up first"
  BACKUP_DIR="${BACKUP_DIR:-/var/backups/familydb}"
  stamp="$(date +%Y%m%d%H%M%S)"
  dest="${BACKUP_DIR}/familydb-${stamp}.sqlite3"
  if [ "$DRY_RUN" = 1 ]; then
    note "would back the database up to ${dest}"
  else
    as_root mkdir -p "$BACKUP_DIR"
    # Never copy a main SQLite file alone: committed data may still be in its WAL.
    if [ -x "${TARGET}/.venv/bin/familydb" ] \
       && as_root env FAMILYDB_PATH="$DB" "${TARGET}/.venv/bin/familydb" db backup "$dest" >/dev/null 2>&1; then
      ok "Backup written with SQLite's backup API."
    else
      have python3 || die "Python 3 is needed for a safe backup; purge stopped"
      as_root python3 - "$DB" "$dest" <<'PY'
import sqlite3, sys
from contextlib import closing
from pathlib import Path
with closing(sqlite3.connect(Path(sys.argv[1]).as_uri() + '?mode=ro', uri=True)) as source:
    with closing(sqlite3.connect(sys.argv[2])) as target:
        source.backup(target)
        if target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup validation failed; purge stopped')
PY
      ok "Backup written with SQLite's backup API."
    fi
    as_root chmod 600 "$dest"
    say "  ${B}${dest}${OFF}"
    say "  That file is the only copy of everything the family said. Keep it somewhere safe."
  fi
fi

# ----------------------------------------------------------- confirmation ----
if [ "$PURGE" = 1 ] && [ "$FORCE" = 0 ] && [ "$DRY_RUN" = 0 ]; then
  head2 "This cannot be undone"
  say "About to remove:"
  say "  ${TARGET}/data          the database, the Google token and the login key"
  say "  ${TARGET}/.env          the keys and the configuration"
  say "  ${TARGET}               the code itself"
  [ "$REMOVE_USER" = 1 ] && say "  the ${SERVICE_USER} system user"
  say ""
  if [ ! -t 0 ]; then
    die "not a terminal, so there is nobody to ask. Re-run with --force if you mean it."
  fi
  printf 'Type %sremove everything%s to go ahead: ' "$B" "$OFF"
  read -r answer || answer=""
  [ "$answer" = "remove everything" ] || die "stopped. Nothing was removed."
fi

# ---------------------------------------------------------------- removal ----
head2 "Removing"

# Remove only the schedule installed by maintain.sh; leave unrelated root jobs alone.
if [ "$DRY_RUN" = 0 ] && have crontab; then
  current_cron="$(as_root crontab -u root -l 2>/dev/null || true)"
  if printf '%s\n' "$current_cron" | grep -q 'familydb-maintain-backup'; then
    printf '%s\n' "$current_cron" | sed '/familydb-maintain-backup/d' | as_root crontab -u root -
  fi
fi

# What an install puts there, and nothing else: a reinstall rebuilds every one of these.
# `.cache` is uv's, which lands here because the service user's home is the install itself.
for path in .venv .cache .ruff_cache .pytest_cache; do
  if [ -e "${TARGET}/${path}" ]; then
    step "Removing ${path}" as_root rm -rf "${TARGET:?}/${path}"
  fi
done
# Compiled Python left behind by an install. Quiet: there can be hundreds.
if [ "$DRY_RUN" = 0 ]; then
  as_root find "$TARGET" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  ok "Removed the compiled Python caches"
else
  note "[dry run] Removing the compiled Python caches"
fi

if [ "$PURGE" = 0 ]; then
  head2 "Done"
  say "The service is gone and the installed files are removed."
  say "Kept: ${TARGET}/.env, ${TARGET}/data, and any backups beside them."
  say ""
  say "To put it back:  cd ${TARGET} && scripts/install.sh"
  say "To remove the rest as well:  scripts/uninstall.sh --purge"
  exit 0
fi

for path in data caddy .env; do
  if [ -e "${TARGET}/${path}" ]; then
    step "Removing ${path}" as_root rm -rf "${TARGET:?}/${path}"
  fi
done
# .env backups the installer wrote when it was re-run.
try_step "Removing old .env backups" as_root find "$TARGET" -maxdepth 1 -name '.env.*.bak' -delete

if [ -d "${TARGET}/backups" ]; then
  step "Removing backups/ from inside the install" as_root rm -rf "${TARGET:?}/backups"
  note "Any backup kept outside ${TARGET} is untouched."
fi

# The checkout itself, but only when this script is not inside the thing it is deleting.
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "$HERE" in
  "${TARGET}"/*|"$TARGET")
    warn "Not removing ${TARGET} itself: this script is inside it."
    note "Finish with:  cd / && sudo rm -rf ${TARGET}"
    ;;
  *)
    step "Removing ${TARGET}" as_root rm -rf "${TARGET:?}"
    ;;
esac

if [ "$REMOVE_USER" = 1 ] && id "$SERVICE_USER" >/dev/null 2>&1; then
  if [ "$SERVICE_USER" = root ] || [ "$(id -u "$SERVICE_USER")" -lt 100 ]; then
    warn "Refusing to remove ${SERVICE_USER}: that is not a service account this created."
  else
    try_step "Removing the ${SERVICE_USER} user" as_root userdel "$SERVICE_USER"
    if [ "$LAST_STEP_STATUS" != 0 ]; then
      note "Something else may still be running as it, or own files it owns. Find them with:"
      note "  sudo find / -xdev -user ${SERVICE_USER} 2>/dev/null | head"
    fi
  fi
fi

head2 "Done"
say "FamilyDB is off this machine."
if [ "$BACKUP" = 1 ] && [ -n "${dest:-}" ]; then
  say "The backup is still at ${B}${dest}${OFF}. Delete it too when you are sure."
fi
say ""
say "Things this did not touch, because they are not ours to remove:"
say "  · Docker itself, and uv"
say "  · the Telegram bot (delete it with /deletebot in @BotFather)"
say "  · the Google Cloud project and its OAuth client"
say "  · the API keys at each provider, which are still live until you revoke them"
