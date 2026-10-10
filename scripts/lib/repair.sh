#!/usr/bin/env bash
# The guided doctor: `maintain.sh doctor`. It answers "it is broken and I do not know why: find out,
# say so, and fix it". Source it, do not run it; maintain.sh names what it needs, and lib/doctor.sh
# and lib/rescue.sh have the looking and the larger remedies.
#
# Five things happen, in this order, and the person is asked only where only they can answer:
#   1. it looks at everything (the same sweep as `check`, plus the service's log when it is unwell);
#   2. it says what is wrong and why, from the root cause up, in plain words;
#   3. it shows what it is going to do about each thing, and what only the person can do;
#   4. on one Enter it does the safe steps, in the order a page comes up; what can lose data asks
#      for a typed yes at its own turn and is never answered by --yes;
#   5. it looks again, and says what it put right, what is still wrong and why, and what next.
# `check` only reads; this changes things, so it asks first, backs the database up before it touches
# it, and writes down everything it did in the transcript (/var/log/familydb-maintain.log).

PL_KIND=(); PL_FUNC=(); PL_TITLE=(); PL_WHY=(); PL_DO=()    # the plan: safe, net (downloads), risky or tidy
NEED_TEXT=(); NEED_CMD=()                                    # what only the person can do
DR_FLAGS=" "                                                 # what the log made plain
DR_LOG=""
BEFORE_NAMES=()                                              # the checks that were not fine at the start
DONE_TITLES=()                                               # the steps that were done

dr_flag() { DR_FLAGS="${DR_FLAGS}${1} "; }
dr_flagged() { case "$DR_FLAGS" in *" $1 "*) return 0 ;; esac; return 1; }

dr_detail() { # dr_detail NAME - what the check of that name said
  local i
  for i in "${!_DR_NAME[@]}"; do
    [ "${_DR_NAME[i]}" != "$1" ] || { printf '%s' "${_DR_DETAIL[i]}"; return 0; }
  done
}

pl_add() { # pl_add KIND FUNC TITLE WHY DO - a step, once however many findings call for it
  local f
  for f in "${PL_FUNC[@]:-}"; do [ "$f" != "$2" ] || return 0; done
  PL_KIND+=("$1"); PL_FUNC+=("$2"); PL_TITLE+=("$3"); PL_WHY+=("$4"); PL_DO+=("$5")
}

need() { # need TEXT [COMMAND] - something the person has to do
  local t
  for t in "${NEED_TEXT[@]:-}"; do [ "$t" != "$1" ] || return 0; done
  NEED_TEXT+=("$1"); NEED_CMD+=("${2:-}")
}

# --- looking ----------------------------------------------------------------------------------------

sweep() { # sweep - everything `check` looks at, left in the rows for doctor_show and the plan
  local before rows why by_hand
  # shellcheck disable=SC2034  # read by lib/doctor.sh
  DC_ONLINE="$CHECK_ONLINE"
  doctor_begin
  dc_all
  local -a asked=(doctor)
  [ "$CHECK_ONLINE" != 1 ] || asked+=(--online)
  _capture "Asking the program" familydb_cmd "${asked[@]}"
  before=$((DOCTOR_FINE + DOCTOR_WARN + DOCTOR_BAD + DOCTOR_SKIP))
  doctor_section "Program"
  doctor_feed "$_OUT"
  rows=$((DOCTOR_FINE + DOCTOR_WARN + DOCTOR_BAD + DOCTOR_SKIP))
  if [ "$rows" = "$before" ]; then
    why="$(printf '%s\n' "$_OUT" | grep -A2 -i 'validation error' | sed '/^--$/d' | tr '\n' ' ' | cut -c1-220 || true)"
    [ -n "$why" ] || why="$(dc_last "$_OUT")"
    by_hand="cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} doctor"
    [ "$DOCKER_MODE" = 0 ] || by_hand="sudo docker compose --project-directory ${TARGET} run --rm bot familydb doctor"
    doctor_section "Program"
    doctor_row bad "its own check" "it printed no report${why:+: ${why}}" "Run it by hand to see all of it: ${by_hand}"
  fi
}

dr_read_log() { # what the service's log says when it is not well: the cause is often named there
  local text="" unwell=0
  rs_any_bad service restarts "last exit" page "sign-in page" listening "scheduled jobs" && unwell=1
  [ "$unwell" = 1 ] || return 0
  if [ "$DOCKER_MODE" = 1 ]; then
    text="$(as_root docker compose --project-directory "$TARGET" logs --tail 80 bot 2>&1 || true)"
  elif service_installed && have journalctl; then
    text="$(as_root journalctl -u familydb -n 80 --no-pager -o cat 2>/dev/null || true)"
  fi
  DR_LOG="$text"
  [ -n "$text" ] || return 0
  case "$text" in *"No module named"*|*ModuleNotFoundError*) dr_flag runtime ;; esac
  case "$text" in *"readonly database"*|*"unable to open database file"*|*"Permission denied"*) dr_flag ownership ;; esac
  case "$text" in *"Address already in use"*|*"Errno 98"*) dr_flag port ;; esac
  case "$text" in *"validation error for Settings"*|*ValidationError*) dr_flag settings ;; esac
  case "$text" in *"no such table"*|*"no such column"*) dr_flag migrate ;; esac
  case "$text" in *"database disk image is malformed"*|*"file is not a database"*) dr_flag database ;; esac
  case "$text" in *MemoryError*|*"Cannot allocate memory"*) dr_flag memory ;; esac
  return 0
}

dr_evidence() { # the line of the log that names the trouble
  printf '%s\n' "$DR_LOG" | grep -E 'Error|error|ERROR|Exception|Traceback' | tail -1 | cut -c1-150 || true
}

# --- what the doctor can do -------------------------------------------------------------------------
# Each of these is one step. They run as root, change one thing, and say nothing when they work.

fix_account() {
  as_root useradd --system --home-dir "$TARGET" --shell /usr/sbin/nologin --user-group "$SERVICE_USER"
  noting_user "$SERVICE_USER"
  record_service_user "$SERVICE_USER"
}

fix_ownership() {
  local data owner="${SERVICE_USER}:${SERVICE_USER}"
  data="$(dirname "$DC_DB")"
  dc_data_dir_ok "$data" || { printf 'Refusing to change who owns %s: it does not look like FamilyDB'"'"'s data folder.\n' "$data" >&2; return 1; }
  [ "$DOCKER_MODE" = 0 ] || owner="1000:1000"
  as_root mkdir -p "$data"
  as_root chown -R "$owner" "$data"
  as_root chmod 700 "$data"
  as_root find "$data" -maxdepth 1 -type f -exec chmod 600 {} +
  if as_root test -f "${TARGET}/.env"; then
    [ "$DOCKER_MODE" = 1 ] || as_root chown "$owner" "${TARGET}/.env"
    as_root chmod 600 "${TARGET}/.env"
  fi
}

fix_modes() {
  as_root test ! -f "${TARGET}/.env" || as_root chmod 600 "${TARGET}/.env"
  if dc_data_dir_ok "$(dirname "$DC_DB")"; then
    as_root find "$(dirname "$DC_DB")" -maxdepth 1 -type f -exec chmod 600 {} +
  fi
  as_root chmod -R go-w "$TARGET"
}

fix_safe_directory() { as_root git config --global --add safe.directory "$TARGET"; }

fix_files() { # put back what git tracks and is gone; what was changed on purpose is left alone
  as_root sh -c 'git -C "$1" ls-files --deleted -z | xargs -0 -r git -C "$1" checkout --' sh "$TARGET"
}

fix_env_create() {
  as_root test ! -e "${TARGET}/.env" || return 0
  as_root cp "${TARGET}/.env.example" "${TARGET}/.env"
  [ "$DOCKER_MODE" = 1 ] || as_root chown "${SERVICE_USER}:${SERVICE_USER}" "${TARGET}/.env"
  as_root chmod 600 "${TARGET}/.env"
}

fix_env_text() { # a byte-order mark and Windows line ends, with the file kept beside as it was
  local saved
  saved="${TARGET}/.env.before-doctor-$(date +%Y%m%d%H%M%S)"
  as_root cp -p "${TARGET}/.env" "$saved"
  as_root chmod 600 "$saved"
  as_root env LC_ALL=C sed -i -e '1s/^\xEF\xBB\xBF//' -e 's/\r$//' "${TARGET}/.env"
}

fix_uv() {
  as_root sh -c 'curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh'
}

fix_runtime() {
  if [ "$DOCKER_MODE" = 1 ]; then
    as_root docker compose --project-directory "$TARGET" build
    return
  fi
  [ -x "${TARGET}/.venv/bin/python" ] && as_root "${TARGET}/.venv/bin/python" -c 'import sys' 2>/dev/null \
    || as_root rm -rf "${TARGET}/.venv"
  uv_sync "$TARGET" || { sleep 3; uv_sync "$TARGET"; }
  as_root chmod -R go-w "$TARGET"
}

fix_migrate() {
  BACKUP_QUIET=1 take_backup "$BACKUP_DIR"
  familydb_cmd db migrate
}

fix_unit() { # the service file as the installer writes it, the old one kept beside it
  local tmp
  tmp="$(mktemp)"
  render_unit "$TARGET" "$SERVICE_USER" >"$tmp" && [ -s "$tmp" ] || { rm -f "$tmp"; printf 'There is no %s/deploy/familydb.service to write it from.\n' "$TARGET" >&2; return 1; }
  [ ! -f "$SERVICE_UNIT" ] || as_root cp -p "$SERVICE_UNIT" "${SERVICE_UNIT}.before-doctor"
  as_root install -m 644 "$tmp" "$SERVICE_UNIT"
  rm -f "$tmp"
  as_root systemctl daemon-reload
  as_root systemctl enable familydb >/dev/null 2>&1 || true
}

fix_reload() { as_root systemctl daemon-reload; }
fix_reset_failed() { as_root systemctl reset-failed familydb; }
fix_enable() { as_root systemctl enable familydb; }
fix_docker_start() { as_root systemctl start docker; }
fix_caddy() { as_root caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null && as_root systemctl restart caddy; }
fix_clock() { as_root timedatectl set-ntp true; }

fix_caddy_follows() { # Caddy passes the page to the port FamilyDB is on
  local old
  old="$(grep -oE 'reverse_proxy[[:space:]]+127\.0\.0\.1:[0-9]+' "$CADDYFILE" | head -1 | sed 's/.*://')"
  caddy_follows "$old" "$DC_PORT"
}

fix_firewall() {
  local port
  port="$(env_file_value WEB_PUBLIC_PORT)"; port="${port:-443}"
  as_root ufw allow 80/tcp >/dev/null
  as_root ufw allow "${port}/tcp" >/dev/null
}

# These three talk to the person, so they run in the open and not under a step's line.
fix_database() { rescue_database; }
fix_space() { rescue_space; }
fix_backups() { BACKUP_QUIET=1 take_backup "$BACKUP_DIR"; cmd_schedule_backups; }

fix_restart() { # the last step: start it, and wait to see whether the page answers
  STEP_QUIET=1 stop_bot
  STEP_QUIET=1 QUIET_START=1 start_bot
}

# --- deciding what to do ----------------------------------------------------------------------------
# In the order a page comes up, so that each step can rely on the ones before it. The words are for a
# person who does not know what a unit file is.

dr_plan() {
  local detail
  # 1. who runs it, and where its files are
  if [ "$DOCKER_MODE" = 0 ] && rs_has bad "service account"; then
    pl_add safe fix_account "Create the ${SERVICE_USER} account" \
      "The service is set to run as ${SERVICE_USER}, and no such account exists, so it cannot start at all." \
      "Create ${SERVICE_USER} as a system account that cannot sign in."
  fi
  if rs_has warn uv; then
    pl_add net fix_uv "Install uv, the program that installs the packages" \
      "uv is not installed, so the packages cannot be rebuilt or upgraded." \
      "Download uv's installer from astral.sh and run it (it puts uv in /usr/local/bin)."
  fi
  if rs_any_bad interpreter packages program image || dr_flagged runtime; then
    if [ "$DOCKER_MODE" = 1 ]; then
      pl_add net fix_runtime "Build the image again" \
        "The image the container runs is missing or cannot load, so the container cannot start." \
        "Run docker compose build; nothing in data/ is touched."
    else
      pl_add net fix_runtime "Rebuild the Python environment" \
        "The program's Python environment is gone or incomplete, so it fails before it can do anything." \
        "Install the exact packages in uv.lock again, downloading what is needed; nothing in data/ is touched."
    fi
  fi
  if [ -d "${TARGET}/.git" ]; then
    case "$(dr_detail checkout)" in
      *"dubious ownership"*)
        pl_add safe fix_safe_directory "Tell git this folder is safe to read" \
          "git refuses to work in a folder owned by another user, so upgrades and rollbacks fail." \
          "Run: git config --global --add safe.directory ${TARGET}." ;;
    esac
    if rs_has bad "missing files" || rs_has bad "program files"; then
      pl_add safe fix_files "Put back the missing program files" \
        "Files the program is made of are gone ($(dr_detail "missing files")), so pages cannot be drawn." \
        "Ask git for each file that is gone; files you changed on purpose are left alone."
    fi
  elif rs_has bad "program files"; then
    need "Files the program is made of are missing and this is not a git checkout, so they cannot be put back." \
      "Unpack a fresh copy of FamilyDB over ${TARGET}: .env and data/ are not in it, so they stay."
  fi
  # 2. its settings
  if [ "$DOCKER_MODE" = 0 ] && rs_has bad ".env"; then
    case "$(dr_detail .env)" in
      "missing"*) pl_add safe fix_env_create "Start a new .env from the example" \
                    "There is no .env, and the service will not start without its settings file." \
                    "Copy .env.example to .env, private to ${SERVICE_USER}. You will need to enter your keys and password again." ;;
    esac
  fi
  detail="$(dr_detail ".env syntax")"
  case "$detail" in
    *"byte-order mark"*|*"Windows way"*)
      pl_add safe fix_env_text "Clean .env of a byte-order mark and Windows line ends" \
        ".env has characters that hide the first option's name or stick to every value." \
        "Remove them; the file as it was is kept beside it." ;;
  esac
  case "$detail" in
    *"not NAME=value"*|*"unclosed quote"*|*"spaces before"*)
      need "${TARGET}/.env has lines FamilyDB cannot read: ${detail}" "sudoedit ${TARGET}/.env" ;;
  esac
  rs_has warn "repeated options" && need "An option is set twice in .env, and the last one wins: $(dr_detail "repeated options")" "sudoedit ${TARGET}/.env"
  rs_has bad "web port" && need "$(dr_detail "web port")" "sudo ${0} port 8080"
  rs_has bad "public port" && need "$(dr_detail "public port")" "sudo ${0} https --port 443"
  rs_has bad "web page" && need "$(dr_detail "web page")" "sudoedit ${TARGET}/.env"
  rs_has warn "web page" && need "The page is switched off in .env, so there is nothing to open." "sudo ${0} rescue locked-out"
  dr_flagged settings && need "The program refuses a setting it was given: $(dr_evidence)" "sudo ${0} rescue wont-start   # it can forget a setting saved on the page"
  # 3. the files' owners and modes
  local own=0
  rs_has bad "data folder" && own=1
  rs_has bad "journal files" && own=1
  if rs_has bad "database file"; then case "$(dr_detail "database file")" in "owned by"*) own=1 ;; esac; fi
  if rs_has bad ".env"; then case "$(dr_detail .env)" in "owned by"*) own=1 ;; esac; fi
  dr_flagged ownership && own=1
  if [ "$own" = 1 ]; then
    pl_add safe fix_ownership "Give ${SERVICE_USER} its files back" \
      "Some of its files belong to someone else (a command run as root does that), and it cannot write to them: that is the \"attempt to write a readonly database\" error." \
      "Hand data/ and .env to ${SERVICE_USER}, mode private."
  fi
  if rs_has warn ".env" || rs_has warn "database file" || rs_has warn "install folder"; then
    pl_add safe fix_modes "Make the secrets private again" \
      "Files that hold your keys, or the code itself, can be read or changed by other users on this machine." \
      "Set .env and the database to owner-only, and take write access to the code away from everyone else."
  fi
  # 4. the database
  local lost=0
  if rs_has bad "database file"; then case "$(dr_detail "database file")" in "none at"*) lost=1 ;; esac; fi
  if rs_has bad integrity || dr_flagged database || [ "$lost" = 1 ]; then
    pl_add risky fix_database "Bring the database back from a backup" \
      "The database file is missing or SQLite cannot read it ($(dr_detail integrity | cut -c1-80)), so nothing can be saved or answered." \
      "Test the backups, keep the damaged file aside, and restore the one you pick. This loses what was saved after that backup, so it asks you."
  fi
  if rs_has bad schema || dr_flagged migrate; then
    pl_add safe fix_migrate "Bring the database up to date" \
      "The database is behind the code, so the program stops at start." \
      "Take a backup, then apply the migrations it is missing."
  fi
  # 5. the service
  if [ "$DOCKER_MODE" = 1 ]; then
    rs_has bad docker && case "$(dr_detail docker)" in *"does not answer"*)
      pl_add safe fix_docker_start "Start Docker" "The Docker daemon is not running, so no container can run." "systemctl start docker." ;;
    esac
  elif service_installed; then
    rs_has bad "unit file" && pl_add safe fix_unit "Write the service file again" \
      "The service file points at something that is gone, or its sandbox leaves the database read-only ($(dr_detail "unit file" | cut -c1-90))." \
      "Write it as the installer would, with this install's paths; the old one is kept beside it."
    rs_has warn "unit loaded" && pl_add safe fix_reload "Make systemd read the changed service file" \
      "The file changed on disk but systemd is still running the old one." "systemctl daemon-reload."
    case "$(dr_detail "last exit")" in
      *"too many failed starts"*) pl_add safe fix_reset_failed "Let systemd try to start it again" \
        "systemd gave up after too many failed starts and will not try again by itself." "systemctl reset-failed familydb." ;;
    esac
    case "$(dr_detail service)" in
      *"at boot"*) rs_has warn service && pl_add safe fix_enable "Make it start with the machine" \
        "It is not enabled, so a reboot would leave it stopped." "systemctl enable familydb." ;;
    esac
    rs_has bad "double start" && need "FamilyDB is running twice, as a service and in Docker: $(dr_detail "double start" | cut -c1-120)" \
      "sudo docker compose --project-directory ${TARGET} down   # or: sudo systemctl disable --now familydb"
  fi
  # 6. in front of the page
  if rs_has bad caddy; then
    pl_add safe fix_caddy "Restart Caddy, which serves the page over HTTPS" \
      "Caddy is not running, so nobody can open the page from outside." "Check its file with caddy validate, then restart it."
  fi
  if rs_has bad caddyfile; then
    case "$(dr_detail caddyfile)" in
      *"bad gateway"*) pl_add safe fix_caddy_follows "Point Caddy at the port FamilyDB is on" \
        "Caddy passes the page to a port FamilyDB is not on, so every visitor gets a bad gateway." \
        "Change the one line in the Caddyfile and reload it; it is put back if Caddy will not load it." ;;
      *) need "Caddy cannot read its Caddyfile: $(dr_detail caddyfile | cut -c1-120)" "sudo ${0} https   # writes it again" ;;
    esac
  fi
  rs_has warn firewall && pl_add safe fix_firewall "Open the ports the page needs in the firewall" \
    "ufw is on and does not let ports 80 and the page's own through, so the address cannot open from outside." \
    "ufw allow 80 and the public port."
  rs_has bad dns && need "$(dr_detail dns)" "# at your registrar: an A record for the name pointing at this server"
  rs_has warn dns && need "$(dr_detail dns)" "# at your registrar: point the A record at this server"
  rs_has bad certificate && need "There is no valid certificate: $(dr_detail certificate | cut -c1-120)" "sudo journalctl -u caddy -n 30 --no-pager"
  case "$(dr_detail listening)" in
    *"is held by"*) need "$(dr_detail listening | cut -c1-140)" "sudo ${0} port random   # moves FamilyDB to a free port" ;;
  esac
  dr_flagged port && need "The port is taken by something else." "sudo ${0} port random"
  # 7. the host
  if rs_any_bad "disk space" inodes; then
    pl_add risky fix_space "Free disk space" \
      "The disk is (nearly) full, and a full disk stops every write, messages included." \
      "Show what can be freed and free the safe things; it asks before it deletes any backup."
  fi
  rs_has warn clock && pl_add safe fix_clock "Turn on time synchronisation" \
    "The clock is not synchronised; certificates, reminders and the digest depend on it." "timedatectl set-ntp true."
  rs_has bad "file system" && need "The disk went read-only, which is what the kernel does after a disk error." "sudo dmesg | tail -20   # then: sudo mount -o remount,rw /  or reboot"
  dr_flagged memory && need "The machine ran out of memory." "sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
  # 8. things only the person can do
  rs_has bad "deploy key" && need "$(dr_detail "deploy key")" "# see docs/INSTALL.md, 'Other ways to get the code onto the server'"
  rs_has warn "deploy key" && need "$(dr_detail "deploy key")" "# see docs/INSTALL.md, 'Other ways to get the code onto the server'"
  rs_has warn upgrade && need "An upgrade stopped part-way: the code moved, but its packages, migrations or the restart may not have run." \
    "sudo ${0} upgrade   # finishes it; or: sudo ${0} rescue rollback"
  rs_has bad "git history" && need "git found damaged history: $(dr_detail "git history" | cut -c1-100)" "sudo git -C ${TARGET} fetch --tags origin"
  rs_has bad family && need "Nobody is on the family list yet." "# open the page: its setup walks you through it"
  rs_has bad "model key" && need "There is no key for any model company, so nothing can answer." "# open the page: Settings, AI model"
  # 9. then start it and look
  local restart=0 f
  for f in "${PL_FUNC[@]:-}"; do
    case "$f" in ''|fix_uv|fix_space|fix_clock|fix_firewall|fix_caddy|fix_caddy_follows|fix_backups) ;; *) restart=1 ;; esac
  done
  rs_any_bad service page listening "scheduled jobs" "sign-in page" && restart=1
  # Started by hand, there is no service to restart: it is said at the end instead.
  [ "$DOCKER_MODE" = 1 ] || service_installed || restart=0
  if [ "$restart" = 1 ]; then
    pl_add safe fix_restart "Start FamilyDB and check the page answers" \
      "Whatever was wrong, it has to be started again for the repairs to count." \
      "Restart it, and wait up to 30 seconds for the page."
  fi
  if rs_has warn "backup schedule" || rs_has warn "backup files"; then
    pl_add tidy fix_backups "Set up the nightly backup" \
      "There is no recent backup, so a bad day could not be undone." "Add the nightly backup to cron, and take one now."
  fi
}

# --- saying it --------------------------------------------------------------------------------------

dr_symptom() {
  if rs_has bad service || rs_has bad page || rs_has bad listening; then
    printf 'The page is down: nobody can open it.'
  elif rs_has bad "sign-in page"; then
    printf 'The page answers, but it crashes when it is drawn.'
  elif [ "$DOCTOR_BAD" -gt 0 ]; then
    printf 'The page answers, but something it relies on is broken.'
  elif [ "$DOCTOR_WARN" -gt 0 ]; then
    printf 'It is running; there are a few things worth a look.'
  else
    printf 'It is running, and every check is fine.'
  fi
}

dr_explain() {
  local i n=${#PL_FUNC[@]}
  printf '\n  %s%s%s\n' "$B" "$(dr_symptom)" "$OFF"
  if [ "$n" -gt 0 ]; then
    printf '\n  %sWhat is wrong, from the bottom up%s\n' "$B" "$OFF"
    for i in "${!PL_FUNC[@]}"; do
      case "${PL_KIND[i]}" in tidy) continue ;; esac
      [ "${PL_FUNC[i]}" != fix_restart ] || continue
      WRAP_FIRST="  ${RED}${S_BAD}${OFF} " wrap "    " "" "${PL_WHY[i]}"
    done
  fi
  if [ -n "$DR_LOG" ] && [ -n "$(dr_evidence)" ]; then
    printf '\n  %sWhat its log says%s\n' "$B" "$OFF"
    printf '    %s%s%s\n' "$DIM" "$(dr_evidence)" "$OFF"
  fi
}

dr_show_plan() {
  local i n=${#PL_FUNC[@]} how
  [ "$n" -gt 0 ] || return 0
  printf '\n  %sWhat I will do%s\n' "$B" "$OFF"
  for i in "${!PL_FUNC[@]}"; do
    case "${PL_KIND[i]}" in
      net) how="downloads" ;;
      risky) how="asks you first" ;;
      tidy) how="optional" ;;
      *) how="" ;;
    esac
    printf '  %s%2d%s  %-48s %s%s%s\n' "$CYN" $((i + 1)) "$OFF" "${PL_TITLE[i]}" "$DIM" "$how" "$OFF"
    WRAP_FIRST="      " wrap "      " "$DIM" "${PL_DO[i]}"
  done
}

dr_show_needs() {
  local i
  [ "${#NEED_TEXT[@]}" -gt 0 ] || return 0
  printf '\n  %sWhat only you can do%s %s(I carry on with the rest meanwhile)%s\n' "$B" "$OFF" "$DIM" "$OFF"
  for i in "${!NEED_TEXT[@]}"; do
    WRAP_FIRST="  ${YEL}${S_WARN}${OFF} " wrap "    " "" "${NEED_TEXT[i]}"
    [ -z "${NEED_CMD[i]}" ] || cmdline "${NEED_CMD[i]}"
  done
}

# --- doing it ---------------------------------------------------------------------------------------

dr_run() { # the steps, in order; the ones that talk to the person run in the open, in a subshell so a failure ends only that step
  local i n=${#PL_FUNC[@]} func kind title
  progress_total "$n"
  for i in "${!PL_FUNC[@]}"; do
    func="${PL_FUNC[i]}"; kind="${PL_KIND[i]}"; title="${PL_TITLE[i]}"
    [ "$kind" != tidy ] || continue
    progress_to "$i"
    LAST_STEP_STATUS=0
    case "$func" in
      fix_database|fix_space)
        printf '\n  %s%s%s\n' "$B" "$title" "$OFF"
        # shellcheck disable=SC2034  # read by finish in lib/common.sh
        ( FINISH_EMBEDDED=1; "$func" ) || LAST_STEP_STATUS=$?
        ;;
      fix_restart)
        printf '\n'
        "$func"
        ;;
      *)
        try_step "$title" "$func"
        ;;
    esac
    if [ "$LAST_STEP_STATUS" = 0 ]; then DONE_TITLES+=("$title"); fi
  done
  progress_to "$n"
}

dr_tidy() { # what is not a fault but would help, asked one at a time after the repair
  local i
  for i in "${!PL_FUNC[@]}"; do
    [ "${PL_KIND[i]}" = tidy ] || continue
    printf '\n'
    if approve "While I am here: ${PL_TITLE[i]}? ${PL_WHY[i]}" yes; then
      # shellcheck disable=SC2034  # read by finish in lib/common.sh
      ( FINISH_EMBEDDED=1; "${PL_FUNC[i]}" ) || warn "That did not work: ${PL_TITLE[i]}."
    fi
  done
}

dr_before() { # remember which checks were not fine, to say what changed
  local i
  BEFORE_NAMES=()
  for i in "${!_DR_NAME[@]}"; do
    case "${_DR_STATE[i]}" in warn|bad) BEFORE_NAMES+=("${_DR_NAME[i]}") ;; esac
  done
}

dr_report() { # after the second look: what is better, and what is not
  local name i fixed=() still=0
  for name in "${BEFORE_NAMES[@]:-}"; do
    [ -n "$name" ] || continue
    if ! rs_has bad "$name" && ! rs_has warn "$name"; then fixed+=("$name"); fi
  done
  if [ "${#fixed[@]}" -gt 0 ]; then
    printf '\n  %sWhat is better now%s\n' "$B" "$OFF"
    for name in "${fixed[@]}"; do printf '  %s%s%s%s %s\n' "$B" "$GRN" "$S_OK" "$OFF" "$name"; done
  fi
  for i in "${!_DR_STATE[@]}"; do
    case "${_DR_STATE[i]}" in warn|bad) still=$((still + 1)) ;; esac
  done
  if [ "$still" -gt 0 ]; then
    printf '\n  %sWhat is still not right%s\n' "$B" "$OFF"
    doctor_show issues
  fi
}

cmd_doctor() {
  local page=0 saved_bad
  sweep
  dr_before
  dr_read_log
  dr_plan || true
  printf '\n'
  dr_explain
  if [ "${#PL_FUNC[@]}" -eq 0 ] && [ "${#NEED_TEXT[@]}" -eq 0 ]; then
    if [ "$DOCTOR_WARN" -gt 0 ]; then
      printf '\n'
      doctor_show problems
      finish warn "Nothing here for me to fix; $DOCTOR_WARN thing$([ "$DOCTOR_WARN" -eq 1 ] || echo s) worth a look"
    else
      finish ok "Nothing is wrong"
    fi
    return 0
  fi
  dr_show_plan
  dr_show_needs
  if [ "${#PL_FUNC[@]}" -eq 0 ]; then
    printf '\n'
    finish bad "There is nothing I can do for this from here: it needs you, as above"
    return 0
  fi
  if [ "$DRY_RUN" = 1 ]; then
    finish ok "Dry run: nothing was changed"
    return 0
  fi
  printf '\n'
  local asking=0 i
  for i in "${!PL_KIND[@]}"; do [ "${PL_KIND[i]}" != risky ] || asking=$((asking + 1)); done
  # With nobody at a terminal and no --yes, approve itself stops here as a failure.
  if ! approve "Go ahead with these$([ "$asking" -eq 0 ] || echo " (${asking} of them will ask you again)")?" yes; then
    say "Nothing was changed."
    return 0
  fi
  dr_run
  printf '\n'
  sweep
  printf '\n'
  dr_report
  if page_health >/dev/null 2>&1; then page=1; fi
  saved_bad="$DOCTOR_BAD"
  if [ "$DOCKER_MODE" = 0 ] && ! service_installed && [ "$page" = 0 ] && [ "${#DONE_TITLES[@]}" -gt 0 ]; then
    note "It is started by hand here, so start it again yourself: cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} run"
  fi
  if [ "$saved_bad" -eq 0 ]; then
    if [ "$page" = 1 ]; then finish ok "Restored: the page answers, and every check that must pass does"
    elif [ "$DOCTOR_WARN" -gt 0 ]; then finish warn "Fixed what I could; $DOCTOR_WARN thing$([ "$DOCTOR_WARN" -eq 1 ] || echo s) still worth a look"
    else finish ok "Fixed"
    fi
    dr_tidy
  else
    finish bad "Not fully restored: $saved_bad thing$([ "$saved_bad" -eq 1 ] || echo s) still wrong"
    after "What to do next"
    {
      rs_has bad "sign-in page" && printf '  sudo %s rescue rollback    # if an upgrade just ran, this undoes it\n' "$0"
      printf '  sudo %s logs                 # what it says now\n' "$0"
      printf '  sudo %s check --all          # the full picture, to send to whoever is helping\n' "$0"
    } | show_commands
    breakglass_hint
  fi
}
