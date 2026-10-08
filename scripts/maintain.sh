#!/usr/bin/env bash
# Looking after a running FamilyDB: backups, restores, upgrades, HTTPS, logs and status.
# `scripts/maintain.sh --help` lists every command.
#
# Nothing here deletes a backup except the nightly prune schedule-backups sets up, which runs
# only after a new backup has been written.
set -euo pipefail

# shellcheck disable=SC2034  # read by lib/common.sh when it opens the transcript.
SCRIPT_ARGS="$*"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -r "${HERE}/lib/common.sh" ] && [ -r "${HERE}/lib/https.sh" ]; then
  # shellcheck source=lib/common.sh
  . "${HERE}/lib/common.sh"
  # shellcheck source=lib/https.sh
  . "${HERE}/lib/https.sh"
else
  printf 'This script needs scripts/lib/common.sh and scripts/lib/https.sh beside it.\n' >&2
  exit 1
fi

TARGET="$(cd -- "${HERE}/.." && pwd -P)"
SERVICE_USER=""   # --user, else the account the install recorded, else familydb
BACKUP_DIR=""
KEEP_DAYS=14
ASSUME_YES=0
DRY_RUN=0
COMMAND=""

usage() {
  _style_usage <<'USAGE'
Look after a running FamilyDB.

  scripts/maintain.sh COMMAND [options]

Look at it (these change nothing)
  status               Is it running, is it healthy, how big is the database, when was the
                       last backup. One screen, with what needs attention at the foot.
  check                The full check (familydb doctor), with every finding and its fix.
  logs [N]             Follow the log, starting with the last N lines (default 50).

Keep it safe
  backup               Take a backup now, using SQLite's online backup, safe while it runs.
  restore FILE         Stop the bot, put that backup in place, start it again. The database
                       being replaced is itself backed up first.
  schedule-backups     Add a nightly backup to cron, and prune ones older than --keep-days.

Change it
  upgrade              Move to the newest version, reinstall the dependencies, migrate and
                       restart. Says what it will do and asks first, takes a backup, and
                       prints how to go back before it changes anything. That is the default
                       branch while CHANGELOG.md says the next version is in progress, else
                       the newest release; it never moves to anything older than what is
                       installed.
  restart              Restart it, and say whether it came back.
  https [DOMAIN] [--port N|random|443]
                       Put the page on HTTPS: at DOMAIN if one is given, else at this server's
                       own address, with a real certificate where it can get one. Opens ports
                       80 and 443 if ufw is on. Run it again after opening a provider's firewall,
                       or to move from an SSH tunnel to a link anyone can open. --port serves the
                       page on another port instead of 443, one the scans that sweep the
                       internet rarely try (random picks one), and --port 443 moves it back.
                       With Docker, only --port: it moves the Caddy container's port.
  port N|random        Move FamilyDB's own port (8080 unless moved), when something else needs
                       it: in .env, in Caddy's configuration and in Docker's, then restart. Behind
                       Caddy the address people open stays as it was; with nothing in front, it
                       is the port people open. A number from 1025 to 65535, or random.
  password [NAME]      A new password for the web page, for one nobody remembers. Printed
                       once. Once people sign in as themselves it is a starting password for
                       NAME, or for the first admin: they sign in with it and choose their
                       own. Until then it is a new family password that everyone signs in with.

Options
  --target DIR         Which install. Default: the checkout this script lives in.
  --user NAME          The account that owns the data. Default: the one the install recorded,
                       else familydb.
  --backup-dir DIR     Where backups go. Default: <target>/backups.
  --keep-days N        How long scheduled backups are kept. Default: 14.
  --port N|random      With https: the port the page is served on. Default: as it was, else 443.
  --yes                Do not ask.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Examples
  scripts/maintain.sh status
  sudo scripts/maintain.sh backup --backup-dir /mnt/backups
  sudo scripts/maintain.sh restore /mnt/backups/familydb-2026-09-14.sqlite3
  sudo scripts/maintain.sh upgrade --dry-run
  sudo scripts/maintain.sh upgrade
  sudo scripts/maintain.sh https --port random
  sudo scripts/maintain.sh port 9090

Output
  Colour is for a terminal; NO_COLOR=1 turns it off and FAMILYDB_ASCII=1 uses plain characters.
  Everything a run prints is also kept in /var/log/familydb-maintain.log.
USAGE
}

# The help text with its section headings in bold and each command or option in cyan.
_style_usage() {
  local line name rest
  local entry='^  ([a-z-][^ ]*( [^ ]+)*)( {2,}(.*))?$'
  while IFS= read -r line; do
    if [[ $line =~ ^[A-Z][^.]*$ ]]; then
      printf '%s%s%s\n' "$B" "$line" "$OFF"
    elif [[ $line =~ $entry ]]; then
      name="${BASH_REMATCH[1]}"; rest="${line#"  ${name}"}"
      printf '  %s%s%s%s\n' "$CYN" "$name" "$OFF" "$rest"
    else
      printf '%s\n' "$line"
    fi
  done
}

[ $# -gt 0 ] || { usage; exit 0; }
COMMAND="$1"; shift
RESTORE_FILE=""
LOG_LINES=50
HTTPS_SITE=""
HTTPS_PORT=""
APP_PORT=""
PASSWORD_FOR=""
case "$COMMAND" in
  https) case "${1:-}" in ''|-*) ;; *) HTTPS_SITE="$1"; shift ;; esac ;;
  port) case "${1:-}" in ''|-*) ;; *) APP_PORT="$1"; shift ;; esac ;;
  password) case "${1:-}" in ''|-*) ;; *) PASSWORD_FOR="$1"; shift ;; esac ;;
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
    --port) HTTPS_PORT="${2:-}"; shift 2 ;;
    --port=*) HTTPS_PORT="${1#*=}"; shift ;;
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

[ -n "$SERVICE_USER" ] || SERVICE_USER="$(recorded_service_user "$TARGET")"
valid_user_name "$SERVICE_USER" \
  || die "--user must be a system account name: lowercase letters, digits, - and _, starting with a letter, not '${SERVICE_USER}'"

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

SERVICE_UNIT="${FAMILYDB_SERVICE_UNIT:-/etc/systemd/system/familydb.service}"   # the override is for tests
service_installed() { [ -f "$SERVICE_UNIT" ]; }
service_active() { have systemctl && systemctl is-active --quiet familydb; }

how_it_runs() { # how the bot is run on this machine, in a few words
  if [ "$DOCKER_MODE" = 1 ]; then
    printf 'Docker containers'
  elif service_installed; then
    printf 'systemd service, as the account %s' "$SERVICE_USER"
  else
    printf 'by hand: no service is installed'
  fi
}

intro() { # intro "Upgrade" - what this is, and which install it is about, before anything happens
  banner "$1"
  kv "Install" "$TARGET"
  kv "Runs as" "$(how_it_runs)"
}

env_file_value() { as_root grep -E "^${1}=" "${TARGET}/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "'\"" || true; }

env_file_set() { # env_file_set KEY VALUE - in place, keeping the file's owner and mode
  local file="${TARGET}/.env"
  if as_root grep -qE "^${1}=" "$file"; then
    as_root sed -i "s|^${1}=.*|${1}=${2}|" "$file"
  else
    printf '%s=%s\n' "$1" "$2" | as_root tee -a "$file" >/dev/null
  fi
}

# What the page says of itself at /healthz: "ok", or why not. Status 0 for ok, 1 for a page that
# does not answer or says it is not well, 2 when it cannot be asked at all (no curl, or no page).
page_health() {
  local host port reply code body
  if [ "$(env_file_value WEB_ENABLED)" = false ]; then printf 'the web page is switched off'; return 2; fi
  have curl || { printf 'curl is not installed, so the page was not asked'; return 2; }
  host="$(env_file_value WEB_HOST)"; port="$(env_file_value WEB_PORT)"; port="${port:-8080}"
  case "$host" in ''|0.0.0.0|::|'[::]') host=127.0.0.1 ;; esac
  case "$host" in *:*) case "$host" in '['*) ;; *) host="[${host}]" ;; esac ;; esac
  reply="$(curl -sS --max-time 3 -w '\n%{http_code}' "http://${host}:${port}/healthz" 2>/dev/null)" \
    || { printf 'nothing answers at %s:%s' "$host" "$port"; return 1; }
  code="${reply##*$'\n'}"
  body="${reply%$'\n'*}"
  if [ "$code" = 200 ]; then printf 'ok'; return 0; fi
  # Its own reason is a sentence; an error page of the web server's is markup, which says nothing.
  case "$body" in '<'*) body="" ;; esac
  printf '%s' "${body:-the page answered with status ${code}}" | tr '\n' ' '
  return 1
}

# After a start: give it up to 30 seconds to answer. Run under _capture, so the line shows the time.
wait_for_page() {
  local waited=0 said status=0
  while :; do
    status=0
    said="$(page_health)" || status=$?
    [ "$status" = 0 ] && break
    [ "$status" = 2 ] && break
    [ "$waited" -lt 30 ] || break
    # A service that has stopped again is not going to answer; no need to wait out the rest.
    if [ "$DOCKER_MODE" = 0 ] && [ "$waited" -ge 3 ] && ! service_active; then break; fi
    sleep 1
    waited=$((waited + 1))
  done
  printf '%s' "$said"
  return "$status"
}

stop_bot() {
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Stopping the containers" as_root docker compose --project-directory "$TARGET" stop bot
  elif service_installed; then
    step "Stopping the service" as_root systemctl stop familydb
  else
    note "Nothing to stop: no service and no containers."
  fi
}

# BOT_STARTED is 1 when it came back and answers, 0 when it did not, empty when nothing was started
# or nobody could tell. The last word of a command reads it.
BOT_STARTED=""
start_bot() {
  BOT_STARTED=""
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Starting the containers" as_root docker compose --project-directory "$TARGET" up -d
  elif service_installed; then
    step "Starting the service" as_root systemctl start familydb
  else
    note "No service to start. Run it in the foreground: cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} run"
    return 0
  fi
  [ "$DRY_RUN" = 1 ] && return 0
  _capture "Waiting for FamilyDB to answer" wait_for_page
  case "$_STATUS" in
    0)
      BOT_STARTED=1
      ok "It came back up, and the page answers." ;;
    2)
      sleep 3
      if [ "$DOCKER_MODE" = 1 ] || service_active; then
        BOT_STARTED=1
        ok "It came back up."
        note "${_OUT}."
      else
        BOT_STARTED=0
      fi ;;
    *)
      BOT_STARTED=0 ;;
  esac
  [ "$BOT_STARTED" = 0 ] || return 0
  if [ "$DOCKER_MODE" = 0 ] && ! service_active; then
    warn "It did not come back up."
  else
    warn "It is running, but the page does not answer yet: ${_OUT:-no reason given}."
  fi
  if [ "$DOCKER_MODE" = 1 ]; then
    note "What to try: sudo docker compose --project-directory ${TARGET} logs --tail 50 bot"
  else
    note "The last 20 lines of its log:"
    as_root journalctl -u familydb -n 20 --no-pager >&2 || true
    note ""
    note "What to try, in order:"
    show_commands <<EOF
  cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} doctor     # names what is wrong
  sudo systemctl status familydb
  sudo journalctl -u familydb -n 100 --no-pager
EOF
  fi
}

# Sets LAST_BACKUP to the file it wrote (stdout is for the person reading).
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
    ok "Backup written ($(du -h "$dest" | cut -f1)), by SQLite's online backup, which is safe while the bot runs."
  else
    # An incomplete backup must not look usable to restore, upgrade, or an operator.
    as_root rm -f -- "$dest"
    die "SQLite online backup failed; no backup was created" \
      "The database was not copied or replaced. See ${LOG_FILE:-the transcript} and fix the error before continuing."
  fi
  as_root chmod 600 "$dest"
  as_root chown "$owner" "$dest"
}

# --- status -------------------------------------------------------------------------------------
# One screen: a verdict, a row for each thing worth knowing, and what to do about any that is not
# well. The rows are gathered first so the verdict can lead.

ROW_LABEL=(); ROW_VALUE=(); ROW_STATE=()
ATTENTION=(); ATTENTION_FIX=()
row()    { ROW_LABEL+=("$1"); ROW_VALUE+=("$2"); ROW_STATE+=("${3:-}"); }
attend() { ATTENTION+=("$1"); ATTENTION_FIX+=("$2"); }   # what is wrong, then the commands for it

BACKUP_STALE_SECONDS=129600   # 36 hours: the same line the bot's own upkeep job draws

status_service() { # the service or containers: sets STATUS_RUNNING to 1, 0 or empty when unknown
  STATUS_RUNNING=""
  if [ "$DOCKER_MODE" = 1 ]; then
    local listing svc state detail
    listing="$(as_root docker compose --project-directory "$TARGET" ps --format '{{.Service}}|{{.State}}|{{.Status}}' 2>/dev/null)" || listing=""
    if [ -z "$listing" ]; then
      row "Containers" "could not be listed: is Docker running?" warn
      return 0
    fi
    while IFS='|' read -r svc state detail; do
      [ -n "$svc" ] || continue
      if [ "$state" = running ]; then
        row "$svc" "${state}, ${detail}" ok
        [ "$svc" != bot ] || STATUS_RUNNING=1
      else
        row "$svc" "${state}, ${detail}" bad
        [ "$svc" != bot ] || STATUS_RUNNING=0
        attend "The ${svc} container is not running" "sudo docker compose --project-directory ${TARGET} up -d
sudo docker compose --project-directory ${TARGET} logs --tail 50 ${svc}   # why it stopped"
      fi
    done <<<"$listing"
    return 0
  fi
  if ! service_installed; then
    row "Service" "not installed; it is started by hand" off
    return 0
  fi
  local active enabled since started up memory
  active="$(systemctl is-active familydb 2>/dev/null || true)"; active="${active:-unknown}"
  enabled="$(systemctl is-enabled familydb 2>/dev/null || true)"; enabled="${enabled:-unknown}"
  if [ "$active" = active ]; then
    STATUS_RUNNING=1
    since="$(systemctl show familydb -p ActiveEnterTimestamp --value 2>/dev/null || true)"
    started="$(date -d "$since" +%s 2>/dev/null || true)"
    up=""; [ -z "$started" ] || up=", up $(fmt_secs $(( $(date +%s) - started )))"
    if [ "$enabled" = enabled ]; then
      row "Service" "running, starts at boot${up}" ok
    else
      row "Service" "running${up}, but it ${enabled} at boot" warn
      attend "FamilyDB will not come back by itself after a reboot" "sudo systemctl enable familydb"
    fi
    memory="$(systemctl show familydb -p MemoryCurrent --value 2>/dev/null | awk '{if ($1 ~ /^[0-9]+$/) printf "%.0f MB", $1/1048576}')"
    [ -z "$memory" ] || row "Memory" "$memory"
  else
    STATUS_RUNNING=0
    row "Service" "${active}, ${enabled} at boot" bad
    attend "FamilyDB is not running" "sudo ${0} restart   # start it again
sudo ${0} logs   # why it stopped"
  fi
}

status_page() { # whether the page answers, and where people open it
  local said code=0 site host port
  if [ "$STATUS_RUNNING" != 0 ]; then
    said="$(page_health)" || code=$?
    case "$code" in
      0) row "Page" "answers, and the scheduled jobs are running" ok
         [ -n "$STATUS_RUNNING" ] || STATUS_RUNNING=1 ;;
      1) row "Page" "$said" bad
         attend "The page does not answer: ${said}" "sudo ${0} logs   # what it says
sudo ${0} check   # what is misconfigured" ;;
      *) row "Page" "not asked: ${said}" off ;;
    esac
  fi
  site="$(env_file_value WEB_DOMAIN)"; host="$(env_file_value WEB_HOST)"; port="$(env_file_value WEB_PORT)"; port="${port:-8080}"
  if [ -n "$site" ]; then
    PUBLIC_PORT="$(env_file_value WEB_PUBLIC_PORT)"; PUBLIC_PORT="${PUBLIC_PORT:-443}"
    row "Address" "$(public_url "$site")"
    if [ "$DOCKER_MODE" = 0 ] && have systemctl; then
      if systemctl is-active --quiet caddy 2>/dev/null; then
        row "HTTPS" "Caddy is serving it" ok
      else
        row "HTTPS" "Caddy is not running, so nobody can open the page from outside" bad
        attend "Caddy, which serves the page over HTTPS, is not running" "sudo systemctl restart caddy
sudo journalctl -u caddy -n 30 --no-pager   # why"
      fi
    fi
  else
    case "${host:-127.0.0.1}" in
      127.0.0.1|localhost|::1) row "Address" "this machine only: reach it through an SSH tunnel to port ${port}" ;;
      *) row "Address" "http://$(this_address):${port}/ (no HTTPS)" warn
         attend "The page is open to the network without HTTPS" "sudo ${0} https   # a certificate and a closed side door" ;;
    esac
  fi
}

status_data() { # the database, the disk, and the backups
  local free_mb free_human percent newest epoch age line cronline at
  if [ -f "$DB" ]; then
    row "Database" "$(du -h "$DB" 2>/dev/null | cut -f1), ${DB}"
  else
    row "Database" "none at ${DB} yet" bad
    attend "There is no database yet" "sudo ${0} restart   # a first start makes one"
  fi
  free_mb="$(df -Pm "$TARGET" 2>/dev/null | awk 'NR==2 {print $4}')"
  free_human="$(df -Ph "$TARGET" 2>/dev/null | awk 'NR==2 {print $4 " free of " $2}')"
  percent="$(df -Ph "$TARGET" 2>/dev/null | awk 'NR==2 {print $5}')"
  if [ -z "$free_mb" ]; then
    row "Disk" "unknown"
  elif [ "$free_mb" -lt 500 ]; then
    row "Disk" "${free_human} (${percent} used): nearly full" bad
    attend "The disk is nearly full" "sudo journalctl --vacuum-size=200M
sudo apt-get clean
docker system prune -af   # if Docker is installed"
  elif [ "$free_mb" -lt 2000 ]; then
    row "Disk" "${free_human} (${percent} used): getting full" warn
  else
    row "Disk" "${free_human} (${percent} used)" ok
  fi

  newest="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -printf '%T@ %p\n' 2>/dev/null \
            | sort -rn | head -1 | cut -d' ' -f2- || true)"
  if [ -n "$newest" ]; then
    epoch="$(as_root stat -c %Y "$newest" 2>/dev/null || echo 0)"
    age=$(( $(date +%s) - epoch ))
    line="$(ago "$age"), $(date -d "@${epoch}" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '?'), $(as_root du -h "$newest" 2>/dev/null | cut -f1)"
    if [ "$age" -gt "$BACKUP_STALE_SECONDS" ]; then
      row "Last backup" "${line}: older than 36 hours" warn
      attend "The newest backup is more than 36 hours old; the nightly one may have stopped" "sudo ${0} backup   # take one now
sudo ${0} schedule-backups   # put the nightly one back"
    else
      row "Last backup" "$line" ok
    fi
    row "" "$newest"
  else
    row "Last backup" "none yet in ${BACKUP_DIR}" warn
    attend "No backup has been taken yet" "sudo ${0} backup   # take one now
sudo ${0} schedule-backups   # and one every night"
  fi
  cronline="$(as_root crontab -u root -l 2>/dev/null | grep 'familydb-maintain-backup' | head -1 || true)"
  if [ -n "$cronline" ]; then
    at="$(printf '%s\n' "$cronline" | awk '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ {printf "%02d:%02d", $2, $1}')"
    row "Schedule" "nightly${at:+ at ${at}}, in root's crontab" ok
  elif as_root crontab -u "$SERVICE_USER" -l 2>/dev/null | grep -q 'familydb db backup'; then
    row "Schedule" "nightly, in ${SERVICE_USER}'s crontab (an older setup)" ok
  else
    row "Schedule" "no nightly backup is scheduled" warn
    [ -z "$newest" ] || attend "Backups only happen when someone takes one" "sudo ${0} schedule-backups"
  fi
}

cmd_status() {
  banner "Status"
  local version="unknown" i bad=0 warns=0 headline mark colour
  if [ -d "${TARGET}/.git" ]; then
    version="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo 'unknown')"
  fi
  row "Version" "$version"
  row "Install" "$TARGET"
  row "Runs as" "$(how_it_runs)"
  status_service
  status_page
  status_data

  for i in "${!ROW_STATE[@]}"; do
    case "${ROW_STATE[i]}" in bad) bad=$((bad + 1)) ;; warn) warns=$((warns + 1)) ;; esac
  done
  if [ "$STATUS_RUNNING" = 0 ]; then
    mark="$S_BAD"; colour="$RED"; headline="FamilyDB is not running"
  elif [ "$bad" -gt 0 ]; then
    mark="$S_BAD"; colour="$RED"
    if [ "$bad" -eq 1 ]; then headline="1 thing needs attention now"; else headline="$bad things need attention now"; fi
  elif [ "$warns" -gt 0 ]; then
    mark="$S_WARN"; colour="$YEL"; headline="Running, with $warns thing$([ "$warns" -eq 1 ] || echo s) to look at"
  else
    mark="$S_OK"; colour="$GRN"; headline="Running, and all is well"
  fi
  printf '\n%s%s %s%s%s\n\n' "$colour" "$mark" "$B" "$headline" "$OFF"
  log_line "== status: $headline"
  for i in "${!ROW_LABEL[@]}"; do
    if [ -z "${ROW_LABEL[i]}" ]; then
      printf '    %-12s %s%s%s\n' "" "$DIM" "${ROW_VALUE[i]}" "$OFF"
    else
      kv "${ROW_LABEL[i]}" "${ROW_VALUE[i]}" "${ROW_STATE[i]}"
    fi
  done

  if [ "${#ATTENTION[@]}" -gt 0 ]; then
    after "Needs attention"
    for i in "${!ATTENTION[@]}"; do
      WRAP_FIRST="  ${YEL}${S_WARN}${OFF} " wrap "    " "" "${ATTENTION[i]}"
      INDENT="      " show_commands <<<"${ATTENTION_FIX[i]}"
    done
  fi
  printf '\n%sFor the full check, with every finding and its fix:%s ' "$DIM" "$OFF"
  _style_command "$CYN" "$DIM" "$OFF" "${0} check"
  printf '\n'
}

cmd_check() {
  hint "$S_OK fine   $S_WARN worth a look   $S_BAD must be fixed   $S_DOT skipped"
  printf '\n'
  _capture "Running the checks" familydb_cmd doctor
  show_doctor all "$_OUT"
  [ -n "$_OUT" ] || warn "The check printed nothing, so it may not have run. Run it by hand: cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} doctor"
  if [ "$DOCTOR_BAD" -gt 0 ]; then
    finish bad "$DOCTOR_BAD thing$([ "$DOCTOR_BAD" -eq 1 ] || echo s) must be fixed, $DOCTOR_WARN worth a look"
  elif [ "$DOCTOR_WARN" -gt 0 ]; then
    finish warn "Nothing is broken; $DOCTOR_WARN thing$([ "$DOCTOR_WARN" -eq 1 ] || echo s) worth a look"
  else
    finish ok "All $DOCTOR_FINE checks are fine"
  fi
  [ -z "$DOCTOR_VERDICT" ] || hint "$DOCTOR_VERDICT"
}

cmd_password() {
  if [ -n "$PASSWORD_FOR" ]; then
    familydb_cmd password "$PASSWORD_FOR"
  else
    familydb_cmd password
  fi
}

cmd_https() {
  as_root test -f "${TARGET}/.env" || die "there is no ${TARGET}/.env" "Run the installer first."
  if [ "$DOCKER_MODE" = 1 ]; then
    https_port_in_docker
    return 0
  fi
  local site port previous chosen
  site="${HTTPS_SITE#https://}"; site="${site#http://}"; site="${site%%/*}"; site="${site%:*}"
  [ -n "$site" ] || site="$(env_file_value WEB_DOMAIN)"
  [ -n "$site" ] || site="$(this_address)"
  [ -n "$site" ] || die "could not tell this server's address" "Give it: ${0} https your.domain"
  port="$(env_file_value WEB_PORT)"; port="${port:-8080}"
  # The port the page is on stays where it was unless --port moves it.
  previous="$(env_file_value WEB_PUBLIC_PORT)"; previous="${previous:-443}"
  chosen="$(choose_public_port "${HTTPS_PORT:-$previous}" "$port")" \
    || die "that port will not do" "Give --port a number from 1024 to 65535, or random, or 443."
  PUBLIC_PORT="$chosen"
  kv "Address" "$site"
  kv "Page port" "$chosen$([ "$chosen" != "$previous" ] && echo " (was ${previous})")"

  have caddy || plan_item "Install Caddy" \
    "it holds the certificate and passes the page on to FamilyDB; it comes from this system's packages"
  if have ufw && as_root ufw status 2>/dev/null | grep -q "^Status: active"; then
    plan_item "Open ports 80 and ${chosen} in this machine's firewall (ufw)" \
      "${chosen} is the page; 80 is where the certificate authority checks that this machine is the one the address leads to"
  fi
  plan_item "Write ${CADDYFILE} and reload Caddy" \
    "it serves $(public_url "$site") and passes the page on to FamilyDB at 127.0.0.1:${port}"
  plan_item "Point FamilyDB at Caddy and restart it" \
    "the page has to believe Caddy about who is visiting, and listen for nobody but Caddy (.env: WEB_DOMAIN, WEB_TRUST_PROXY, WEB_HOST, WEB_PUBLIC_PORT)"
  plan_untouched "your data and settings, and any other site Caddy serves (a Caddyfile that serves something else is left as it is)"
  show_plan "What this will do"

  phase "Setting up Caddy"
  setup_https "$site" "$port" || die "the page could not be put on HTTPS" "What went wrong is above."
  phase "Pointing FamilyDB at it"
  env_file_set WEB_DOMAIN "$site"
  env_file_set WEB_TRUST_PROXY true
  env_file_set WEB_HOST 127.0.0.1
  env_file_set WEB_PUBLIC_PORT "$PUBLIC_PORT"
  ok "Wrote the page's address and port into ${TARGET}/.env"
  close_old_web_ports "$previous"
  if service_installed; then
    step "Restarting FamilyDB so the page knows it is behind HTTPS" as_root systemctl restart familydb
  fi
  if [ "$HTTPS_BLOCKED" = 1 ]; then
    finish warn "The page is on HTTPS, but nothing outside seems able to reach it yet"
  else
    finish ok "The page is on HTTPS"
  fi
  say "The page: ${B}$(public_url "$site")${OFF}"
  case "$HTTPS_KIND" in
    public) kv "Certificate" "a real one: no browser will warn" ;;
    internal) kv "Certificate" "Caddy's own, so the browser warns once" ;;
  esac
  if [ "$PUBLIC_PORT" != "$previous" ]; then
    hint "It moved from port ${previous}: open it at the address above from now on. A bookmark to the old address finds nothing."
  fi
  say_how_to_open
}

# With Docker, Caddy is the compose file's tls profile, set up by the installer from .env; what is
# left to move is the port of this machine it is published on.
https_port_in_docker() {
  local site port previous chosen
  site="$(env_file_value WEB_DOMAIN)"
  if [ -z "$site" ] || [ -z "$HTTPS_PORT" ]; then
    die "with Docker, this only moves the port of a page already on HTTPS" \
      "For HTTPS, set WEB_DOMAIN, WEB_TRUST_PROXY=true and COMPOSE_PROFILES=tls in ${TARGET}/.env, then: docker compose up -d" \
      "Then, to move it off 443: sudo ${0} https --port random"
  fi
  port="$(env_file_value WEB_PORT)"; port="${port:-8080}"
  previous="$(env_file_value WEB_PUBLIC_PORT)"; previous="${previous:-443}"
  chosen="$(choose_public_port "$HTTPS_PORT" "$port")" \
    || die "that port will not do" "Give --port a number from 1024 to 65535, or random, or 443."
  if [ "$chosen" != "$previous" ] && port_listening "$chosen"; then
    die "something on this machine already listens on port ${chosen}, so the page cannot" \
      "Nothing was changed. Choose another: sudo ${0} https --port random"
  fi
  PUBLIC_PORT="$chosen"
  if [ "$chosen" = "$previous" ]; then
    finish ok "The page is already served on port ${chosen}: nothing to do"
  else
    plan_item "Serve the page on port ${chosen} instead of ${previous}" \
      "WEB_PUBLIC_PORT in ${TARGET}/.env, then the containers are started again with it"
    show_plan "What this will do"
    phase "Moving the page"
    if [ "$DRY_RUN" = 0 ]; then
      env_file_set WEB_PUBLIC_PORT "$chosen"
      ok "WEB_PUBLIC_PORT is ${chosen} in ${TARGET}/.env"
    fi
    step "Starting the containers again" as_root docker compose --project-directory "$TARGET" up -d
    finish ok "The page is on port ${chosen}"
  fi
  say "The page: ${B}$(public_url "$site")${OFF}"
  if [ "$chosen" != "$previous" ]; then
    hint "It moved from port ${previous}: open it at the address above from now on. A bookmark to the old address finds nothing."
  fi
  say_how_to_open
}

cmd_port() {
  [ -n "$APP_PORT" ] || die "which port?" "Usage: ${0} port N, with N from 1025 to 65535, or random"
  as_root test -f "${TARGET}/.env" || die "there is no ${TARGET}/.env" "Run the installer first."
  local now served chosen followed=0 site host
  now="$(env_file_value WEB_PORT)"; now="${now:-8080}"
  served="$(env_file_value WEB_PUBLIC_PORT)"; served="${served:-443}"
  chosen="$(choose_app_port "$APP_PORT" "$served" "$now")" \
    || die "that port will not do" "Give it a number from 1025 to 65535, or random."
  if [ "$chosen" = "$now" ]; then
    finish ok "Nothing to do: FamilyDB already listens on port ${now}"
    return 0
  fi
  kv "Port now" "$now"
  kv "Port after" "$chosen"
  plan_item "Change WEB_PORT from ${now} to ${chosen} in ${TARGET}/.env" "FamilyDB reads it when it starts"
  if [ "$DOCKER_MODE" = 1 ]; then
    plan_item "Start the containers again" \
      "the compose file publishes the port, and Caddy passes the page on to it"
  else
    plan_item "Point Caddy at the new port" \
      "/etc/caddy/Caddyfile passes the page on to ${now}; it is changed and Caddy reloaded, and the old file comes back if Caddy will not load the change"
    plan_safe "If Caddy will not load the change, its old configuration is put back and nothing moves."
    if service_installed; then
      plan_item "Restart FamilyDB" "so that it listens on ${chosen}"
    fi
  fi
  plan_untouched "the address people open, when Caddy is in front: only the port behind it moves"
  show_plan "What this will do"
  if [ "$DRY_RUN" = 1 ]; then
    finish ok "Dry run"
    return 0
  fi
  phase "Changing the setting"
  env_file_set WEB_PORT "$chosen"
  ok "WEB_PORT is ${chosen} in ${TARGET}/.env"
  if [ "$DOCKER_MODE" = 1 ]; then
    phase "Starting the containers again"
    step "Starting the containers again on port ${chosen}" \
      as_root docker compose --project-directory "$TARGET" up -d
  else
    phase "Pointing Caddy at it"
    caddy_follows "$now" "$chosen" || followed=$?
    if [ "$followed" = 1 ]; then
      env_file_set WEB_PORT "$now"
      die "Caddy would not load the change, so nothing was moved" \
        "Its configuration is as it was. What it said: sudo journalctl -u caddy -n 30"
    fi
    [ "$followed" = 0 ] && ok "Caddy passes the page on to port ${chosen} now."
    if service_installed; then
      phase "Restarting FamilyDB"
      step "Restarting FamilyDB on port ${chosen}" as_root systemctl restart familydb
    else
      note "No service here to restart: start FamilyDB again yourself, and it listens on ${chosen}."
    fi
  fi
  site="$(env_file_value WEB_DOMAIN)"
  host="$(env_file_value WEB_HOST)"; host="${host:-127.0.0.1}"
  if [ -n "$site" ] && [ "$followed" = 2 ] && [ "$DOCKER_MODE" = 0 ]; then
    warn "No Caddyfile here passed the page on to port ${now}, so none was changed. Point whatever serves ${site} at 127.0.0.1:${chosen} instead."
  fi
  finish ok "FamilyDB now listens on port ${chosen}"
  if [ -n "$site" ]; then
    PUBLIC_PORT="$served"
    say "The page is still at ${B}$(public_url "$site")${OFF}: only the port behind Caddy moved."
  elif [ "$DOCKER_MODE" = 1 ] || [ "$host" = 127.0.0.1 ] || [ "$host" = localhost ] || [ "$host" = ::1 ]; then
    say "It is on this machine alone. From your own computer, open a tunnel to it:"
    cmdline "ssh -L ${chosen}:127.0.0.1:${chosen} ${SUDO_USER:-$(id -un)}@$(this_address)"
    say "and, while it is connected, open ${B}http://127.0.0.1:${chosen}/${OFF} on that computer."
  else
    say "The page: ${B}http://$(this_address):${chosen}/${OFF}. A bookmark to port ${now} finds nothing."
    after "If a firewall let port ${now} in"
    hint "Let ${chosen} in instead, and close ${now}:"
    cmdline "sudo ufw allow ${chosen}/tcp && sudo ufw delete allow ${now}/tcp"
  fi
}

cmd_backup() {
  phase "Taking the backup"
  take_backup "$BACKUP_DIR" "so today's state can be put back if something goes wrong"
  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  finish ok "Backup saved"
  kv "File" "$LAST_BACKUP"
  kv "Size" "$(du -h "$LAST_BACKUP" | cut -f1), readable only by its owner"
  after "Keep a copy somewhere that is not this machine"
  para "A backup on the same disk goes with the disk. Hand yourself a copy here, then fetch it:"
  cmdline "sudo install -m 600 -o ${SUDO_USER:-\$USER} ${LAST_BACKUP} ~/"
  cmdline "scp ${SUDO_USER:-you}@$(hostname -I 2>/dev/null | awk '{print $1}'):$(basename "$LAST_BACKUP") ." "run this one on your own computer"
}

cmd_restore() {
  [ -n "$RESTORE_FILE" ] || die "which backup?" "Usage: ${0} restore /path/to/familydb-....sqlite3"
  [ -f "$RESTORE_FILE" ] || die "no such file: ${RESTORE_FILE}" \
    "Look in ${BACKUP_DIR}:" "  ls -lh ${BACKUP_DIR}"
  # Validate before stopping or replacing anything. quick_check reports damage in its answer, not
  # as an error, so the answer itself must be 'ok'; reading members shows it is FamilyDB's. A
  # backup from a newer FamilyDB would run on code that does not know its tables: migrate skips
  # versions already applied and cannot go back, so it is refused here (exit 3, "have known").
  local validate target_owner checked=0 said have known
  validate='import sqlite3,sys
from pathlib import Path
from familydb.store import db
c=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+"?mode=ro",uri=True)
assert c.execute("pragma quick_check").fetchone()[0]=="ok"
c.execute("select id from members limit 1")
have=c.execute("select max(version) from schema_version").fetchone()[0] or 0
c.close()
known=max(v for v,_,_ in db.list_migrations())
if have>known:
    print(have,known)
    sys.exit(3)'
  target_owner="${SERVICE_USER}:${SERVICE_USER}"
  if [ "$DOCKER_MODE" = 1 ]; then
    RESTORE_FILE="$(cd -- "$(dirname -- "$RESTORE_FILE")" && pwd -P)/$(basename -- "$RESTORE_FILE")"
    said="$(as_root docker compose --project-directory "$TARGET" run --rm -T --no-deps \
      --user 0:0 -v "${RESTORE_FILE}:/restore.sqlite3:ro" bot python -c "$validate" /restore.sqlite3)" \
      || checked=$?
    target_owner="$(stat -c '%u:%g' "$DB" 2>/dev/null || echo 1000:1000)"
  else
    said="$(as_root "${TARGET}/.venv/bin/python" -c "$validate" "$RESTORE_FILE")" || checked=$?
  fi
  case "$checked" in
    0) ;;
    3)
      read -r have known <<<"$(printf '%s\n' "$said" | tail -1)"
      die "that backup is from a newer FamilyDB than this code: its database is at version ${have}, and this code knows up to ${known}" \
          "Nothing was stopped or replaced. Restoring it would run this code on tables it does not know." \
          "Upgrade the code first:  sudo ${0} upgrade" \
          "or use a backup taken by this version or an older one:  ls -lh ${BACKUP_DIR}" ;;
    *) die "backup validation failed; nothing was restored" ;;
  esac
  ok "That file is a sound FamilyDB backup: it passes SQLite's integrity check and is not from a newer FamilyDB."

  local taken taken_text
  taken="$(stat -c %Y "$RESTORE_FILE")"
  taken_text="$(date -d "@${taken}" '+%Y-%m-%d %H:%M' 2>/dev/null || stat -c '%y' "$RESTORE_FILE" | cut -d. -f1)"
  head2 "The backup, and what it replaces"
  kv "Restoring" "$RESTORE_FILE"
  kv "Taken" "${taken_text} ($(ago $(( $(date +%s) - taken ))))"
  kv "Size" "$(du -h "$RESTORE_FILE" | cut -f1)"
  if [ -f "$DB" ]; then
    kv "Replacing" "${DB} ($(du -h "$DB" | cut -f1), last written $(date -d "@$(stat -c %Y "$DB")" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '?'))"
  else
    kv "Replacing" "nothing: there is no database at ${DB} yet"
  fi

  if [ -f "$DB" ]; then
    plan_item "Back up the database being replaced" \
      "so this restore can be undone; the copy goes to ${BACKUP_DIR}"
  fi
  plan_item "Stop the bot" \
    "it must not write while the file is replaced; on a virtualenv install this can take up to 150 seconds if a model call is in progress"
  plan_item "Put the backup in place" \
    "copies it over ${DB}, clears the write-ahead files that belonged to the old database, and sets the owner and mode"
  plan_item "Bring the database up to date" \
    "applies any migrations this backup lacks"
  plan_item "Start the bot" \
    "it is down from step $([ -f "$DB" ] && echo 2 || echo 1) until this one"
  plan_note "Everything the bot has been told since ${taken_text} will be gone from the live database."
  [ ! -f "$DB" ] || plan_safe "The database being replaced is backed up first, so this can be undone."
  show_plan "What restoring does"
  approve "Replace the database with that backup?" || { say "Nothing was changed."; exit 0; }

  local safety=""
  if [ -f "$DB" ]; then
    phase "Backing up the database being replaced"
    take_backup "$BACKUP_DIR" "so this restore itself can be undone"
    safety="$LAST_BACKUP"
  fi
  phase "Stopping the bot"
  stop_bot
  phase "Putting the backup in place"
  step "Putting ${RESTORE_FILE} in place" as_root cp "$RESTORE_FILE" "$DB"
  # The write-ahead files belong to the database that was just replaced.
  try_step "Clearing the write-ahead files" as_root rm -f "${DB}-wal" "${DB}-shm"
  step "Restoring database ownership" as_root chown "$target_owner" "$DB"
  step "Protecting the restored database" as_root chmod 600 "$DB"
  phase "Bringing the database up to date"
  step "Bringing the schema up to date" familydb_cmd db migrate
  phase "Starting the bot"
  start_bot

  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  if [ "${BOT_STARTED:-}" = 0 ]; then
    finish bad "Restored, but FamilyDB did not start"
  else
    finish ok "Restored from ${taken_text}"
  fi
  kv "Restored" "$RESTORE_FILE"
  if [ -n "$safety" ]; then
    kv "Before" "$safety"
    after "To undo this restore"
    cmdline "sudo ${0} restore ${safety}" "puts back what was there before"
  fi
  hint "Settings changed on the web page and the saved keys come back with the database. The calendar key does not: Status shows what is connected."
}

# An upgrade that has moved the code writes this, and removes it once dependencies and migrations
# are done: what a rerun reads to tell a half-finished upgrade from an up-to-date one.
UPGRADE_PENDING="${LEDGER_DIR}/upgrade-pending"

pending_get() { # pending_get KEY - target, before or backup of an unfinished upgrade; empty if none
  as_root grep -s "^${1}=" "$UPGRADE_PENDING" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

pending_write() { # pending_write TARGET BEFORE BACKUP
  [ "$DRY_RUN" = 1 ] && return 0
  as_root mkdir -p "$LEDGER_DIR"
  as_root chmod 700 "$LEDGER_DIR"
  printf 'target=%s\nbefore=%s\nbackup=%s\n' "$1" "$2" "$3" | as_root tee "$UPGRADE_PENDING" >/dev/null
}

# The version the database is at, and the newest migration this checkout has; empty when unreadable.
database_version() {
  local python="${TARGET}/.venv/bin/python"
  [ -x "$python" ] || python="python3"
  as_root "$python" -c 'import sqlite3,sys; from pathlib import Path; c=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+"?mode=ro",uri=True); print(c.execute("select max(version) from schema_version").fetchone()[0] or 0)' "$DB" 2>/dev/null || true
}
newest_migration() {
  find "${TARGET}/src/familydb/store/migrations" -maxdepth 1 -name '[0-9][0-9][0-9][0-9]_*.sql' -printf '%f\n' 2>/dev/null \
    | sort | tail -1 | cut -c1-4 | sed 's/^0*//' || true
}

# Going back is the code, what it was installed with, and the database from before its
# migrations, in that order: the restore restarts the bot on the code checked out above it.
rollback_lines() { # rollback_lines LABEL BEFORE BACKUP - the commands, one a line
  local label="$1" before="$2" backup="$3"
  if [ -n "$before" ]; then
    printf '  sudo git -C %s checkout --quiet --detach %s     # %s\n' "$TARGET" "$before" "$label"
    if [ "$DOCKER_MODE" = 1 ]; then
      printf '  sudo docker compose --project-directory %s build\n' "$TARGET"
    else
      printf '  sudo uv sync --frozen --no-dev --project %s\n' "$TARGET"
    fi
  fi
  printf '  sudo %s restore %s\n' "$0" "$backup"
}

cmd_upgrade() {
  [ -d "${TARGET}/.git" ] || die "${TARGET} is not a git checkout, so there is nothing to pull" \
    "Upgrade by unpacking a new copy over it, keeping .env and data/."

  local current
  current="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)"
  kv "Now on" "$current"

  plan_item "Back up the database" \
    "a copy goes to ${BACKUP_DIR}, so a bad upgrade can be undone"
  plan_item "Fetch the newest version from the git remote" \
    "this is the code the bot runs; nothing about your configuration or data changes"
  plan_item "Stop the bot and install the new version" \
    "reinstalls the dependencies at their locked versions, because a new release may need a library version this machine does not have (Docker: rebuilds the image)"
  plan_item "Apply any new database migrations" \
    "they are applied in order and change the database's layout; some rewrite what is in it. The backup taken first covers that, and going back means restoring it"
  plan_item "Start the bot again" \
    "the new code only takes effect once the process restarts"
  plan_item "Check that it is well" \
    "the same check as ${0##*/} check; it shows what must be fixed and counts the rest"
  plan_note "FamilyDB is stopped from step 3 until step 5: usually a minute or two, longer on Docker, which rebuilds its image."
  plan_safe "A backup is taken first, and the commands to go back are printed before the new code goes in."
  plan_safe "If a step fails it stops and says how to finish or go back; running this again carries on from where it stopped."
  plan_untouched ".env, your keys, and everything the family has told it"
  show_plan "What upgrading does"
  approve "Upgrade now?" || { say "Nothing was changed."; exit 0; }

  phase "Backing up the database"
  take_backup "$BACKUP_DIR" "so a bad upgrade can be undone"
  local before upgrade_backup="$LAST_BACKUP" unfinished=""
  before="$(as_root git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo unknown)"

  phase "Fetching the newest version"
  # A private repository needs a credential here. bootstrap.sh leaves the deploy key wired up
  # when one was used, and deliberately does not write a token down, so say which case this is.
  # shellcheck disable=SC2034  # lib/common.sh names this in its failure report.
  FAILED_STEP="fetching the newest code"
  local -a fetch_from=(origin)
  local origin_url
  origin_url="$(as_root git -C "$TARGET" remote get-url origin 2>/dev/null || true)"
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    case "$origin_url" in
      https://github.com/*)
        # Used for this fetch only, as bootstrap did for the clone: never written down.
        fetch_from=("https://x-access-token:${GITHUB_TOKEN}@github.com/${origin_url#https://github.com/}"
                    "+refs/heads/*:refs/remotes/origin/*")
        note "Fetching over HTTPS with the token from the environment." ;;
      *) warn "GITHUB_TOKEN only helps with an https://github.com/... remote; this one is ${origin_url}" ;;
    esac
  fi
  _capture "Fetching the newest code from ${origin_url:-the git remote}" \
    as_root git -C "$TARGET" fetch --tags --quiet "${fetch_from[@]}"
  [ -z "$_OUT" ] || printf '%s\n' "$_OUT" >>"${LOG_FILE:-/dev/null}"
  if [ "$_STATUS" != 0 ]; then
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
        "  · with a token — give it again for this run; it is not written down:" \
        "      read -rs GITHUB_TOKEN && export GITHUB_TOKEN" \
        "      sudo --preserve-env=GITHUB_TOKEN bash ${0} upgrade" \
        "    (a token that has expired needs a new one; a deploy key never expires)" \
        "  · with a copy you made yourself — there is nothing to fetch from. Unpack the new" \
        "    version over ${TARGET} (.env and data/ are not in it, so they stay) and run:" \
        "      sudo bash ${TARGET}/scripts/install.sh" \
        "    docs/INSTALL.md, 'Day to day', has the steps." \
        "" \
        "Currently configured: ${sshcmd:-no core.sshCommand set}" \
        "docs/INSTALL.md, 'Other ways to get the code onto the server', covers all three."
  fi
  # shellcheck disable=SC2034  # cleared so a later failure does not name this step.
  FAILED_STEP=""
  ok "Fetched the newest code"
  local kind name target
  read -r kind name <<<"$(wanted_version "$TARGET")"
  case "$kind" in
    branch) target="origin/${name}"; note "The newest version is still being built, so this follows ${name}." ;;
    tag) target="$name" ;;
    *) die "there is nothing to upgrade to: the remote has no default branch and no release" ;;
  esac
  # An earlier upgrade that stopped part-way remembers what to go back to: that, not the state
  # this run found.
  if [ -n "$(pending_get before)" ]; then
    before="$(pending_get before)"
    upgrade_backup="$(pending_get backup)"
    current="$(as_root git -C "$TARGET" describe --tags --always "$before" 2>/dev/null || echo "$before")"
  fi
  if as_root git -C "$TARGET" merge-base --is-ancestor "$target" HEAD; then
    # On the code is not the same as upgraded: a stop after the checkout leaves the code here and
    # the dependencies, the migrations or the restart undone.
    local have newest
    have="$(database_version)"
    newest="$(newest_migration)"
    if [ -n "$(pending_get target)" ]; then
      unfinished="an earlier upgrade to $(pending_get target) stopped after moving the code; its dependencies, migrations or restart may not have run"
    elif [ -n "$have" ] && [ -n "$newest" ] && [ "$have" -lt "$newest" ]; then
      unfinished="the database is at migration ${have} and this code has up to ${newest}"
    fi
    if [ -z "$unfinished" ]; then
      finish ok "Already up to date with ${name}, and the database is migrated. Nothing to do."
      kv "Version" "$current"
      kv "Backup" "$upgrade_backup"
      return 0
    fi
    warn "The code is already on ${name}, but it is not upgraded: ${unfinished}."
    say "Finishing it now."
    # Nothing recorded the code it came from, so only the database can be put back.
    [ -n "$(pending_get before)" ] || before=""
  else
    # Only forward. A release tag older than what is installed would take the database back past
    # migrations it has already run; a branch that lacks what is here would lose it.
    moves_forward "$TARGET" "$target" \
      || die "${name} does not contain what is installed now (${current}), so moving to it would go backwards" \
             "Nothing was changed. To choose a version yourself: sudo git -C ${TARGET} checkout NAME"
    local arriving commits
    arriving="$(as_root git -C "$TARGET" describe --tags --always "$target" 2>/dev/null || echo "$name")"
    commits="$(as_root git -C "$TARGET" rev-list --count "HEAD..${target}" 2>/dev/null || true)"
    kv "Moving to" "${arriving}${commits:+, ${commits} new commit$([ "$commits" = 1 ] || echo s)}"
    hint "If anything goes wrong from here, these put it back (they are printed again then):"
    rollback_lines "$current" "$before" "$upgrade_backup" | show_commands
    pending_write "$name" "$before" "$upgrade_backup"
    step "Checking out ${name}" as_root git -C "$TARGET" checkout --quiet --detach "$target"
  fi

  # From here the code is the new one, so a failure is not "nothing was half-done": say what is,
  # and how to go back or finish. lib/common.sh prints both at the foot of every failure.
  local undo back
  undo="$(rollback_lines "$current" "$before" "$upgrade_backup")"
  back="To go back to ${current} instead, database and all:"
  [ -n "$before" ] || back="To put the database from before the upgrade back instead:"
  on_failure_hint "The upgrade stopped part-way: the code is on ${name}, and the steps after it (dependencies, migrations, restart) are not all done. The bot may be stopped."$'\n'"${back}"$'\n'"${undo}"
  again_hint "finish the upgrade: sudo bash ${0} upgrade"

  phase "Installing the new version"
  stop_bot
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Rebuilding the image" as_root docker compose --project-directory "$TARGET" build
  else
    retry 2 "Installing the dependencies" \
      as_root env PATH="$SYSTEM_PATH" uv sync --frozen --no-dev --project "$TARGET"
    try_step "Keeping the code owned by root" as_root chmod -R go-w "$TARGET"
  fi
  phase "Updating the database"
  step "Applying any new migrations" familydb_cmd db migrate
  [ "$DRY_RUN" = 1 ] || as_root rm -f "$UPGRADE_PENDING"
  on_failure_hint ""
  again_hint ""
  phase "Starting the bot"
  start_bot

  local now_on
  now_on="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)"
  if [ "$DRY_RUN" = 1 ]; then
    finish ok "Dry run"
    return 0
  fi
  phase "Checking that it is well"
  _capture "Running the checks" familydb_cmd doctor
  show_doctor failures "$_OUT"
  [ -n "$_OUT" ] || warn "The check printed nothing, so it may not have run. Run it yourself: sudo ${0} check"

  if [ "${BOT_STARTED:-}" = 0 ]; then
    finish bad "Upgraded to ${now_on}, but FamilyDB did not start"
  elif [ "$DOCTOR_BAD" -gt 0 ]; then
    finish warn "Upgraded to ${now_on}, but the check found $DOCTOR_BAD thing$([ "$DOCTOR_BAD" -eq 1 ] || echo s) to fix"
  else
    finish ok "Upgraded to ${now_on}"
  fi
  kv "Version" "${current} ${S_TO} ${now_on}"
  kv "Backup" "$upgrade_backup"
  if [ -n "$_OUT" ]; then
    local checks="${DOCTOR_FINE} fine, ${DOCTOR_WARN} worth a look, ${DOCTOR_BAD} to fix"
    if [ "$DOCTOR_BAD" -gt 0 ]; then kv "Check" "$checks" bad
    elif [ "$DOCTOR_WARN" -gt 0 ]; then kv "Check" "$checks" warn
    else kv "Check" "$checks" ok; fi
  fi
  recap
  if [ -n "$before" ]; then
    after "If something is wrong, go back to ${current}, database and all"
  else
    after "If something is wrong, the database from before the upgrade can be put back"
  fi
  rollback_lines "$current" "$before" "$upgrade_backup" | show_commands
  hint "Every finding, with its fix: sudo ${0} check"
}

cmd_logs() {
  if [ "$DOCKER_MODE" = 1 ]; then
    [ ! -t 2 ] || printf '%sFollowing the bot'"'"'s log. Press Ctrl-C to stop.%s\n' "$E_DIM" "$E_OFF" >&2
    as_root docker compose --project-directory "$TARGET" logs -f --tail "$LOG_LINES" bot
  elif service_installed; then
    [ ! -t 2 ] || printf '%sFollowing the bot'"'"'s log. Press Ctrl-C to stop.%s\n' "$E_DIM" "$E_OFF" >&2
    as_root journalctl -u familydb -n "$LOG_LINES" -f
  else
    die "there is no service and no container here, so there is no log to follow" \
        "If you run it by hand, the log is wherever you sent that command's output."
  fi
}

cmd_restart() {
  phase "Stopping the bot"
  stop_bot
  phase "Starting the bot"
  start_bot
  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  case "${BOT_STARTED:-}" in
    1) finish ok "FamilyDB restarted, and is running" ;;
    0) finish bad "FamilyDB did not come back up" ;;
    *) finish ok "Restarted" ;;
  esac
}

cmd_schedule_backups() {
  case "$KEEP_DAYS" in ''|*[!0-9]*) die "--keep-days must be a nonnegative integer" ;; esac
  case "${TARGET}${BACKUP_DIR}" in *$'\n'*|*%*) die "cron paths cannot contain newlines or percent signs" ;; esac
  local line command quoted target_q dir_q
  printf -v target_q '%q' "$TARGET"
  printf -v dir_q '%q' "$BACKUP_DIR"
  command="/bin/bash ${target_q}/scripts/maintain.sh backup --target ${target_q} --backup-dir ${dir_q} --yes && find ${dir_q} -maxdepth 1 -name 'familydb-*.sqlite3' -mtime +${KEEP_DAYS} -delete"
  printf -v quoted '%q' "$command"
  line="15 3 * * * /bin/bash -c ${quoted} # familydb-maintain-backup"
  kv "Folder" "$BACKUP_DIR"
  kv "Kept for" "${KEEP_DAYS} days"
  plan_item "Add a line to root's crontab" \
    "takes a backup at 03:15 every night and prunes old backups only after a successful backup; supports Docker and systemd"
  plan_item "Create ${BACKUP_DIR}" \
    "where those backups are written"
  plan_item "Remove the older schedule from ${SERVICE_USER}'s crontab, if it is there" \
    "the two lines earlier versions added; this one line replaces them"
  plan_untouched "any backup that already exists"
  show_plan "What scheduling backups does"
  hint "It runs this script rather than familydb itself, so a Docker install and a systemd one back up the same way, and a backup that fails is never followed by the prune."
  after "The crontab line"
  printf '  %s%s%s\n' "$DIM" "$line" "$OFF"
  printf '\n'
  approve "Add them to the crontab?" || { say "Nothing was changed."; exit 0; }

  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  phase "Scheduling"
  case "$BACKUP_DIR" in "${TARGET}"/*) ;; *) noting_new "$BACKUP_DIR" dir ;; esac
  as_root mkdir -p "$BACKUP_DIR"
  local existing
  # No crontab before this: removing FamilyDB then removes the crontab, not leaves an empty one.
  as_root crontab -u root -l >/dev/null 2>&1 || ledger crontab "root"
  ledger cron-line "familydb-maintain-backup"
  existing="$(as_root crontab -u root -l 2>/dev/null | grep -v 'familydb-maintain-backup' || true)"
  printf '%s\n%s\n' "$existing" "$line" \
    | sed '/^$/d' \
    | as_root crontab -u root - \
    || die "could not write root's crontab" \
           "Check that cron is installed: sudo apt-get install cron"
  ok "Added the nightly backup to root's crontab."
  # An older install has backup and prune lines in the service account's crontab, which would
  # keep pruning whether or not the backup worked.
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
  finish ok "A backup will be taken every night at 03:15"
  hint "Check it any time with:"
  cmdline "sudo crontab -u root -l"
  after "Copy them off the machine now and then"
  para "A backup on the same disk is only half a backup. This takes one and prints how to fetch it to your own computer:"
  cmdline "sudo ${0} backup"
}

case "$COMMAND" in
  status)           cmd_status ;;
  check)            intro "Check"; cmd_check ;;
  password)         intro "New password"; cmd_password ;;
  https)            intro "HTTPS"; cmd_https ;;
  port)             intro "Port"; cmd_port ;;
  backup)           intro "Backup"; cmd_backup ;;
  restore)          intro "Restore"; cmd_restore ;;
  upgrade)          intro "Upgrade"; cmd_upgrade ;;
  logs)             cmd_logs ;;
  restart)          intro "Restart"; cmd_restart ;;
  schedule-backups) intro "Nightly backups"; cmd_schedule_backups ;;
  -h|--help|help)   usage ;;
  *) usage >&2; die "unknown command: ${COMMAND}" ;;
esac
[ "$RECAPPED" = 1 ] || recap
