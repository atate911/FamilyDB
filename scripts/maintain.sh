#!/usr/bin/env bash
# Looking after a running FamilyDB: backups, restores, upgrades, HTTPS, logs and status.
# `scripts/maintain.sh --help` lists every command.
#
# Each command says what it is about to change before it changes it, and explains any failure in
# terms of what to do next. Nothing here deletes a backup except the nightly prune that
# schedule-backups sets up, which runs only after a new backup has been written.
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
  status               Is it running and does the page answer, where the page is, the
                       database and the disk, the backups, and whether there is a newer
                       version; then what, if anything, wants a look. Changes nothing, and
                       asks nothing of the network.
  check                The full check (familydb doctor), with every finding and its fix.
  password [NAME]      A new password for the web page, for one nobody remembers. Printed
                       once. Once people sign in as themselves it is a starting password for
                       NAME, or for the first admin: they sign in with it and choose their
                       own. Until then it is a new family password that everyone signs in with.
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
  backup               Take a backup now, using SQLite's online backup, safe while it runs.
  restore FILE         Stop the bot, put that backup in place, start it again. The database
                       being replaced is itself backed up first.
  upgrade              Move to the newest version, reinstall the dependencies, migrate and
                       restart. Says what the new version brings and asks before changing
                       anything, then takes a backup first. That is the default branch while
                       CHANGELOG.md says the next version is in progress, else the newest
                       release; it never moves to anything older than what is installed.
  logs [N]             Follow the log, starting with the last N lines (default 50).
  restart              Restart it, and say whether it came back.
  schedule-backups     Add a nightly backup to cron, and prune ones older than --keep-days.

Options
  --target DIR         Which install. Default: the checkout this script lives in.
  --user NAME          The account that owns the data. Default: familydb.
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
  sudo scripts/maintain.sh upgrade
  sudo scripts/maintain.sh https --port random
  sudo scripts/maintain.sh port 9090
USAGE
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

# ---------------------------------------------------------------- reading ----
# How status and the other commands lay out what they found: a heading per part, then one row a
# thing, the label in a column and a mark in front that says at a glance whether it is well.

ISSUES=()  # what `status` found wanting, said again together at the end

section() { printf '\n%s%s%s\n' "$B" "$1" "$OFF"; log_line "== $1"; }

row() { # row LABEL VALUE [good|bad|poor|""] - one aligned line; a bad or poor one is remembered
  local label="$1" value="$2" state="${3:-}" mark=" "
  case "$state" in
    good) mark="${GRN}✓${OFF}" ;;
    poor) mark="${YEL}!${OFF}"; ISSUES+=("${label}: ${value}") ;;
    bad)  mark="${RED}✗${OFF}"; ISSUES+=("${label}: ${value}") ;;
  esac
  printf '  %s %-12s %s\n' "$mark" "$label" "$value"
  log_line "${state:-info}: ${label}: ${value}"
}

more() { printf '    %-12s %s%s%s\n' "" "$DIM" "$1" "$OFF"; }  # a dim line under the row above

ago() { # ago SECONDS - "just now", "5 minutes", "3 hours", "2 days", for a person to read
  local s="${1:-0}"
  [ "$s" -ge 0 ] 2>/dev/null || s=0
  if   [ "$s" -lt 90 ];     then printf 'just now'; return 0
  elif [ "$s" -lt 5400 ];   then printf '%s minutes' $(( (s + 30) / 60 ))
  elif [ "$s" -lt 129600 ]; then printf '%s hours' $(( (s + 1800) / 3600 ))
  else                           printf '%s days' $(( (s + 43200) / 86400 ))
  fi
  printf ' ago'
}

human_size() { # human_size BYTES - "812 KB", "11 MB", "1.4 GB"
  awk -v b="${1:-0}" 'BEGIN {
    if (b < 1000000) printf "%d KB", (b + 999) / 1000
    else if (b < 1000000000) printf "%.0f MB", b / 1000000
    else printf "%.1f GB", b / 1000000000 }'
}

took() { # took SECONDS - "12s", "1m 40s"
  if [ "$1" -lt 60 ]; then printf '%ss' "$1"; else printf '%sm %ss' $(( $1 / 60 )) $(( $1 % 60 )); fi
}

app_port() { local p; p="$(env_file_value WEB_PORT)"; printf '%s' "${p:-8080}"; }

answering() { # answering - the page's own liveness check says ok, straight to FamilyDB's port
  have curl || return 2
  curl -fsS -m 3 "http://127.0.0.1:$(app_port)/healthz" 2>/dev/null | grep -q '^ok'
}

wait_until_answering() { # wait_until_answering SECONDS - sets WAITED to how long it took
  WAITED=0
  have curl || return 2
  while [ "$WAITED" -lt "$1" ]; do
    answering && return 0
    sleep 1
    WAITED=$((WAITED + 1))
  done
  return 1
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

start_bot() {
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Starting the containers" as_root docker compose --project-directory "$TARGET" up -d
    say_if_answering
  elif service_installed; then
    step "Starting the service" as_root systemctl start familydb
    sleep 3
    if service_active; then
      say_if_answering
    else
      warn "It did not come back up. The last 20 lines:"
      as_root journalctl -u familydb -n 20 --no-pager >&2 || true
      note ""
      note "What to try, in order:"
      note "  cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} doctor     # names what is wrong"
      note "  sudo systemctl status familydb"
      note "  sudo journalctl -u familydb -n 100 --no-pager"
    fi
  else
    note "No service to start. Run it in the foreground: cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} run"
  fi
}

# After a start: running is not the same as answering, so wait for the page to say so.
say_if_answering() {
  [ "$DRY_RUN" = 1 ] && return 0
  local status=0
  wait_until_answering 30 || status=$?
  case "$status" in
    0) ok "It came back up, and the page answers on port $(app_port) (after $((WAITED + 3))s)." ;;
    2) ok "It came back up." ; note "(curl is not installed, so whether the page answers was not checked.)" ;;
    *) warn "It is running, but the page did not answer on port $(app_port) within 30 seconds."
       note "It may still be starting. Look again in a minute:  ${0} status"
       note "If it stays that way, the log says why:             ${0} logs 100" ;;
  esac
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
    ok "Backup written ($(human_size "$(as_root stat -c %s "$dest" 2>/dev/null || echo 0)")), with SQLite's online backup, which is safe while the bot runs."
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
  status_version
  status_running
  status_page
  status_data
  status_backups
  say ""
  if [ ${#ISSUES[@]} -eq 0 ]; then
    ok "All looks well."
  else
    printf '%s!%s %s\n' "$YEL" "$OFF" \
      "$([ ${#ISSUES[@]} -eq 1 ] && echo "One thing wants a look:" || echo "${#ISSUES[@]} things want a look:")"
    local issue
    for issue in "${ISSUES[@]}"; do printf '    · %s\n' "$issue"; done
  fi
  say ""
  note "The full check, with every finding and its fix:  ${0} check"
}

status_version() {
  section "Version"
  if [ ! -d "${TARGET}/.git" ]; then
    row "Installed" "not a git checkout, so no version to name"
    return 0
  fi
  local version when
  version="$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)"
  when="$(as_root git -C "$TARGET" log -1 --format=%cd --date=format:'%-d %b %Y' 2>/dev/null || true)"
  row "Installed" "${version}${when:+, from ${when}}"
  # What is newer, from what the last fetch saw: status never goes to the network itself.
  local branch target behind fetched=""
  branch="$(as_root git -C "$TARGET" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -f "${TARGET}/.git/FETCH_HEAD" ]; then
    fetched="$(ago $(( $(date +%s) - $(stat -c %Y "${TARGET}/.git/FETCH_HEAD" 2>/dev/null || date +%s) )))"
  fi
  [ -n "$branch" ] || return 0
  target="$branch"
  if ! in_progress "$TARGET" "$branch"; then
    target="$(as_root git -C "$TARGET" tag -l 'v*' --sort=-v:refname 2>/dev/null | head -1 || true)"
    [ -n "$target" ] || target="$branch"
  fi
  behind="$(as_root git -C "$TARGET" rev-list --count --no-merges "HEAD..${target}" 2>/dev/null || echo 0)"
  if [ "$behind" -gt 0 ] 2>/dev/null; then
    row "Newer" "${behind} changes on ${target#origin/}, not installed yet" poor
    more "upgrade with:  sudo ${0} upgrade${fetched:+   (last looked ${fetched})}"
  else
    row "Newer" "nothing newer${fetched:+ as of the last look, ${fetched}}" good
  fi
}

status_running() {
  section "Running"
  if [ "$DOCKER_MODE" = 1 ]; then
    local lines line name state detail
    lines="$(as_root docker compose --project-directory "$TARGET" ps -a \
      --format '{{.Service}}|{{.State}}|{{.Status}}' 2>/dev/null || true)"
    if [ -z "$lines" ]; then
      row "Containers" "none running" bad
    else
      while IFS='|' read -r name state detail; do
        [ -n "$name" ] || continue
        if [ "$state" = running ]; then row "$name" "$detail" good; else row "$name" "$detail" bad; fi
      done <<<"$lines"
    fi
  elif service_installed; then
    local active enabled since restarts memory started
    active="$(systemctl is-active familydb 2>/dev/null || true)"
    enabled="$(systemctl is-enabled familydb 2>/dev/null || true)"
    if [ "$active" = active ]; then
      row "Service" "running, $([ "$enabled" = enabled ] && echo "starts at boot" || echo "${enabled:-not set} at boot")" \
        "$([ "$enabled" = enabled ] && echo good || echo poor)"
      started="$(systemctl show familydb -p ActiveEnterTimestamp --value 2>/dev/null || true)"
      since="$(date -d "$started" +%s 2>/dev/null || true)"
      [ -n "$since" ] && row "Up since" "$(date -d "@${since}" '+%a %-d %b %H:%M') ($(ago $(( $(date +%s) - since )) | sed 's/ ago//'))"
      memory="$(systemctl show familydb -p MemoryCurrent --value 2>/dev/null || true)"
      case "$memory" in ''|*[!0-9]*) ;; *) row "Memory" "$(human_size "$memory")" ;; esac
      restarts="$(systemctl show familydb -p NRestarts --value 2>/dev/null || true)"
      case "$restarts" in
        ''|*[!0-9]*|0) ;;
        *) row "Restarts" "systemd has restarted it ${restarts} times after it stopped by itself" poor
           more "the log says why:  ${0} logs 200" ;;
      esac
    else
      row "Service" "${active:-unknown}, not running" bad
      more "start it:  sudo ${0} restart      the log says why it stopped:  ${0} logs 100"
    fi
  else
    row "Service" "not installed; started by hand"
  fi
  local status=0
  answering || status=$?
  case "$status" in
    0) row "Answers" "the page says ok on port $(app_port)" good ;;
    2) row "Answers" "not checked: curl is not installed" ;;
    *) row "Answers" "nothing answered on port $(app_port)" bad ;;
  esac
}

status_page() {
  section "The page"
  if ! as_root test -f "${TARGET}/.env"; then
    row "Address" "no ${TARGET}/.env, so no address is set" poor
    return 0
  fi
  local site host port
  site="$(env_file_value WEB_DOMAIN)"
  host="$(env_file_value WEB_HOST)"; host="${host:-127.0.0.1}"
  port="$(app_port)"
  PUBLIC_PORT="$(env_file_value WEB_PUBLIC_PORT)"; PUBLIC_PORT="${PUBLIC_PORT:-443}"
  if [ -n "$site" ]; then
    row "Address" "$(public_url "$site")"
    local caddy=""
    if [ "$DOCKER_MODE" = 1 ]; then
      caddy="$(as_root docker compose --project-directory "$TARGET" ps --format '{{.Service}} {{.State}}' 2>/dev/null \
        | awk '$1 == "caddy" {print $2}' || true)"
      [ "$caddy" = running ] && caddy=active
    elif have systemctl; then
      caddy="$(systemctl is-active caddy 2>/dev/null || true)"
    fi
    if [ "$caddy" = active ]; then
      row "HTTPS" "Caddy on port ${PUBLIC_PORT}, passing the page on to ${port}" good
    else
      row "HTTPS" "Caddy is ${caddy:-not found}, so the address above finds nothing" bad
      more "put it back:  sudo ${0} https"
    fi
  elif [ "$host" = 127.0.0.1 ] || [ "$host" = localhost ] || [ "$host" = ::1 ]; then
    row "Address" "this machine only, on port ${port}: open it through an SSH tunnel"
    more "for a link anyone in the family can open:  sudo ${0} https"
  else
    row "Address" "http://$(this_address):${port}/, without HTTPS" poor
    more "passwords cross the network readable; put it on HTTPS:  sudo ${0} https"
  fi
}

status_data() {
  section "Data"
  # data/ is the service account's alone, so it is read as root.
  if as_root test -f "$DB"; then
    row "Database" "$(human_size "$(as_root stat -c %s "$DB" 2>/dev/null || echo 0)")"
    more "$DB"
  else
    row "Database" "none yet at ${DB}" poor
  fi
  local avail size used
  read -r avail size used <<<"$(df -Pk "$TARGET" 2>/dev/null | awk 'NR==2 {print $4, $2, $5}')"
  if [ -n "${avail:-}" ]; then
    local state=good
    { [ "$avail" -lt 1000000 ] || [ "${used%\%}" -ge 90 ]; } && state=poor
    [ "$avail" -lt 200000 ] && state=bad
    row "Disk" "$(human_size $((avail * 1024))) free of $(human_size $((size * 1024))) (${used} used)" "$state"
  fi
}

status_backups() {
  section "Backups"
  local found newest stamp count bytes
  found="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -printf '%T@ %s %p\n' 2>/dev/null \
    | sort -rn || true)"
  local scheduled=""
  if as_root crontab -u root -l 2>/dev/null | grep -q 'familydb-maintain-backup'; then
    scheduled="every night at 03:15, from root's crontab"
  elif as_root crontab -u "$SERVICE_USER" -l 2>/dev/null | grep -q 'familydb db backup'; then
    scheduled="every night, from ${SERVICE_USER}'s crontab (an older schedule: sudo ${0} schedule-backups replaces it)"
  fi
  if [ -z "$found" ]; then
    row "Newest" "none in ${BACKUP_DIR}" bad
    more "take one now:  sudo ${0} backup"
  else
    read -r stamp _ newest <<<"$(head -1 <<<"$found")"
    stamp="${stamp%.*}"
    local age=$(( $(date +%s) - stamp )) state=good
    [ "$age" -gt 172800 ] && state=poor  # two days: a nightly one has missed at least once
    row "Newest" "$(ago "$age"), $(date -d "@${stamp}" '+%a %-d %b %H:%M')" "$state"
    more "$newest"
    count="$(wc -l <<<"$found")"
    bytes="$(awk '{s += $2} END {print s + 0}' <<<"$found")"
    row "Kept" "${count} in ${BACKUP_DIR}, $(human_size "$bytes") together"
  fi
  if [ -n "$scheduled" ]; then
    row "Nightly" "$scheduled" good
  else
    row "Nightly" "not scheduled" poor
    more "schedule it:  sudo ${0} schedule-backups"
  fi
}

cmd_check() {
  head2 "Checking the install"
  familydb_cmd doctor || true
}

cmd_password() {
  head2 "A new password for the web page"
  if [ -n "$PASSWORD_FOR" ]; then
    familydb_cmd password "$PASSWORD_FOR"
  else
    familydb_cmd password
  fi
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

cmd_https() {
  head2 "HTTPS for the page"
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
  setup_https "$site" "$port" || die "the page could not be put on HTTPS" "What went wrong is above."
  # The page has to believe Caddy about who is visiting, and listen for nobody but Caddy.
  env_file_set WEB_DOMAIN "$site"
  env_file_set WEB_TRUST_PROXY true
  env_file_set WEB_HOST 127.0.0.1
  env_file_set WEB_PUBLIC_PORT "$PUBLIC_PORT"
  close_old_web_ports "$previous"
  if service_installed; then
    step "Restarting FamilyDB so the page knows it is behind HTTPS" as_root systemctl restart familydb
  fi
  say ""
  say "The page: ${B}$(public_url "$site")${OFF}"
  if [ "$PUBLIC_PORT" != "$previous" ]; then
    note "It moved from port ${previous}: open it at the address above from now on. A bookmark to"
    note "the old address finds nothing."
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
    ok "The page is already served on port ${chosen}. Nothing to do."
  else
    system_change "Serve the page on port ${chosen} instead of ${previous}" \
      "WEB_PUBLIC_PORT in ${TARGET}/.env, then the containers are started again with it"
    if [ "$DRY_RUN" = 0 ]; then
      env_file_set WEB_PUBLIC_PORT "$chosen"
      step "Starting the containers again" as_root docker compose --project-directory "$TARGET" up -d
    fi
  fi
  say ""
  say "The page: ${B}$(public_url "$site")${OFF}"
  if [ "$chosen" != "$previous" ]; then
    note "It moved from port ${previous}: open it at the address above from now on. A bookmark to"
    note "the old address finds nothing."
  fi
  say_how_to_open
}

# ------------------------------------------------------------------ port ----
cmd_port() {
  head2 "FamilyDB's own port"
  [ -n "$APP_PORT" ] || die "which port?" "Usage: ${0} port N, with N from 1025 to 65535, or random"
  as_root test -f "${TARGET}/.env" || die "there is no ${TARGET}/.env" "Run the installer first."
  local now served chosen followed=0 site host
  now="$(env_file_value WEB_PORT)"; now="${now:-8080}"
  served="$(env_file_value WEB_PUBLIC_PORT)"; served="${served:-443}"
  chosen="$(choose_app_port "$APP_PORT" "$served" "$now")" \
    || die "that port will not do" "Give it a number from 1025 to 65535, or random."
  if [ "$chosen" = "$now" ]; then
    ok "FamilyDB already listens on port ${now}. Nothing to do."
    return 0
  fi
  if [ "$DOCKER_MODE" = 1 ]; then
    system_change "Move FamilyDB from port ${now} to port ${chosen}" \
      "WEB_PORT in ${TARGET}/.env, which the compose file publishes and Caddy passes the page on to"
  else
    system_change "Move FamilyDB from port ${now} to port ${chosen}" \
      "WEB_PORT in ${TARGET}/.env, and Caddy's configuration where it passes the page on to ${now}"
  fi
  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] nothing was changed"
    return 0
  fi
  env_file_set WEB_PORT "$chosen"
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Starting the containers again on port ${chosen}" \
      as_root docker compose --project-directory "$TARGET" up -d
  else
    caddy_follows "$now" "$chosen" || followed=$?
    if [ "$followed" = 1 ]; then
      env_file_set WEB_PORT "$now"
      die "Caddy would not load the change, so nothing was moved" \
        "Its configuration is as it was. What it said: sudo journalctl -u caddy -n 30"
    fi
    [ "$followed" = 0 ] && ok "Caddy passes the page on to port ${chosen} now."
    if service_installed; then
      step "Restarting FamilyDB on port ${chosen}" as_root systemctl restart familydb
    else
      note "No service here to restart: start FamilyDB again yourself, and it listens on ${chosen}."
    fi
  fi
  say ""
  site="$(env_file_value WEB_DOMAIN)"
  host="$(env_file_value WEB_HOST)"; host="${host:-127.0.0.1}"
  if [ -n "$site" ]; then
    PUBLIC_PORT="$served"
    say "The page is still at ${B}$(public_url "$site")${OFF}: only the port behind Caddy moved."
    if [ "$followed" = 2 ] && [ "$DOCKER_MODE" = 0 ]; then
      warn "No Caddyfile here passed the page on to port ${now}, so none was changed."
      note "Point whatever serves ${site} at 127.0.0.1:${chosen} instead."
    fi
  elif [ "$DOCKER_MODE" = 1 ] || [ "$host" = 127.0.0.1 ] || [ "$host" = localhost ] || [ "$host" = ::1 ]; then
    say "It is on this machine alone. From your own computer, open a tunnel to it:"
    say "  ssh -L ${chosen}:127.0.0.1:${chosen} ${SUDO_USER:-$(id -un)}@$(this_address)"
    say "  and, while it is connected, open ${B}http://127.0.0.1:${chosen}/${OFF} on that computer."
  else
    say "The page: ${B}http://$(this_address):${chosen}/${OFF}. A bookmark to port ${now} finds nothing."
    note "If a firewall let port ${now} in, let ${chosen} in instead, and close ${now}:"
    note "  sudo ufw allow ${chosen}/tcp && sudo ufw delete allow ${now}/tcp"
  fi
}

# ---------------------------------------------------------------- backup ----
cmd_backup() {
  head2 "Taking a backup"
  take_backup "$BACKUP_DIR" "so today's state can be put back if something goes wrong"
  say ""
  say "Backup: ${B}${LAST_BACKUP}${OFF}"
  say "Copy it somewhere that is not this machine. A backup on the same disk is not a backup."
  say "It is readable by root only, so hand yourself a copy here, then fetch it:"
  say "  sudo install -m 600 -o ${SUDO_USER:-\$USER} ${LAST_BACKUP} ~/"
  say "  scp ${SUDO_USER:-you}@$(this_address):$(basename "$LAST_BACKUP") .    # on your own computer"
}

cmd_restore() {
  [ -n "$RESTORE_FILE" ] || die "which backup?" "Usage: ${0} restore /path/to/familydb-....sqlite3"
  [ -f "$RESTORE_FILE" ] || die "no such file: ${RESTORE_FILE}" \
    "Look in ${BACKUP_DIR}:" "  ls -lh ${BACKUP_DIR}"
  # Validate before stopping or replacing anything. quick_check reports damage in its answer, not
  # as an error, so the answer itself must be 'ok'; reading members shows it is FamilyDB's.
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

  local before
  before="$(as_root git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo unknown)"

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
  if ! as_root git -C "$TARGET" fetch --tags --quiet "${fetch_from[@]}" 2>>"${LOG_FILE:-/dev/null}"; then
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
        "    version over ${TARGET} (.env and data/ are not in it, so they stay) and run" \
        "    sudo bash ${TARGET}/scripts/install.sh; docs/INSTALL.md, 'Day to day', has the steps." \
        "" \
        "Currently configured: ${sshcmd:-no core.sshCommand set}" \
        "docs/INSTALL.md, 'Other ways to get the code onto the server', covers all three."
  fi
  # shellcheck disable=SC2034  # cleared so a later failure does not name this step.
  FAILED_STEP=""
  ok "Fetched the newest code, which changes nothing here by itself"
  local kind name target
  read -r kind name <<<"$(wanted_version "$TARGET")"
  case "$kind" in
    branch) target="origin/${name}"; note "The newest version is still being built, so this follows ${name}." ;;
    tag) target="$name" ;;
    *) die "there is nothing to upgrade to: the remote has no default branch and no release" ;;
  esac
  if as_root git -C "$TARGET" merge-base --is-ancestor "$target" HEAD; then
    ok "Already up to date with ${name}. Nothing to do."
    return 0
  fi
  # Only forward. A release tag older than what is installed would take the database back past
  # migrations it has already run; a branch that lacks what is here would lose it.
  moves_forward "$TARGET" "$target" \
    || die "${name} does not contain what is installed now (${current}), so moving to it would go backwards" \
           "Nothing was changed. To choose a version yourself: sudo git -C ${TARGET} checkout NAME"

  upgrade_preview "$target" "$name"
  plan_item "Take a backup of the database" \
    "so a bad upgrade can be undone, database and all"
  plan_item "Check out ${name} and reinstall the dependencies at their locked versions" \
    "this is the code the bot runs; a new version may need a library this machine lacks"
  plan_item "Apply any new database migrations" \
    "they are applied in order and never rewrite what is already there"
  plan_item "Restart the bot, and check the page answers" \
    "the new code only takes effect once the process restarts; it is down for a few seconds"
  plan_untouched ".env, your keys, and everything the family has told it"
  show_plan "What upgrading does"
  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] That is what it would do. Nothing was changed."
    return 0
  fi
  approve "Upgrade now?" || { say "Nothing was changed."; exit 0; }

  take_backup "$BACKUP_DIR" "so a bad upgrade can be undone"
  local upgrade_backup="$LAST_BACKUP"
  step "Checking out ${name}" as_root git -C "$TARGET" checkout --quiet --detach "$target"

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
  say "Now on ${B}$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo unknown)${OFF}, from ${current}."
  # Going back is the code, what it was installed with, and the database from before its
  # migrations, in that order: the restore restarts the bot on the code checked out above it.
  say ""
  say "If something is wrong, go back to what was installed (${current}), database and all:"
  say "  sudo git -C ${TARGET} checkout --quiet --detach ${before}"
  if [ "$DOCKER_MODE" = 1 ]; then
    say "  sudo docker compose --project-directory ${TARGET} build"
  else
    say "  sudo uv sync --frozen --no-dev --project ${TARGET}"
  fi
  say "  sudo ${0} restore ${upgrade_backup}"
  head2 "The check, on the new version"
  familydb_cmd doctor || true
}

# What an upgrade brings, said before anyone is asked: how many changes, the newest of them in
# their own words, whether the database changes, and whether the dependencies do.
upgrade_preview() { # upgrade_preview TARGET NAME
  local target="$1" name="$2" count subjects migrations deps shown=12
  count="$(as_root git -C "$TARGET" rev-list --count --no-merges "HEAD..${target}" 2>/dev/null || echo 0)"
  head2 "What ${name} brings"
  say "  ${count} changes since ${current}. The newest:"
  subjects="$(as_root git -C "$TARGET" log --no-merges --format='%s' "HEAD..${target}" 2>/dev/null || true)"
  printf '%s\n' "$subjects" | head -"$shown" | sed 's/^/    · /'
  [ "$count" -gt "$shown" ] 2>/dev/null && note "    … and $((count - shown)) more:  git -C ${TARGET} log --oneline HEAD..${target}"
  migrations="$(as_root git -C "$TARGET" diff --name-only --diff-filter=A "HEAD" "$target" \
    -- src/familydb/store/migrations/ 2>/dev/null | sed 's|.*/||; s|\.sql$||' || true)"
  if [ -z "$migrations" ]; then
    say "  The database is not changed."
  else
    local n first last
    n="$(wc -l <<<"$migrations")"; first="$(head -1 <<<"$migrations")"; last="$(tail -1 <<<"$migrations")"
    if [ "$n" = 1 ]; then
      say "  The database gains one migration, ${first}. The backup taken first is the way back."
    else
      say "  The database gains ${n} migrations, ${first} to ${last}. The backup taken first is the way back."
    fi
  fi
  deps="$(as_root git -C "$TARGET" diff --quiet HEAD "$target" -- uv.lock 2>/dev/null && echo same || echo moved)"
  if [ "$deps" = moved ]; then
    say "  Some libraries move to new versions, which takes a minute to install."
  else
    say "  The libraries stay as they are."
  fi
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
  case "$BACKUP_DIR" in "${TARGET}"/*) ;; *) noting_new "$BACKUP_DIR" dir ;; esac
  as_root mkdir -p "$BACKUP_DIR"
  local existing
  # Root having no crontab at all before this is worth knowing: then removing FamilyDB removes
  # the crontab too, rather than leaving an empty one behind.
  as_root crontab -u root -l >/dev/null 2>&1 || ledger crontab "root"
  ledger cron-line "familydb-maintain-backup"
  existing="$(as_root crontab -u root -l 2>/dev/null | grep -v 'familydb-maintain-backup' || true)"
  printf '%s\n%s\n' "$existing" "$line" \
    | sed '/^$/d' \
    | as_root crontab -u root - \
    || die "could not write root's crontab" \
           "Check that cron is installed: sudo apt-get install cron"
  # An install from before this schedule has a backup line and a prune line in the service
  # account's crontab. Left there, they would keep pruning whether or not the backup worked.
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
  say "A backup on the same disk is only half a backup. Copy them off the machine now and then:"
  say "  sudo ${0} backup      # takes one and prints how to fetch it to your own computer"
}

case "$COMMAND" in
  status)           cmd_status ;;
  check)            cmd_check ;;
  password)         cmd_password ;;
  https)            cmd_https ;;
  port)             cmd_port ;;
  backup)           cmd_backup ;;
  restore)          cmd_restore ;;
  upgrade)          cmd_upgrade ;;
  logs)             cmd_logs ;;
  restart)          cmd_restart ;;
  schedule-backups) cmd_schedule_backups ;;
  -h|--help|help)   usage ;;
  *) usage >&2; die "unknown command: ${COMMAND}" ;;
esac

# The foot of anything that changed the machine: how long it took, whether anything wanted a look
# on the way, and where the whole run is written down.
case "$COMMAND" in
  https|port|backup|restore|upgrade|restart|schedule-backups)
    [ "$DRY_RUN" = 1 ] && exit 0
    say ""
    if [ "$WARNINGS" -gt 0 ]; then
      note "Finished in $(took "$SECONDS"), with ${WARNINGS} warning$([ "$WARNINGS" = 1 ] || echo s) above.${LOG_FILE:+ Every step is in ${LOG_FILE}.}"
    else
      note "Finished in $(took "$SECONDS").${LOG_FILE:+ Every step is in ${LOG_FILE}.}"
    fi ;;
esac
