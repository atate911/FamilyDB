#!/usr/bin/env bash
# Break glass: `maintain.sh rescue`. For the day the usual fixes are not enough: nobody can sign in,
# it will not start, an upgrade broke it, the database is damaged, the disk is full. Source it, do
# not run it; maintain.sh names what it needs (TARGET, SERVICE_USER, DOCKER_MODE, DB, BACKUP_DIR and
# the commands it already has: take_backup, stop_bot, start_bot, cmd_restore, cmd_password ...).
#
# Each way looks first and says what it found, then offers the remedies that fit, one at a time. A
# remedy that can be undone by running something is asked with Enter for yes; one that loses data
# (a database put back, a backup deleted, everyone signed out) needs a typed "yes" at a terminal
# and is never answered by --yes. Whatever it changes in the database is backed up first, and what
# it replaces is kept beside the backups, not thrown away. It uses nothing from the program except
# where it has to (a new password), so it works when the program does not.
#
#   cmd_rescue        the menu, or one way by name (RESCUE_WHAT)

RESCUE_WHAT=""

rs_confirm_risky() { # rs_confirm_risky QUESTION - for what cannot be undone by running it again
  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] would ask: $1"
    return 0
  fi
  if [ ! -t 0 ]; then
    warn "$1"
    note "That cannot be put back by running it again, so it is never done without a person at a terminal. Run this from one."
    return 1
  fi
  local reply
  read -r -p "${RED}?${OFF} ${B}$1${OFF} Type ${B}yes${OFF} to go ahead: " reply || reply=""
  [ "$reply" = yes ]
}

rs_ask() { # rs_ask PROMPT - a line typed at a terminal; empty without one
  local reply=""
  [ -t 0 ] || { printf ''; return 0; }
  read -r -p "${CYN}?${OFF} ${B}$1${OFF}: " reply || reply=""
  printf '%s' "$reply"
}

rs_has() { # rs_has STATE NAME - the last look found this check in that state
  local i
  for i in "${!_DR_NAME[@]}"; do
    [ "${_DR_NAME[i]}" = "$2" ] && [ "${_DR_STATE[i]}" = "$1" ] && return 0
  done
  return 1
}

rs_any_bad() { # rs_any_bad NAME... - any of these checks is wrong (warn or bad)
  local name
  for name in "$@"; do
    rs_has bad "$name" && return 0
    rs_has warn "$name" && return 0
  done
  return 1
}

rs_look() { # rs_look SECTION... - run those machine sections and show only what is wrong
  doctor_begin
  dc_setup
  local section
  for section in "$@"; do "dc_${section}" || true; done
  doctor_show problems
  [ $((DOCTOR_WARN + DOCTOR_BAD)) -gt 0 ] || say "  Nothing in those sections is wrong."
}

rs_service_restart() { # restart the bot after a change, saying whether it came back
  STEP_QUIET=1 stop_bot
  STEP_QUIET=1 QUIET_START=1 start_bot
}

rs_database_sound() { # rs_database_sound FILE - succeeds when it is a sound FamilyDB database; prints its migration
  local py="${TARGET}/.venv/bin/python"
  [ -x "$py" ] || py="$(command -v python3 || true)"
  [ -n "$py" ] || return 1
  as_root "$py" - "$1" <<'PY' 2>/dev/null
import sqlite3
import sys
from pathlib import Path

try:
    conn = sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
    if conn.execute("pragma quick_check").fetchone()[0] != "ok":
        sys.exit(1)
    conn.execute("select id from members limit 1")
    print(conn.execute("select max(version) from schema_version").fetchone()[0] or 0)
except Exception:
    sys.exit(1)
PY
}

rs_set_aside() { # rs_set_aside - copy the database and its journal files into a folder of their own, and say where
  local stamp dest f
  stamp="$(date +%Y%m%d%H%M%S)"
  dest="${BACKUP_DIR}/set-aside-${stamp}"
  as_root mkdir -p "$dest"
  for f in "$DB" "${DB}-wal" "${DB}-shm"; do
    [ ! -e "$f" ] || as_root cp -p "$f" "$dest/"
  done
  as_root chmod -R go-rwx "$dest"
  printf '%s' "$dest"
}

rs_free_mb() { df -Pm "${1:-$TARGET}" 2>/dev/null | awk 'NR==2 {print $4}'; }

# --- the menu ---------------------------------------------------------------------------------------

rescue_menu() {
  local pick
  printf '\n  %sWhat is wrong?%s\n\n' "$B" "$OFF"
  printf '  %s1%s  %-38s %s%s%s\n' "$CYN" "$OFF" "Nobody can sign in, or no page opens" "$DIM" "a new password, the lockout, sign everyone out" "$OFF"
  printf '  %s2%s  %-38s %s%s%s\n' "$CYN" "$OFF" "It will not start, or keeps stopping" "$DIM" "ownership, packages, a bad setting" "$OFF"
  printf '  %s3%s  %-38s %s%s%s\n' "$CYN" "$OFF" "An upgrade broke it" "$DIM" "the code back, and the data if it changed" "$OFF"
  printf '  %s4%s  %-38s %s%s%s\n' "$CYN" "$OFF" "The database is damaged" "$DIM" "check, restore a backup, salvage" "$OFF"
  printf '  %s5%s  %-38s %s%s%s\n' "$CYN" "$OFF" "The disk is full" "$DIM" "free what is safe to free" "$OFF"
  printf '\n'
  if [ ! -t 0 ]; then
    note "Name one: sudo ${0} rescue locked-out | wont-start | rollback | database | space"
    finish ok "Nothing was changed"
    return 0
  fi
  pick="$(rs_ask "Which? [1-5, Enter to leave]")"
  case "$pick" in
    1) rescue_locked_out ;;
    2) rescue_wont_start ;;
    3) rescue_rollback ;;
    4) rescue_database ;;
    5) rescue_space ;;
    *) finish ok "Nothing was changed" ;;
  esac
}

# --- nobody can get in ------------------------------------------------------------------------------

rescue_locked_out() {
  local said code=0 enabled site restart=0 name admins port env="${TARGET}/.env"
  as_root test -f "$env" || die "there is no ${env}" "Without it the program has no settings at all: sudo ${0} rescue wont-start"
  printf '\n'
  if [ "$DOCKER_MODE" = 1 ] || service_active; then kv "Service" "running" ok; else kv "Service" "not running" bad; fi
  said="$(page_health)" || code=$?
  case "$code" in
    0) kv "Page" "answers" ok ;;
    1) kv "Page" "$said" bad ;;
    *) kv "Page" "not asked: ${said}" off ;;
  esac
  enabled="$(env_file_value WEB_ENABLED)"
  if dc_truthy "$enabled"; then kv "Web page" "switched on in .env" ok; else kv "Web page" "switched OFF in .env (WEB_ENABLED=${enabled:-unset})" bad; fi
  site="$(env_file_value WEB_DOMAIN)"
  PUBLIC_PORT="$(env_file_value WEB_PUBLIC_PORT)"; PUBLIC_PORT="${PUBLIC_PORT:-443}"
  if [ -n "$site" ]; then kv "Address" "$(public_url "$site")"; else kv "Address" "this machine only, through an SSH tunnel"; fi
  admins="$(familydb_cmd members list 2>/dev/null | grep -E '\[(admin|parent)\]' | head -6 || true)"
  if [ -n "$admins" ]; then
    printf '\n  %sWho can sign in%s\n' "$B" "$OFF"
    printf '%s\n' "$admins" | sed "s/^/    ${DIM}/; s/\$/${OFF}/"
  fi

  if ! dc_truthy "$enabled"; then
    printf '\n'
    if approve "The page is switched off, so there is nothing to sign in to. Switch it on and restart?" yes; then
      if [ "$DRY_RUN" = 1 ]; then note "[dry run] would set WEB_ENABLED=true in .env"; else env_file_set WEB_ENABLED true; ok "Set WEB_ENABLED=true in .env"; fi
      restart=1
    fi
  elif [ "$code" = 1 ]; then
    printf '\n'
    para "The page is on but does not answer, so signing in is not the trouble yet. Get it running first:"
    cmdline "sudo ${0} rescue wont-start"
  fi

  printf '\n'
  if approve "Restart the bot? (Clears \"Too many tries\": the counts live in memory. A message being answered is interrupted.)" no; then restart=1; fi

  if [ -t 0 ]; then
    printf '\n'
    if approve "Make a new password for someone?" yes; then
      name="$(rs_ask "Whose? A name from the family list above, or Enter for the first admin (or the family password)")"
      # shellcheck disable=SC2034  # read by cmd_password in maintain.sh
      PASSWORD_FOR="$name"
      if [ "$DRY_RUN" = 1 ]; then
        note "[dry run] would make a starting password${name:+ for ${name}}"
      else
        cmd_password || warn "That did not work. If the program will not run, see: sudo ${0} rescue wont-start"
        hint "Copy it now: it is not kept anywhere and cannot be shown again. Clear the terminal afterwards."
      fi
    fi
  else
    printf '\n'
    note "A new password needs a person at a terminal to see it once: sudo ${0} password [NAME]"
  fi

  if as_root test -f "${TARGET}/data/web_secret" && [ -z "$(env_file_value WEB_SECRET_KEY)" ]; then
    printf '\n'
    if rs_confirm_risky "Sign everyone out, on every device? (Deletes the key their sign-ins are signed with.)"; then
      if [ "$DRY_RUN" = 1 ]; then note "[dry run] would delete data/web_secret"; else as_root rm -f "${TARGET}/data/web_secret"; ok "Signed everyone out: a new key is made at the next start"; fi
      restart=1
    fi
  fi

  if [ "$restart" = 1 ]; then
    printf '\n'
    rs_service_restart
    [ "$DRY_RUN" = 1 ] || { page_health >/dev/null && ok "The page answers" || warn "The page does not answer yet: sudo ${0} rescue wont-start"; }
  fi

  after "If the address does not open at all (a certificate, DNS or the firewall) reach the page without it"
  port="$(env_file_value WEB_PORT)"; port="${port:-8080}"
  show_commands <<EOF
  ssh -L 8080:127.0.0.1:${port} ${SUDO_USER:-you}@$(this_address 2>/dev/null || echo this-server)     # on your own computer
  then open http://127.0.0.1:8080/ in its browser
EOF
  finish ok "Done"
}

# --- it will not start ------------------------------------------------------------------------------

rs_stored_settings() { # the names of the settings kept on the page, one a line
  local py="${TARGET}/.venv/bin/python"
  [ -x "$py" ] || py="$(command -v python3 || true)"
  [ -n "$py" ] || return 0
  as_root "$py" - "$DB" <<'PY' 2>/dev/null || true
import sqlite3
import sys
from pathlib import Path

conn = sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
for (key,) in conn.execute("select key from app_settings order by key"):
    print(key)
PY
}

rs_forget_setting() { # rs_forget_setting KEY - the page's saved value goes, so the setting falls back to .env or its default
  local py="${TARGET}/.venv/bin/python"
  [ -x "$py" ] || py="$(command -v python3 || true)"
  as_root "$py" - "$DB" "$1" <<'PY'
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1], timeout=10)
removed = conn.execute("delete from app_settings where key = ?", (sys.argv[2],)).rowcount
conn.commit()
print(removed)
PY
}

rescue_wont_start() {
  local ownership=0 files=0 packages=0 migrate=0 reload=0 reset="" keys key worst
  printf '\n  %sWhat is wrong now%s\n' "$B" "$OFF"
  rs_look files git config python database service
  if [ "$DOCKER_MODE" = 0 ] && service_installed && have journalctl; then
    printf '\n  %sWhat its log says%s\n' "$B" "$OFF"
    as_root journalctl -u familydb -n 12 --no-pager -o cat 2>/dev/null | sed "s/^/    ${DIM}/; s/\$/${OFF}/" | cut -c1-150 || true
  elif [ "$DOCKER_MODE" = 1 ]; then
    printf '\n  %sWhat its log says%s\n' "$B" "$OFF"
    as_root docker compose --project-directory "$TARGET" logs --tail 12 bot 2>&1 | sed "s/^/    ${DIM}/; s/\$/${OFF}/" | cut -c1-150 || true
  fi

  rs_any_bad "data folder" "database file" "journal files" ".env" && ownership=1
  rs_any_bad "program files" "missing files" && files=1
  rs_any_bad "interpreter" "packages" "program" "image" && packages=1
  rs_has bad schema && migrate=1
  rs_has warn "unit loaded" && reload=1
  printf '\n'

  if [ "$ownership" = 1 ] && [ "$DOCKER_MODE" = 0 ]; then
    if approve "Give ${SERVICE_USER} back its files (the data folder and .env)?" yes; then
      if dc_data_dir_ok "${DC_DB%/*}"; then
        step "Handing the files back to ${SERVICE_USER}" as_root chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DC_DB%/*}"
      else
        warn "${DC_DB%/*} does not look like FamilyDB's data folder, so who owns it is left alone."
      fi
      [ "$DRY_RUN" = 1 ] || as_root chown "${SERVICE_USER}:${SERVICE_USER}" "${TARGET}/.env" 2>/dev/null || true
    fi
  fi
  if [ "$files" = 1 ]; then
    if approve "Put back the program files that are gone or changed? (git checkout of every tracked file; changes to them are lost.)" yes; then
      step "Restoring the program files" as_root git -C "$TARGET" checkout -- .
    fi
  fi
  if [ "$packages" = 1 ]; then
    if [ "$DOCKER_MODE" = 1 ]; then
      if approve "Build the image again?" yes; then
        step "Building the image" as_root docker compose --project-directory "$TARGET" build
      fi
    elif approve "Build the Python environment again from the lock file? (Takes a minute or two; nothing in data/ is touched.)" yes; then
      if [ "$DRY_RUN" != 1 ] && [ ! -x "${TARGET}/.venv/bin/python" ]; then as_root rm -rf "${TARGET}/.venv"; fi
      retry 2 "Installing the packages from uv.lock" as_root env PATH="${SYSTEM_PATH:-$PATH}" uv sync --frozen --no-dev --project "$TARGET"
      [ "$DRY_RUN" = 1 ] || as_root chmod -R go-w "$TARGET" 2>/dev/null || true
    fi
  fi
  if [ "$migrate" = 1 ]; then
    if approve "Bring the database up to date (apply its missing migrations)?" yes; then
      BACKUP_QUIET=1 take_backup "$BACKUP_DIR"
      step "Applying the migrations" familydb_cmd db migrate
    fi
  fi
  if [ "$reload" = 1 ]; then
    if approve "Tell systemd to read the changed unit file?" yes; then
      step "Reloading systemd" as_root systemctl daemon-reload
    fi
  fi
  if [ "$DOCKER_MODE" = 0 ] && service_installed && [ "$(as_root systemctl show familydb -p Result --value 2>/dev/null || true)" = start-limit-hit ]; then
    if approve "systemd gave up after too many failed starts. Clear that so it may try again?" yes; then
      step "Clearing systemd's \"too many failed starts\"" as_root systemctl reset-failed familydb
    fi
  fi

  keys="$(rs_stored_settings)"
  if [ -n "$keys" ] && [ "$DRY_RUN" != 1 ] && [ -t 0 ]; then
    if approve "Forget one setting saved on the settings page? (For a value that stops it starting; the setting goes back to .env or its default.)" no; then
      printf '%s\n' "$keys" | paste -sd' ' | fold -s -w "$(( $(ui_width) - 4 ))" | sed 's/^/    /'
      key="$(rs_ask "Which one")"
      if [ -n "$key" ] && printf '%s\n' "$keys" | grep -qx "$key"; then
        BACKUP_QUIET=1 take_backup "$BACKUP_DIR"
        rs_forget_setting "$key" >/dev/null && ok "Forgot ${key}: it falls back to .env or its default" && reset=1
      elif [ -n "$key" ]; then
        warn "There is no saved setting called ${key}."
      fi
    fi
  fi

  printf '\n'
  rs_service_restart
  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  worst=0
  case "${BOT_STARTED:-}" in
    0) worst=1 ;;
  esac
  if [ "$worst" = 1 ]; then
    finish bad "It still does not start"
    after "What is left"
    show_commands <<EOF
  sudo ${0} logs                       # what it says now
  sudo ${0} rescue rollback            # if an upgrade just changed it
  sudo ${0} rescue database            # if the log names the database
EOF
  else
    finish ok "It starts${reset:+, without the setting that stopped it}"
  fi
}

# --- an upgrade broke it ----------------------------------------------------------------------------

rs_migration_at() { # rs_migration_at REF - the number of the newest migration that version has; empty if unknown
  as_root git -C "$TARGET" ls-tree -r --name-only "$1" -- src/familydb/store/migrations 2>/dev/null \
    | sed -n 's|.*/\([0-9]\{4\}\)_.*\.sql$|\1|p' | sort | tail -1 | sed 's/^0*//' || true
}

rescue_rollback() {
  [ -d "${TARGET}/.git" ] || die "${TARGET} is not a git checkout, so there is no earlier version to go back to" \
    "Unpack the older copy over it, keeping .env and data/."
  local from backup source label have wants need_data=0 taken when
  from="$(pending_get before)"; backup="$(pending_get backup)"; source="an upgrade that stopped part-way"
  if [ -z "$from" ]; then
    from="$(last_upgrade_get from)"; backup="$(last_upgrade_get backup)"
    when="$(last_upgrade_get at)"
    source="the last upgrade ($(ago $(( $(date +%s) - ${when:-0} ))))"
  fi
  [ -n "$from" ] || die "nothing here remembers an upgrade, so it does not know what to go back to" \
    "Pick the version yourself:" \
    "  sudo git -C ${TARGET} log --oneline --decorate -15" \
    "  sudo git -C ${TARGET} checkout --detach THAT_COMMIT" \
    "  sudo uv sync --frozen --no-dev --project ${TARGET}" \
    "and, if the database must go back too: sudo ${0} restore BACKUP"
  as_root git -C "$TARGET" rev-parse --verify --quiet "${from}^{commit}" >/dev/null \
    || die "the version it would go back to (${from}) is no longer in this checkout" \
           "Fetch it first: sudo git -C ${TARGET} fetch --tags origin"
  label="$(version_label "$from")"
  printf '\n'
  kv "Undoing" "$source"
  kv "Now" "$(version_label HEAD)" bad
  kv "Back to" "$label" ok
  have="$(database_version)"; wants="$(rs_migration_at "$from")"
  if [ -n "$have" ] && [ -n "$wants" ] && [ "$have" -gt "$wants" ]; then
    need_data=1
    kv "Database" "at migration ${have}; ${label} knows up to ${wants}: it has to go back too" warn
  else
    kv "Database" "at migration ${have:-?}, which ${label} can read as it is: only the code goes back" ok
  fi
  if [ "$need_data" = 1 ]; then
    if [ -z "$backup" ] || ! as_root test -f "$backup"; then
      die "the database has to go back, and the backup taken before the upgrade is not there (${backup:-no record})" \
          "Look for one yourself: ls -lt ${BACKUP_DIR}" \
          "then: sudo ${0} rescue rollback after putting it in place with: sudo ${0} restore FILE"
    fi
    taken="$(as_root stat -c %Y "$backup" 2>/dev/null || echo 0)"
    kv "From" "${backup#"${TARGET}/"} ($(date -d "@${taken}" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '?'), $(ago $(( $(date +%s) - taken ))))"
    caution "Everything saved since then is lost: every message, plan and change made after the upgrade."
    hint "A copy of the database as it is now is kept first, so this can itself be undone."
    rs_confirm_risky "Put the code AND the database back?" || { say "Nothing was changed."; return 0; }
  else
    approve "Put the code back to ${label}?" yes || { say "Nothing was changed."; return 0; }
  fi

  progress_total 6
  BACKUP_QUIET=1 take_backup "$BACKUP_DIR"
  local safety="$LAST_BACKUP"
  progress_to 1
  STEP_QUIET=1 stop_bot
  progress_to 2
  step "Checking out ${label}" as_root git -C "$TARGET" checkout --quiet --detach "$from"
  progress_to 3
  if [ "$DOCKER_MODE" = 1 ]; then
    step "Rebuilding the image" as_root docker compose --project-directory "$TARGET" build
  else
    retry 2 "Installing the packages that version used" as_root env PATH="${SYSTEM_PATH:-$PATH}" uv sync --frozen --no-dev --project "$TARGET"
    [ "$DRY_RUN" = 1 ] || as_root chmod -R go-w "$TARGET" 2>/dev/null || true
  fi
  progress_to 4
  if [ "$need_data" = 1 ]; then
    local owner="${SERVICE_USER}:${SERVICE_USER}"
    [ "$DOCKER_MODE" = 0 ] || owner="$(stat -c '%u:%g' "$DB" 2>/dev/null || echo 1000:1000)"
    step "Putting the database from before the upgrade back" put_backup_in_place "$backup" "$owner"
  fi
  progress_to 5
  STEP_QUIET=1 QUIET_START=1 start_bot
  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  progress_to 6
  as_root rm -f "$UPGRADE_PENDING" "$LAST_UPGRADE"
  if [ "${BOT_STARTED:-}" = 0 ]; then
    finish bad "Back on ${label}, but FamilyDB did not start"
  else
    finish ok "Back on ${label}"
  fi
  if [ "$need_data" = 1 ]; then
    kv "Before" "$safety"
    cmdline "sudo ${0} restore ${safety}" "to undo the data part"
  fi
}

# --- the database is damaged ------------------------------------------------------------------------

rescue_database() {
  local quick candidate best="" version taken age listing="" i=0 choice file
  [ -f "$DB" ] || printf '\n  %sThere is no database at %s.%s\n' "$YEL" "$DB" "$OFF"
  printf '\n'
  if [ -f "$DB" ]; then
    if quick="$(rs_database_sound "$DB")"; then
      kv "Database" "sound, at migration ${quick}" ok
      para "SQLite finds nothing wrong with the file, so this is not what is stopping it. Try: sudo ${0} rescue wont-start"
      finish ok "Nothing to repair"
      return 0
    fi
    kv "Database" "SQLite cannot read it as a FamilyDB database" bad
  fi
  printf '\n  %sBackups, newest first%s\n' "$B" "$OFF"
  while IFS= read -r candidate; do
    [ -n "$candidate" ] || continue
    i=$((i + 1))
    [ "$i" -le 6 ] || break
    taken="$(as_root stat -c %Y "$candidate" 2>/dev/null || echo 0)"
    age="$(ago $(( $(date +%s) - taken )))"
    if version="$(rs_database_sound "$candidate")"; then
      kv "$i" "${candidate##*/}  ${age}, $(as_root du -h "$candidate" | cut -f1), migration ${version}" ok
      [ -n "$best" ] || best="$candidate"
    else
      kv "$i" "${candidate##*/}  ${age}: not sound" bad
    fi
    listing="${listing}${candidate}"$'\n'
  done < <(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -printf '%T@ %p\n' 2>/dev/null | sort -rn | cut -d' ' -f2-)
  [ "$i" -gt 0 ] || printf '  %sNone in %s.%s\n' "$DIM" "$BACKUP_DIR" "$OFF"

  if [ -n "$best" ] && [ -t 0 ]; then
    printf '\n'
    choice="$(rs_ask "Restore which? Number from the list (Enter for ${best##*/}, n for none)")"
    case "$choice" in
      n|N|no) best="" ;;
      '') ;;
      *[!0-9]*) best="" ;;
      *) file="$(printf '%s' "$listing" | sed -n "${choice}p")"; [ -z "$file" ] || best="$file" ;;
    esac
  elif [ -n "$best" ]; then
    note "To restore the newest sound one: sudo ${0} restore ${best}"
    best=""
  fi
  if [ -n "$best" ]; then
    caution "Everything saved after ${best##*/} was made is lost. The damaged database is kept beside the backups."
    if rs_confirm_risky "Restore ${best##*/} over the database?"; then
      if [ "$DRY_RUN" = 1 ]; then
        note "[dry run] would stop the bot, set the damaged database aside, and restore ${best}"
      else
        STEP_QUIET=1 stop_bot
        local aside
        aside="$(rs_set_aside)"
        ok "Kept the damaged database in ${aside#"${TARGET}/"}"
        as_root rm -f "$DB" "${DB}-wal" "${DB}-shm"
        # shellcheck disable=SC2034  # read by cmd_restore in maintain.sh
        RESTORE_FILE="$best"
        local saved="$ASSUME_YES"
        ASSUME_YES=1
        cmd_restore
        ASSUME_YES="$saved"
        return 0
      fi
    fi
  fi

  if [ -f "$DB" ] && have sqlite3 && [ -t 0 ]; then
    printf '\n'
    if approve "Salvage what can be read from the damaged file into a new one? (Never touches the original; you decide what to do with the result.)" "$([ -n "$best" ] && echo no || echo yes)"; then
      local work out stamp
      stamp="$(date +%Y%m%d%H%M%S)"
      work="$(mktemp -d)"
      as_root cp -p "$DB" "$work/damaged.sqlite3"
      [ ! -e "${DB}-wal" ] || as_root cp -p "${DB}-wal" "$work/damaged.sqlite3-wal"
      out="${BACKUP_DIR}/salvaged-${stamp}.sqlite3"
      if as_root sh -c 'sqlite3 "$1" ".recover" | sqlite3 "$2"' sh "$work/damaged.sqlite3" "$out" 2>>"${LOG_FILE:-/dev/null}"; then
        as_root chmod 600 "$out"
        if version="$(rs_database_sound "$out")"; then
          ok "Salvaged into ${out#"${TARGET}/"} (migration ${version}); it passes SQLite's check."
          note "Check it before using it, then put it in place with:"
          cmdline "sudo ${0} restore ${out}"
        else
          warn "It was written to ${out#"${TARGET}/"}, but it is not a sound FamilyDB database (too little could be read)."
        fi
      else
        warn "sqlite3 could not recover anything from it."
      fi
      rm -rf "$work"
    fi
  elif [ -f "$DB" ] && ! have sqlite3; then
    note "To try to salvage a damaged file: sudo apt-get install sqlite3, then run this again."
  fi
  finish ok "Done"
}

# --- the disk is full -------------------------------------------------------------------------------

rs_size_mb() { # rs_size_mb PATH... - how many megabytes they hold
  as_root du -sm "$@" 2>/dev/null | awk '{s += $1} END {print s + 0}' || true
}

rescue_space() {
  local before after journal apt uvc docker backups old n
  before="$(rs_free_mb)"
  printf '\n'
  kv "Free now" "$(dc_mb "${before:-0}") on the disk ${TARGET} lives on" "$([ "${before:-0}" -lt 500 ] && echo bad || echo ok)"
  printf '\n  %sWhat can be freed%s\n' "$B" "$OFF"
  journal=0
  if have journalctl; then
    journal="$(as_root journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | head -1 \
      | awk '{s = $1; n = s + 0; u = substr(s, length(s)); if (u == "G") n *= 1024; else if (u == "K") n /= 1024; else if (u == "T") n *= 1048576; printf "%d", n}' || true)"
    journal="${journal:-0}"
  fi
  apt="$(rs_size_mb /var/cache/apt/archives)"
  uvc=0
  if have uv; then uvc="$(rs_size_mb "$(uv cache dir 2>/dev/null || echo /nonexistent)")"; fi
  docker=0
  if have docker; then
    docker="$(as_root docker system df --format '{{.Reclaimable}}' 2>/dev/null \
      | awk '{s = $1; n = s + 0; if (s ~ /GB/) n *= 1024; else if (s ~ /kB/) n /= 1024; else if (s !~ /MB/) n /= 1048576; t += n} END {printf "%d", t}' || true)"
    docker="${docker:-0}"
  fi
  old="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -mtime +"$KEEP_DAYS" 2>/dev/null | wc -l || true)"
  n="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' 2>/dev/null | wc -l || true)"
  backups="$(rs_size_mb "$BACKUP_DIR")"
  kv "Journal" "${journal} MB of system logs (can be cut to 200 MB)"
  kv "Package cache" "${apt} MB downloaded by apt"
  [ "$uvc" -le 0 ] || kv "uv cache" "${uvc} MB of downloaded packages"
  [ "$docker" -le 0 ] || kv "Docker" "${docker} MB reclaimable (unused images and build cache)"
  kv "Backups" "${n} kept, ${backups} MB; ${old} older than ${KEEP_DAYS} days"

  printf '\n'
  if [ "$journal" -gt 200 ] && approve "Cut the system journal to 200 MB?" yes; then
    step "Trimming the journal" as_root journalctl --vacuum-size=200M
  fi
  if [ "$apt" -gt 20 ] && approve "Empty apt's download cache?" yes; then
    step "Cleaning apt's cache" as_root apt-get clean
  fi
  if [ "$uvc" -gt 20 ] && approve "Empty uv's download cache? (The next install downloads what it needs again.)" yes; then
    step "Cleaning uv's cache" uv cache clean
  fi
  if [ "$docker" -gt 20 ]; then
    if approve "Remove Docker images nothing uses, and the build cache?" yes; then
      step "Pruning Docker" as_root docker image prune -af
      step "Pruning the build cache" as_root docker builder prune -f
    fi
  fi
  if [ "$old" -gt 0 ] && [ "$n" -gt "$old" ]; then
    if rs_confirm_risky "Delete the ${old} backups older than ${KEEP_DAYS} days? The newest $((n - old)) stay."; then
      if [ "$DRY_RUN" = 1 ]; then note "[dry run] would delete ${old} backups"; else
        as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -mtime +"$KEEP_DAYS" -delete
        ok "Deleted ${old} old backups"
      fi
    fi
  fi
  after="$(rs_free_mb)"
  hint "The model-call texts the program keeps are the other big thing: Settings, Troubleshooting, 'keep_ai_text_days'."
  if [ "$DRY_RUN" = 1 ]; then finish ok "Dry run"; return 0; fi
  if [ "${after:-0}" -ge "${before:-0}" ]; then
    finish ok "Free space: $(dc_mb "${before:-0}") ${S_TO} $(dc_mb "${after:-0}")"
  fi
}

cmd_rescue() {
  case "$RESCUE_WHAT" in
    '') rescue_menu ;;
    locked-out|lockout|login) rescue_locked_out ;;
    wont-start|start) rescue_wont_start ;;
    rollback) rescue_rollback ;;
    database|db) rescue_database ;;
    space|disk) rescue_space ;;
    *) die "rescue what? \"${RESCUE_WHAT}\"" "One of: locked-out, wont-start, rollback, database, space (or none, for a menu)." ;;
  esac
}
