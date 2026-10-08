#!/usr/bin/env bash
# The checks `maintain.sh check` makes of the machine, before the program is asked anything: the files
# and who owns them, the git checkout, .env, Python and its packages, the database file, the service,
# the web server in front of the page and the page itself, and the host under it all. Source it, do
# not run it; maintain.sh names what it needs (TARGET, SERVICE_USER, DOCKER_MODE, DB, BACKUP_DIR,
# env_file_value, page_health, service_installed and the helpers in common.sh).
#
# It is written for the day the program will not start: nothing here imports FamilyDB, and each
# check that needs Python uses the interpreter on its own, as the service account, so "readable"
# means readable by the service and not just by root. A check reads and never repairs; what is wrong
# comes out as a row (doctor_row) with the command that fixes it, and `maintain.sh rescue` has the
# larger remedies.
#
#   dc_all            every section, with a bar while it works
#   dc_files ...      one section each: files git config python database service web https host backups

DC_DB=""            # the database file the service opens
DC_WEB=""           # http://HOST:PORT of the page, as this machine reaches it
DC_PORT=""
DC_HEADERS=""       # the headers of the last dc_http
DC_BODY=""          # and the start of its body
DC_CODE=""          # and its status
DC_ONLINE="${DC_ONLINE:-0}"   # 1 allows the checks that need the internet
_DC_OUT=""
_DC_RC=0
_DC_ASIS=0          # 1 when dc_try had no service account to be, and ran the command as whoever is running this

# dc_try CMD... - run it as the service account (its output in _DC_OUT, its status in _DC_RC). With no
# such account it runs as whoever this is, so a question about the code still gets an answer, and says
# so in _DC_ASIS: a question about what the service may write must not be answered by root.
dc_try() {
  _DC_RC=0; _DC_ASIS=0
  if [ "$DOCKER_MODE" = 1 ] || [ "$(id -un)" = "$SERVICE_USER" ]; then
    _DC_OUT="$(timeout 30 "$@" 2>&1)" || _DC_RC=$?
  elif ! id "$SERVICE_USER" >/dev/null 2>&1; then
    _DC_ASIS=1
    _DC_OUT="$(timeout 30 "$@" 2>&1)" || _DC_RC=$?
  else
    _DC_OUT="$(as_root timeout 30 sudo -n -u "$SERVICE_USER" "$@" 2>&1)" || _DC_RC=$?
  fi
}

dc_first() { # dc_first TEXT - its first non-empty line, cut to fit a row
  printf '%s\n' "$1" | sed '/^[[:space:]]*$/d' | head -1 | cut -c1-160
}

dc_last() { # dc_last TEXT - its last non-empty line: where a traceback says what went wrong
  printf '%s\n' "$1" | sed '/^[[:space:]]*$/d' | tail -1 | cut -c1-160
}

dc_list() { # dc_list N ITEM... - the first N items joined, and how many more there were
  local limit="$1" out="" count=0 item
  shift
  for item in "$@"; do
    count=$((count + 1))
    [ "$count" -le "$limit" ] || continue
    out="${out}${out:+, }${item}"
  done
  [ "$count" -le "$limit" ] || out="${out}, and $((count - limit)) more"
  printf '%s' "$out"
}

dc_loose() { # dc_loose MODE MASK - succeeds when MODE (octal, as stat prints it) has any of MASK's bits
  case "${1:-}" in ''|*[!0-7]*) return 1 ;; esac
  [ $((8#$1 & 8#$2)) -ne 0 ]
}

dc_meter() { # dc_meter USED TOTAL [WIDTH] - [██████░░░░], plain, so it reads the same in any colour
  local used="$1" total="$2" width="${3:-12}" cells i out=""
  [ "$total" -gt 0 ] || total=1
  cells=$((width * used / total))
  [ "$cells" -le "$width" ] || cells=$width
  for ((i = 0; i < width; i++)); do
    if [ "$i" -lt "$cells" ]; then out+="$BAR_FULL"; else out+="$BAR_EMPTY"; fi
  done
  printf '[%s]' "$out"
}

dc_mb() { # dc_mb MEGABYTES - 18.4 GB, 640 MB
  if [ "$1" -ge 1024 ]; then awk -v m="$1" 'BEGIN {printf "%.1f GB", m / 1024}'; else printf '%s MB' "$1"; fi
}

# dc_http PATH - fetch it from the page. Sets DC_CODE (000 when nothing answered), DC_HEADERS and
# DC_BODY; they are set here and not printed, because a command substitution would lose them.
dc_http() {
  local head body
  head="$(mktemp)"; body="$(mktemp)"
  DC_CODE="$(curl -sS --max-time 5 -o "$body" -D "$head" -w '%{http_code}' "${DC_WEB}${1}" 2>/dev/null)" || DC_CODE=000
  DC_CODE="${DC_CODE:-000}"
  DC_HEADERS="$(tr -d '\r' <"$head" 2>/dev/null || true)"
  DC_BODY="$(head -c 4000 "$body" 2>/dev/null || true)"
  rm -f "$head" "$body"
}

dc_header() { # dc_header NAME - a header of the last answer
  printf '%s\n' "$DC_HEADERS" | grep -i "^$1:" | head -1 | cut -d: -f2- | sed 's/^[[:space:]]*//' || true
}

dc_unit_lines() { # dc_unit_lines KEY - every KEY= line of the service file, the value only
  as_root sed -n "s/^${1}=//p" "$SERVICE_UNIT" 2>/dev/null || true
}

dc_unit_value() { # dc_unit_value KEY - the last of them
  dc_unit_lines "$1" | tail -1
}

# dc_data_dir_ok DIR - whether a repair may change who owns what is in DIR. The data folder comes from
# FAMILYDB_PATH, which anyone can type anything into, so a repair that hands a folder to the service
# account first asks whether it is plausibly FamilyDB's: a folder inside the install, or one named for
# it. Never the install itself (that is the code), never a system folder.
dc_data_dir_ok() {
  case "$1" in "${TARGET}"/?*) return 0 ;; esac
  case "$1" in
    /|/etc|/etc/*|/usr|/usr/*|/bin|/bin/*|/sbin|/sbin/*|/lib|/lib/*|/boot|/boot/*|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*) return 1 ;;
    /var|/var/|/home|/home/|/root|/root/|/opt|/opt/|/tmp|/tmp/|"$TARGET"|"${TARGET}/") return 1 ;;
  esac
  case "$1" in *familydb*) return 0 ;; esac
  return 1
}

dc_truthy() { case "$(printf '%s' "$1" | tr 'A-Z' 'a-z')" in true|1|yes|on|t|y) return 0 ;; esac; return 1; }

dc_setup() { # where the database is and where the page is, as the service sees them
  local path host
  DC_DB="$DB"
  if [ "$DOCKER_MODE" = 0 ] && service_installed; then
    path="$(dc_unit_lines Environment | tr ' ' '\n' | sed -n 's/^"\{0,1\}FAMILYDB_PATH=//p' | tr -d '"' | tail -1)"
    [ -z "$path" ] || DC_DB="$path"
  fi
  if [ "$DOCKER_MODE" = 0 ]; then
    path="$(env_file_value FAMILYDB_PATH)"
    if [ -n "$path" ]; then
      case "$path" in /*) DC_DB="$path" ;; *) DC_DB="${TARGET}/${path#./}" ;; esac
    fi
  fi
  host="$(env_file_value WEB_HOST)"; DC_PORT="$(env_file_value WEB_PORT)"; DC_PORT="${DC_PORT:-8080}"
  case "$host" in ''|0.0.0.0|::|'[::]') host=127.0.0.1 ;; esac
  case "$host" in *:*) case "$host" in '['*) ;; *) host="[${host}]" ;; esac ;; esac
  DC_WEB="http://${host}:${DC_PORT}"
}

# --- the files ------------------------------------------------------------------------------------

dc_files() {
  doctor_section "Files"
  local mode owner data missing f loose foreign
  if [ "$DOCKER_MODE" = 1 ]; then
    : # the container runs as its own user; the data folder row says what it needs
  elif id "$SERVICE_USER" >/dev/null 2>&1; then
    doctor_row ok "service account" "${SERVICE_USER} (uid $(id -u "$SERVICE_USER"))"
  else
    doctor_row bad "service account" "${SERVICE_USER} does not exist, so the service cannot start under it" \
      "sudo useradd --system --home ${TARGET} --shell /usr/sbin/nologin ${SERVICE_USER}   # or run install.sh again"
  fi

  mode="$(stat -c '%a' "$TARGET" 2>/dev/null || true)"; owner="$(stat -c '%U' "$TARGET" 2>/dev/null || true)"
  loose="$(as_root find "$TARGET" \( -path "${TARGET}/.git" -o -path "${TARGET}/.venv" -o -path "${TARGET}/data" -o -path "${TARGET}/backups" -o -path "${TARGET}/caddy" \) -prune \
           -o -perm /022 -not -type l -print 2>/dev/null | head -4 | sed "s|^${TARGET}/||" | tr '\n' ' ' || true)"
  if [ -n "$loose" ]; then
    doctor_row warn "install folder" "code anyone on this machine can change: ${loose% }" "sudo chmod -R go-w ${TARGET}"
  else
    doctor_row ok "install folder" "${TARGET}, owned by ${owner:-?}, mode ${mode:-?}; the code is not writable by others"
  fi

  missing=""
  for f in pyproject.toml uv.lock .env.example scripts/maintain.sh src/familydb/cli.py \
           src/familydb/web/templates/base.html src/familydb/web/static/style.css \
           src/familydb/web/static/themes.css src/familydb/wiki/_nav.json; do
    [ -e "${TARGET}/${f}" ] || missing="${missing}${missing:+ }${f}"
  done
  if [ -n "$missing" ]; then
    # shellcheck disable=SC2086  # the names are words
    doctor_row bad "program files" "missing: $(dc_list 4 $missing); the page cannot be drawn without them" \
      "sudo git -C ${TARGET} checkout -- .   # puts back every tracked file that is gone"
  elif ! ls "${TARGET}"/src/familydb/store/migrations/[0-9]*.sql >/dev/null 2>&1; then
    doctor_row bad "program files" "no migrations under src/familydb/store/migrations, so the database cannot be built" \
      "sudo git -C ${TARGET} checkout -- src/familydb/store/migrations"
  else
    doctor_row ok "program files" "pages, styles, wiki and migrations are all there"
  fi

  if [ ! -f "${TARGET}/.env" ]; then
    if [ "$DOCKER_MODE" = 1 ]; then
      doctor_row warn ".env" "none, so the container starts with no key and no password" \
        "cp ${TARGET}/.env.example ${TARGET}/.env, then fill it in"
    else
      doctor_row bad ".env" "missing: the service reads its settings from ${TARGET}/.env and will not start without it" \
        "sudo cp ${TARGET}/.env.example ${TARGET}/.env && sudo chown ${SERVICE_USER} ${TARGET}/.env && sudo chmod 600 ${TARGET}/.env"
    fi
  else
    mode="$(stat -c '%a' "${TARGET}/.env")"; owner="$(stat -c '%U' "${TARGET}/.env")"
    dc_try test -r "${TARGET}/.env"
    if [ "$DOCKER_MODE" = 0 ] && [ "$_DC_RC" != 0 ] && [ "$_DC_ASIS" = 0 ]; then
      doctor_row bad ".env" "owned by ${owner}, mode ${mode}: ${SERVICE_USER} cannot read it, so the service starts with none of its settings" \
        "sudo chown ${SERVICE_USER} ${TARGET}/.env && sudo chmod 600 ${TARGET}/.env"
    elif dc_loose "$mode" 077; then
      doctor_row warn ".env" "mode ${mode}: other users on this machine can read your keys" "sudo chmod 600 ${TARGET}/.env"
    else
      doctor_row ok ".env" "private (mode ${mode}, owner ${owner})"
    fi
  fi

  data="$(dirname "$DC_DB")"
  if [ ! -d "$data" ]; then
    doctor_row bad "data folder" "${data} does not exist; with it missing the sandbox cannot even set up the service" \
      "sudo mkdir -p ${data} && sudo chown ${SERVICE_USER}:${SERVICE_USER} ${data} && sudo chmod 700 ${data}"
  else
    dc_try sh -c 'f=$(mktemp "$1/.doctor.XXXXXX") && rm -f "$f"' sh "$data"
    if [ "$_DC_ASIS" = 1 ]; then
      doctor_row skip "data folder" "not tested: there is no ${SERVICE_USER} account to try writing as"
    elif [ "$DOCKER_MODE" = 1 ]; then
      foreign="$(as_root find "$data" -maxdepth 2 ! -uid 1000 2>/dev/null | head -3 | tr '\n' ' ' || true)"
      if [ -n "$foreign" ]; then
        doctor_row warn "data folder" "not all owned by uid 1000, which the container runs as: ${foreign% }" \
          "sudo chown -R 1000:1000 ${data}"
      else
        doctor_row ok "data folder" "${data}, owned by uid 1000 as the container needs"
      fi
    elif [ "$_DC_RC" != 0 ]; then
      doctor_row bad "data folder" "${SERVICE_USER} cannot write in ${data}: $(dc_last "$_DC_OUT")" \
        "sudo chown -R ${SERVICE_USER}:${SERVICE_USER} ${data} && sudo chmod 700 ${data}   # a read-only disk needs: sudo mount -o remount,rw /"
    else
      foreign="$(as_root find "$data" -maxdepth 2 ! -user "$SERVICE_USER" 2>/dev/null | sed "s|^${data}/||" | head -4 | tr '\n' ' ' || true)"
      if [ -n "$foreign" ]; then
        doctor_row bad "data folder" "files here belong to someone else, so the service may fail to write them (\"attempt to write a readonly database\"): ${foreign% }" \
          "sudo chown -R ${SERVICE_USER}:${SERVICE_USER} ${data}"
      else
        doctor_row ok "data folder" "${data}, ${SERVICE_USER} can write in it and owns what is in it"
      fi
    fi
  fi

  if [ -d "$BACKUP_DIR" ]; then
    dc_try sh -c 'f=$(mktemp "$1/.doctor.XXXXXX") && rm -f "$f"' sh "$BACKUP_DIR"
    if [ "$_DC_ASIS" = 1 ]; then
      :
    elif [ "$DOCKER_MODE" = 0 ] && [ "$_DC_RC" != 0 ]; then
      doctor_row warn "backups folder" "${SERVICE_USER} cannot write in ${BACKUP_DIR}, and the backup runs as ${SERVICE_USER}" \
        "sudo chown ${SERVICE_USER}:${SERVICE_USER} ${BACKUP_DIR}"
    else
      doctor_row ok "backups folder" "${BACKUP_DIR}, writable"
    fi
  fi
}

# --- the git checkout -----------------------------------------------------------------------------

dc_git() {
  doctor_section "Git"
  if [ ! -d "${TARGET}/.git" ]; then
    doctor_row warn "checkout" "not a git checkout, so \`upgrade\` has nothing to fetch with" \
      "Upgrade by unpacking a new copy over it, keeping .env and data/ (docs/INSTALL.md, 'Day to day')"
    return 0
  fi
  if ! have git; then
    doctor_row bad "git" "git is not installed, so upgrades and rollbacks cannot run" "sudo apt-get install git"
    return 0
  fi
  local out rc=0 branch short where changed deleted url key keyfile
  out="$(as_root git -C "$TARGET" status --porcelain --untracked-files=no 2>&1)" || rc=$?
  if [ "$rc" != 0 ]; then
    case "$out" in
      *"dubious ownership"*)
        doctor_row bad "checkout" "git refuses it as \"dubious ownership\": it belongs to a different user than the one running git, so every upgrade fails" \
          "sudo git config --global --add safe.directory ${TARGET}" ;;
      *) doctor_row bad "checkout" "git cannot read it: $(dc_first "$out")" \
           "sudo git -C ${TARGET} fsck   # and see docs/INSTALL.md for fetching a fresh copy" ;;
    esac
    return 0
  fi
  branch="$(as_root git -C "$TARGET" symbolic-ref -q --short HEAD 2>/dev/null || true)"
  short="$(as_root git -C "$TARGET" rev-parse --short HEAD 2>/dev/null || echo '?')"
  if [ -n "$branch" ]; then where="on ${branch}"; else where="detached at ${short}"; fi
  doctor_row ok "checkout" "$(as_root git -C "$TARGET" describe --tags --always 2>/dev/null || echo "$short"), ${where}"

  deleted="$(printf '%s\n' "$out" | sed -n 's/^.D //p; s/^D  //p' | sed '/^$/d')"
  changed="$(printf '%s\n' "$out" | grep -v -e '^.D ' -e '^D  ' | sed 's/^...//' | sed '/^$/d' || true)"
  if [ -n "$deleted" ]; then
    # shellcheck disable=SC2086  # the names are words
    doctor_row bad "missing files" "$(printf '%s\n' "$deleted" | grep -c .) tracked file(s) are gone: $(dc_list 4 $deleted)" \
      "sudo git -C ${TARGET} checkout -- .   # puts every one back"
  else
    doctor_row ok "missing files" "every file the version tracks is there"
  fi
  if [ -n "$changed" ]; then
    # shellcheck disable=SC2086  # the names are words
    doctor_row warn "working tree" "$(printf '%s\n' "$changed" | grep -c .) tracked file(s) differ from the version: $(dc_list 4 $changed). The next upgrade may refuse or overwrite them" \
      "git -C ${TARGET} diff   # to see; to throw the changes away: sudo git -C ${TARGET} checkout -- ."
  else
    doctor_row ok "working tree" "no tracked file has been changed here"
  fi

  rc=0
  out="$(as_root timeout 30 git -C "$TARGET" fsck --connectivity-only --no-dangling 2>&1)" || rc=$?
  if [ "$rc" = 124 ]; then
    doctor_row skip "git history" "the check took over 30 seconds and was left"
  elif [ "$rc" != 0 ]; then
    doctor_row bad "git history" "git found damaged or missing objects: $(dc_first "$out")" \
      "sudo git -C ${TARGET} fetch --tags origin   # often fills them in; otherwise unpack a fresh copy over this one"
  else
    doctor_row ok "git history" "no object is missing or damaged"
  fi

  url="$(as_root git -C "$TARGET" remote get-url origin 2>/dev/null || true)"
  if [ -z "$url" ]; then
    doctor_row warn "remote" "no remote called origin, so \`upgrade\` has nowhere to fetch from" \
      "sudo git -C ${TARGET} remote add origin git@github.com:atate911/FamilyDB.git"
  else
    case "$url" in
      *://*:*@*)
        doctor_row warn "remote" "its address carries a credential, which anyone who can read ${TARGET}/.git/config can use" \
          "sudo git -C ${TARGET} remote set-url origin https://github.com/OWNER/REPO.git   # and use a deploy key" ;;
      *) doctor_row ok "remote" "$url" ;;
    esac
    key="$(as_root git -C "$TARGET" config core.sshCommand 2>/dev/null || true)"
    keyfile="$(printf '%s' "$key" | sed -n 's/.*-i \([^ ]*\).*/\1/p')"
    if [ -n "$keyfile" ]; then
      if ! as_root test -f "$keyfile"; then
        doctor_row warn "deploy key" "the checkout fetches with ${keyfile}, which is not there, so \`upgrade\` cannot fetch" \
          "Make a new deploy key and add it under the repository's Settings, Deploy keys (docs/INSTALL.md)"
      elif dc_loose "$(as_root stat -c '%a' "$keyfile" 2>/dev/null || echo 600)" 077; then
        doctor_row warn "deploy key" "${keyfile} is readable by others, and ssh refuses a key like that" "sudo chmod 600 ${keyfile}"
      else
        doctor_row ok "deploy key" "${keyfile}, private"
      fi
    fi
    if [ "$DC_ONLINE" = 1 ]; then
      rc=0
      out="$(as_root timeout 20 git -C "$TARGET" ls-remote --exit-code origin HEAD 2>&1)" || rc=$?
      if [ "$rc" = 0 ]; then
        doctor_row ok "remote reachable" "origin answered"
      else
        doctor_row warn "remote reachable" "origin did not answer: $(dc_last "$out")" \
          "Check the deploy key, and that this machine can reach github.com on port 22 or 443"
      fi
    fi
  fi

  local target at
  target="$(pending_get target)"
  at="$(last_upgrade_get at)"
  if [ -n "$target" ]; then
    doctor_row warn "upgrade" "an upgrade to ${target} stopped part-way: the code moved, but its packages, migrations or the restart may not have run" \
      "sudo ${0} upgrade   # finishes it; or: sudo ${0} rescue rollback"
  elif [ -n "$at" ] && [ "$at" -gt 0 ] 2>/dev/null; then
    doctor_row ok "last upgrade" "$(ago $(( $(date +%s) - at ))): $(last_upgrade_get from_label) ${S_TO} $(last_upgrade_get to_label)"
  fi
}

# --- .env and the settings it holds ---------------------------------------------------------------

dc_config() {
  doctor_section "Config"
  local env="${TARGET}/.env" report issues="" worst=ok value bom crlf odd spaced quote dup
  as_root test -f "$env" || return 0
  report="$(as_root awk '
    NR == 1 && substr($0, 1, 3) == "\357\273\277" { bom = 1; $0 = substr($0, 4) }
    { if (sub(/\r$/, "")) crlf++ }
    /^[[:space:]]*(#|$)/ { next }
    {
      line = $0
      sub(/^[[:space:]]*export[[:space:]]+/, "", line)
      if (line !~ /^[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/) { odd = odd (odd == "" ? "" : ", ") NR; next }
      key = line; sub(/[[:space:]]*=.*/, "", key)
      if (line ~ /^[A-Za-z_][A-Za-z0-9_]*[[:space:]]+=/) spaced = spaced (spaced == "" ? "" : ", ") key
      val = line; sub(/^[^=]*=[[:space:]]*/, "", val)
      if (val ~ /^"/ && val !~ /^"([^"\\]|\\.)*"([[:space:]]*#.*)?$/) quote = quote (quote == "" ? "" : ", ") NR
      if (val ~ /^\047/ && val !~ /^\047[^\047]*\047([[:space:]]*#.*)?$/) quote = quote (quote == "" ? "" : ", ") NR
      if (key in seen && seen[key] != val) dup = dup (dup == "" ? "" : ", ") key
      seen[key] = val
    }
    END { print "bom=" bom + 0; print "crlf=" crlf + 0; print "odd=" odd; print "spaced=" spaced; print "quote=" quote; print "dup=" dup }
  ' "$env" 2>/dev/null || true)"
  bom="$(printf '%s\n' "$report" | sed -n 's/^bom=//p')"; crlf="$(printf '%s\n' "$report" | sed -n 's/^crlf=//p')"
  odd="$(printf '%s\n' "$report" | sed -n 's/^odd=//p')"; spaced="$(printf '%s\n' "$report" | sed -n 's/^spaced=//p')"
  quote="$(printf '%s\n' "$report" | sed -n 's/^quote=//p')"; dup="$(printf '%s\n' "$report" | sed -n 's/^dup=//p')"
  [ "${bom:-0}" = 0 ] || { issues="${issues}${issues:+; }a byte-order mark at the start hides the first option's name"; worst=bad; }
  [ -z "$odd" ] || { issues="${issues}${issues:+; }line ${odd} is not NAME=value, so it is ignored"; [ "$worst" = bad ] || worst=warn; }
  [ -z "$quote" ] || { issues="${issues}${issues:+; }an unclosed quote on line ${quote}"; [ "$worst" = bad ] || worst=warn; }
  [ -z "$spaced" ] || { issues="${issues}${issues:+; }spaces before the = in ${spaced}"; [ "$worst" = bad ] || worst=warn; }
  [ "${crlf:-0}" = 0 ] || { issues="${issues}${issues:+; }${crlf} line(s) end the Windows way (CR LF)"; [ "$worst" = bad ] || worst=warn; }
  if [ -n "$issues" ]; then
    doctor_row "$worst" ".env syntax" "$issues" "Open ${env} and correct it; for Windows line ends: sudo sed -i 's/\\r\$//' ${env}"
  else
    doctor_row ok ".env syntax" "every line is NAME=value"
  fi
  if [ -n "$dup" ]; then
    doctor_row warn "repeated options" "set twice with different values, and the last wins: ${dup}" "Delete the one you do not mean from ${env}"
  fi

  value="$(env_file_value WEB_PORT)"
  if [ -n "$value" ]; then
    case "$value" in
      *[!0-9]*) doctor_row bad "web port" "WEB_PORT is \"${value}\", not a number, so the page cannot bind" "sudo ${0} port 8080   # or any number from 1025 to 65535" ;;
      *) if [ "$value" -lt 1025 ] || [ "$value" -gt 65535 ]; then
           doctor_row bad "web port" "WEB_PORT=${value}: the service has no right to a port under 1025, and none is above 65535" "sudo ${0} port random"
         else
           doctor_row ok "web port" "${value}"
         fi ;;
    esac
  fi
  value="$(env_file_value WEB_PUBLIC_PORT)"
  case "$value" in
    '') ;;
    *[!0-9]*) doctor_row bad "public port" "WEB_PUBLIC_PORT is \"${value}\", not a number" "sudo ${0} https --port 443" ;;
    *) if [ "$value" -lt 1 ] || [ "$value" -gt 65535 ]; then
         doctor_row bad "public port" "WEB_PUBLIC_PORT=${value} is not a port" "sudo ${0} https --port 443"
       fi ;;
  esac
  value="$(env_file_value WEB_ENABLED)"
  if [ -n "$value" ] && ! dc_truthy "$value"; then
    case "$(printf '%s' "$value" | tr 'A-Z' 'a-z')" in
      false|0|no|off|f|n) doctor_row warn "web page" "WEB_ENABLED=${value}: the page is switched off, so there is nothing to open or sign in to" "sudo ${0} rescue locked-out   # turns it on and restarts" ;;
      *) doctor_row bad "web page" "WEB_ENABLED=\"${value}\" is not true or false, so the settings will not load" "Set WEB_ENABLED=true in ${env}" ;;
    esac
  fi
}

# --- Python and the packages ----------------------------------------------------------------------

dc_python() {
  doctor_section "Python"
  local py="${TARGET}/.venv/bin/python" version missing differ
  if [ "$DOCKER_MODE" = 1 ]; then
    if as_root docker image inspect familydb:local >/dev/null 2>&1; then
      doctor_row ok "image" "familydb:local is built ($(as_root docker image inspect -f '{{.Created}}' familydb:local 2>/dev/null | cut -c1-10))"
    else
      doctor_row bad "image" "no image called familydb:local, so the container cannot start" \
        "sudo docker compose --project-directory ${TARGET} build"
    fi
    return 0
  fi
  if ! [ -x "$py" ]; then
    doctor_row bad "interpreter" "no Python at ${py}, so the service has nothing to run" \
      "sudo ${0} rescue wont-start   # builds it again from the lock file"
    return 0
  fi
  dc_try "$py" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])'
  if [ "$_DC_RC" != 0 ]; then
    doctor_row bad "interpreter" "${py} does not run: $(dc_last "$_DC_OUT"). The system Python it was built on is probably gone" \
      "sudo ${0} rescue wont-start   # builds it again"
    return 0
  fi
  version="$_DC_OUT"
  case "$version" in
    3.1[1-9].*|3.[2-9][0-9].*|[4-9].*) doctor_row ok "interpreter" "Python ${version}" ;;
    *) doctor_row bad "interpreter" "Python ${version}, and FamilyDB needs 3.11 or newer" "sudo ${0} rescue wont-start" ;;
  esac
  if have uv || [ -x /usr/local/bin/uv ]; then
    doctor_row ok "uv" "$(command -v uv || echo /usr/local/bin/uv)"
  else
    doctor_row warn "uv" "not installed, so \`upgrade\` cannot install packages" \
      "curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh"
  fi

  dc_try "$py" - "$TARGET" <<'PY'
import importlib.metadata as md
import re
import sys
import tomllib

root = sys.argv[1]
with open(root + "/pyproject.toml", "rb") as handle:
    wanted = [re.split(r"[<>=!~;\[ ]", d, maxsplit=1)[0].strip() for d in tomllib.load(handle)["project"]["dependencies"]]
locked = {}
try:
    with open(root + "/uv.lock", "rb") as handle:
        for package in tomllib.load(handle).get("package", []):
            locked[package["name"].lower().replace("_", "-")] = package.get("version")
except OSError:
    pass
missing, differ = [], []
for name in wanted:
    try:
        have = md.version(name)
    except md.PackageNotFoundError:
        missing.append(name)
        continue
    key = name.lower().replace("_", "-")
    if locked.get(key) and locked[key] != have:
        differ.append("%s %s (lock has %s)" % (name, have, locked[key]))
print("MISSING " + ", ".join(missing))
print("DIFFER " + "; ".join(differ))
PY
  if [ "$_DC_RC" != 0 ]; then
    doctor_row warn "packages" "could not be listed: $(dc_last "$_DC_OUT")"
  else
    missing="$(printf '%s\n' "$_DC_OUT" | sed -n 's/^MISSING //p')"; differ="$(printf '%s\n' "$_DC_OUT" | sed -n 's/^DIFFER //p')"
    if [ -n "$missing" ]; then
      doctor_row bad "packages" "not installed: ${missing}; the program fails at import" \
        "sudo uv sync --frozen --no-dev --project ${TARGET}   # or: sudo ${0} rescue wont-start"
    elif [ -n "$differ" ]; then
      doctor_row warn "packages" "differ from uv.lock: ${differ}" "sudo uv sync --frozen --no-dev --project ${TARGET}"
    else
      doctor_row ok "packages" "every dependency is installed at the version uv.lock names"
    fi
  fi

  if [ -x "${TARGET}/.venv/bin/familydb" ]; then
    dc_try env -C "$TARGET" "${TARGET}/.venv/bin/familydb" --help
    if [ "$_DC_RC" != 0 ]; then
      doctor_row bad "program" "\`familydb --help\` fails: $(dc_last "$_DC_OUT")" \
        "sudo ${0} rescue wont-start   # or, if an upgrade just broke it: sudo ${0} rescue rollback"
    else
      doctor_row ok "program" "familydb loads and answers --help"
    fi
  else
    doctor_row bad "program" "no ${TARGET}/.venv/bin/familydb, which is what the service runs" "sudo ${0} rescue wont-start"
  fi
}

# --- the database file, read without the program --------------------------------------------------

dc_database() {
  doctor_section "Database file"
  local db="$DC_DB" owner mode size py suffix path info quick version jmode wal newest why
  if [ ! -f "$db" ]; then
    doctor_row bad "database file" "none at ${db}" \
      "sudo ${0} restart   # a first start makes one; to bring one back: sudo ${0} restore FILE"
    return 0
  fi
  owner="$(stat -c '%U' "$db" 2>/dev/null || echo '?')"; mode="$(stat -c '%a' "$db" 2>/dev/null || echo '?')"
  size="$(du -h "$db" 2>/dev/null | cut -f1)"
  if [ "$DOCKER_MODE" = 1 ]; then
    doctor_row ok "database file" "${db}, ${size}"
  elif [ "$owner" != "$SERVICE_USER" ]; then
    doctor_row bad "database file" "owned by ${owner}, not ${SERVICE_USER}: a root-run command probably made or changed it, and the service can no longer write to it" \
      "sudo chown ${SERVICE_USER}:${SERVICE_USER} ${db}*"
  elif dc_loose "$mode" 077; then
    doctor_row warn "database file" "mode ${mode}: other users on this machine can read every message" "sudo chmod 600 ${db}*"
  else
    doctor_row ok "database file" "${db}, ${size}, private to ${owner}"
  fi
  for suffix in -wal -shm -journal; do
    path="${db}${suffix}"
    [ -e "$path" ] || continue
    owner="$(stat -c '%U' "$path" 2>/dev/null || echo '?')"
    if [ "$DOCKER_MODE" = 0 ] && [ "$owner" != "$SERVICE_USER" ]; then
      doctor_row bad "journal files" "${path##*/} belongs to ${owner}: SQLite will say \"attempt to write a readonly database\" until it is the service's" \
        "sudo chown ${SERVICE_USER}:${SERVICE_USER} ${db}*"
      break
    fi
  done
  wal="$(stat -c %s "${db}-wal" 2>/dev/null || echo 0)"
  if [ "$wal" -gt 268435456 ]; then
    doctor_row warn "journal files" "the write-ahead log is $((wal / 1048576)) MB: it is not being folded back into the database" \
      "sudo ${0} restart   # a clean stop does it"
  fi

  py="${TARGET}/.venv/bin/python"; [ -x "$py" ] || py="$(command -v python3 || true)"
  if [ -z "$py" ]; then
    doctor_row skip "integrity" "no Python to read the file with"
    return 0
  fi
  info="$(as_root "$py" - "$db" <<'PY' 2>&1 || true
import sqlite3
import sys
from pathlib import Path

try:
    conn = sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
    quick = [row[0] for row in conn.execute("pragma quick_check").fetchall()]
    version = conn.execute("select max(version) from schema_version").fetchone()[0] or 0
    mode = conn.execute("pragma journal_mode").fetchone()[0]
    print("QUICK", "ok" if quick == ["ok"] else quick[0])
    print("VERSION", version)
    print("JOURNAL", mode)
except Exception as exc:
    print("ERROR", str(exc).splitlines()[0] if str(exc) else type(exc).__name__)
PY
)"
  quick="$(printf '%s\n' "$info" | sed -n 's/^QUICK //p' | head -1)"
  version="$(printf '%s\n' "$info" | sed -n 's/^VERSION //p' | head -1)"
  jmode="$(printf '%s\n' "$info" | sed -n 's/^JOURNAL //p' | head -1)"
  if [ -z "$quick" ]; then
    why="$(printf '%s\n' "$info" | sed -n 's/^ERROR //p' | head -1)"
    case "$why" in
      *locked*) doctor_row warn "integrity" "the database is locked right now, so it could not be read: something is holding a write open" "sudo ${0} restart" ;;
      *) doctor_row bad "integrity" "SQLite cannot read it: ${why:-$(dc_first "$info")}" \
           "sudo ${0} rescue database   # checks the backups and offers to restore the newest sound one" ;;
    esac
    return 0
  fi
  if [ "$quick" = ok ]; then
    doctor_row ok "integrity" "SQLite's own check finds the file sound (${size}, ${jmode:-?} journal)"
  else
    doctor_row bad "integrity" "SQLite found damage: ${quick}" "sudo ${0} rescue database"
  fi
  newest="$(newest_migration)"
  case "$version$newest" in
    ''|*[!0-9]*) ;;
    *) if [ -z "$version" ] || [ -z "$newest" ]; then
         :
       elif [ "$version" -lt "$newest" ]; then
         doctor_row bad "schema" "the database is at migration ${version} and this code has up to ${newest}: the program stops at start" \
           "cd ${TARGET} && sudo -u ${SERVICE_USER} ${FAMILYDB} db migrate"
       elif [ "$version" -gt "$newest" ]; then
         doctor_row warn "schema" "the database is at migration ${version}, newer than this code's ${newest}: an older checkout is on a newer database" \
           "sudo ${0} upgrade   # or, if it was a rollback: sudo ${0} rescue rollback"
       else
         doctor_row ok "schema" "up to date at migration ${version}"
       fi ;;
  esac
}

# --- the service ----------------------------------------------------------------------------------

dc_service() {
  doctor_section "Service"
  if [ "$DOCKER_MODE" = 1 ]; then
    dc_docker
    return 0
  fi
  if ! service_installed; then
    doctor_row skip "systemd unit" "none at ${SERVICE_UNIT}: it is started by hand"
    return 0
  fi
  if ! have systemctl; then
    doctor_row skip "systemd unit" "a unit is installed but systemctl is not here"
    return 0
  fi
  local user wd exe envf rw home problems="" reload active sub enabled since restarts result status allowed p
  user="$(dc_unit_value User)"; wd="$(dc_unit_value WorkingDirectory)"
  exe="$(dc_unit_value ExecStart | awk '{print $1}' | sed 's/^[-@+!:]*//')"
  envf="$(dc_unit_value EnvironmentFile)"; rw="$(dc_unit_value ReadWritePaths)"; home="$(dc_unit_value ProtectHome)"
  if [ -n "$user" ] && ! id "$user" >/dev/null 2>&1; then
    problems="${problems}${problems:+; }it runs as ${user}, who does not exist"
  fi
  if [ -n "$wd" ] && [ ! -d "$wd" ]; then problems="${problems}${problems:+; }its folder ${wd} is gone"; fi
  if [ -n "$exe" ] && [ ! -x "$exe" ]; then problems="${problems}${problems:+; }it starts ${exe}, which is missing or not executable"; fi
  case "$envf" in
    ''|-*) ;;
    *) as_root test -f "$envf" || problems="${problems}${problems:+; }its settings file ${envf} is missing" ;;
  esac
  case "$(dc_unit_value ProtectSystem)" in
    strict|full)
      if [ -n "$rw" ] && [ -n "$DC_DB" ]; then
        allowed=0
        for p in $rw; do case "$DC_DB" in "${p%/}"/*|"$p") allowed=1 ;; esac; done
        [ "$allowed" = 1 ] || problems="${problems}${problems:+; }its sandbox makes everything read-only except ${rw}, and the database is at ${DC_DB}"
      fi ;;
  esac
  case "$TARGET" in
    /home/*|/root/*) [ "$home" != true ] || problems="${problems}${problems:+; }ProtectHome=true hides ${TARGET} from the service" ;;
  esac
  if [ -n "$problems" ]; then
    doctor_row bad "unit file" "${problems}" \
      "Compare ${SERVICE_UNIT} with ${TARGET}/deploy/familydb.service; then: sudo systemctl daemon-reload && sudo systemctl restart familydb"
  else
    doctor_row ok "unit file" "${SERVICE_UNIT}: runs ${exe:-?} as ${user:-?} in ${wd:-?}"
  fi
  if [ -n "$user" ] && [ "$user" != "$SERVICE_USER" ]; then
    doctor_row warn "unit account" "the unit runs as ${user}, but this check looked at ${SERVICE_USER}'s files" "Run it again with: ${0} check --user ${user}"
  fi
  reload="$(as_root systemctl show familydb -p NeedDaemonReload --value 2>/dev/null || true)"
  if [ "$reload" = yes ]; then
    doctor_row warn "unit loaded" "the unit file changed on disk and systemd has not read it yet, so it is running the old one" "sudo systemctl daemon-reload && sudo systemctl restart familydb"
  fi
  if [ -f "${TARGET}/deploy/familydb.service" ]; then
    local shipped installed
    shipped="$(grep -E '^(Restart|ProtectSystem|NoNewPrivileges|UMask)=' "${TARGET}/deploy/familydb.service" | sort)"
    installed="$(grep -E '^(Restart|ProtectSystem|NoNewPrivileges|UMask)=' "$SERVICE_UNIT" | sort)"
    [ "$shipped" = "$installed" ] || doctor_row warn "unit version" "the unit differs from the one this version ships (restart, sandbox or umask)" \
      "diff ${TARGET}/deploy/familydb.service ${SERVICE_UNIT}   # then copy it over and daemon-reload"
  fi

  active="$(systemctl is-active familydb 2>/dev/null || true)"; active="${active:-unknown}"
  sub="$(as_root systemctl show familydb -p SubState --value 2>/dev/null || true)"
  enabled="$(systemctl is-enabled familydb 2>/dev/null || true)"; enabled="${enabled:-unknown}"
  since="$(as_root systemctl show familydb -p ActiveEnterTimestamp --value 2>/dev/null || true)"
  restarts="$(as_root systemctl show familydb -p NRestarts --value 2>/dev/null || true)"
  result="$(as_root systemctl show familydb -p Result --value 2>/dev/null || true)"
  status="$(as_root systemctl show familydb -p ExecMainStatus --value 2>/dev/null || true)"
  if [ "$active" = active ]; then
    local up=""
    since="$(date -d "$since" +%s 2>/dev/null || true)"
    [ -z "$since" ] || up=", up $(fmt_secs $(( $(date +%s) - since )))"
    if [ "$enabled" = enabled ]; then
      doctor_row ok "service" "running${up}; starts at boot"
    else
      doctor_row warn "service" "running${up}, but it is ${enabled} at boot, so it will not come back after a restart of the machine" "sudo systemctl enable familydb"
    fi
  else
    doctor_row bad "service" "${active}${sub:+ (${sub})}: nothing is serving, and no reminder or message is going out" \
      "sudo journalctl -u familydb -n 50 --no-pager   # why; then: sudo ${0} restart"
  fi
  case "$restarts" in
    ''|*[!0-9]*) ;;
    *) if [ "$restarts" -ge 5 ]; then
         doctor_row bad "restarts" "${restarts} automatic restarts: it crashes on start and systemd keeps trying" \
           "sudo journalctl -u familydb -n 50 --no-pager   # the first error line names the cause"
       elif [ "$restarts" -ge 1 ]; then
         doctor_row warn "restarts" "${restarts} automatic restart(s) since it was last started" "sudo journalctl -u familydb -n 50 --no-pager"
       else
         doctor_row ok "restarts" "none since it was last started"
       fi ;;
  esac
  case "$result" in
    ''|success) ;;
    oom-kill) doctor_row bad "last exit" "the kernel killed it for want of memory, and it will again under the same load" "free -h; sudo journalctl -k | grep -i 'killed process'   # then add swap or memory" ;;
    start-limit-hit) doctor_row bad "last exit" "systemd stopped trying after too many failed starts" "sudo systemctl reset-failed familydb && sudo ${0} restart" ;;
    timeout) doctor_row warn "last exit" "it was killed for not stopping in time" "sudo journalctl -u familydb -n 100 --no-pager" ;;
    exit-code) doctor_row bad "last exit" "it exited with status ${status:-?}: a start-up error is the usual cause" "sudo journalctl -u familydb -n 50 --no-pager" ;;
    *) doctor_row warn "last exit" "${result}" "sudo journalctl -u familydb -n 50 --no-pager" ;;
  esac
  if [ "$active" = active ] && have docker && as_root docker ps --format '{{.Names}}' 2>/dev/null | grep -qi familydb; then
    doctor_row bad "double start" "the service and a Docker container are both running FamilyDB: two schedulers answer every message and fight over the database" \
      "Stop one: sudo docker compose --project-directory ${TARGET} down   # or: sudo systemctl disable --now familydb"
  fi
}

dc_docker() {
  if ! have docker; then
    doctor_row bad "docker" "this install runs in Docker, and docker is not installed" "sudo ${0} rescue wont-start"
    return 0
  fi
  local out rc=0 listing svc state detail id restarts oom health name
  as_root timeout 10 docker info >/dev/null 2>&1 || rc=$?
  if [ "$rc" != 0 ]; then
    doctor_row bad "docker" "the Docker daemon does not answer" "sudo systemctl start docker && sudo systemctl enable docker"
    return 0
  fi
  rc=0
  out="$(as_root docker compose --project-directory "$TARGET" config -q 2>&1)" || rc=$?
  if [ "$rc" != 0 ]; then
    doctor_row bad "compose file" "Docker cannot read the setup: $(dc_first "$out")" \
      "Fix the line it names in ${TARGET}/docker-compose.yml or .env (a bad quote in .env is the usual cause)"
  else
    doctor_row ok "compose file" "docker-compose.yml and .env read cleanly"
  fi
  listing="$(as_root docker compose --project-directory "$TARGET" ps -a --format '{{.Service}}|{{.State}}|{{.Status}}' 2>/dev/null || true)"
  if [ -z "$listing" ]; then
    doctor_row bad "service" "no container exists for it" "sudo docker compose --project-directory ${TARGET} up -d"
    return 0
  fi
  while IFS='|' read -r svc state detail; do
    [ -n "$svc" ] || continue
    id="$(as_root docker compose --project-directory "$TARGET" ps -aq "$svc" 2>/dev/null | head -1)"
    restarts="$(as_root docker inspect -f '{{.RestartCount}}' "$id" 2>/dev/null || echo 0)"
    oom="$(as_root docker inspect -f '{{.State.OOMKilled}}' "$id" 2>/dev/null || echo false)"
    health="$(as_root docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$id" 2>/dev/null || true)"
    name="container ${svc}"
    [ "$svc" != bot ] || name="service"
    if [ "$state" != running ]; then
      doctor_row bad "$name" "${state}, ${detail}" "sudo docker compose --project-directory ${TARGET} logs --tail 50 ${svc}   # why; then: sudo ${0} restart"
    elif [ "$oom" = true ]; then
      doctor_row bad "$name" "running, but the kernel killed it for memory earlier" "free -h   # then add swap or memory"
    elif [ "$health" = unhealthy ]; then
      doctor_row bad "$name" "running, but Docker's own health check says it is unwell" "sudo docker compose --project-directory ${TARGET} logs --tail 50 ${svc}"
    elif [ "${restarts:-0}" -ge 3 ] 2>/dev/null; then
      doctor_row warn "$name" "running, restarted ${restarts} times: it crashes and Docker brings it back" "sudo docker compose --project-directory ${TARGET} logs --tail 50 ${svc}"
    else
      doctor_row ok "$name" "${detail}"
    fi
  done <<<"$listing"
  if have systemctl && systemctl is-active --quiet familydb 2>/dev/null; then
    doctor_row bad "double start" "a systemd service called familydb is also running, beside the containers" "sudo systemctl disable --now familydb"
  fi
}

# --- the web server: the page, and what is in front of it -----------------------------------------

dc_web() {
  doctor_section "Web server"
  # dc_config said so when the page is off; there is nothing to ask of it.
  dc_truthy "$(env_file_value WEB_ENABLED)" || return 0
  local holder name code said rc=0 type
  if have ss; then
    holder="$(as_root ss -lntp 2>/dev/null | awk -v p=":${DC_PORT}" '$4 ~ p"$" {print; exit}' || true)"
    if [ -z "$holder" ]; then
      doctor_row bad "listening" "nothing listens on port ${DC_PORT}, so no browser can reach the page" \
        "sudo ${0} restart   # and see the Service section above for why it is not up"
    else
      name="$(printf '%s' "$holder" | sed -n 's/.*users:(("\([^"]*\)".*/\1/p')"
      case "${name:-python}" in
        python*|familydb*|waitress*|docker-proxy|com.docker*) doctor_row ok "listening" "port ${DC_PORT}${name:+, held by ${name}}" ;;
        *) doctor_row bad "listening" "port ${DC_PORT} is held by ${name}, not by FamilyDB: whatever a browser reaches there is not the page" \
             "sudo ss -lntp | grep :${DC_PORT}   # then stop it, or move FamilyDB: sudo ${0} port random" ;;
      esac
    fi
  fi
  if ! have curl; then
    doctor_row skip "page" "curl is not installed, so the page was not asked"
    return 0
  fi
  said="$(page_health)" || rc=$?
  case "$rc" in
    0) doctor_row ok "page" "/healthz answers at ${DC_WEB}: the database answers and the scheduler is ticking" ;;
    1) doctor_row bad "page" "${said}" "sudo ${0} logs   # what it says; then: sudo ${0} restart" ;;
  esac
  case "$said" in "nothing answers"*) return 0 ;; esac
  dc_http /
  code="$DC_CODE"
  type="$(dc_header content-type)"
  case "$code" in
    200|301|302|303|307|308)
      if [ "$code" = 200 ] && [ -n "$DC_BODY" ] && ! printf '%s' "$DC_BODY" | grep -qi '<html'; then
        doctor_row bad "sign-in page" "answers 200 but not with a page: ${type:-no content type}" "sudo ${0} logs"
      else
        doctor_row ok "sign-in page" "the front page answers ${code} and is drawn"
      fi ;;
    000) doctor_row skip "sign-in page" "no answer within 5 seconds" ;;
    5??) doctor_row bad "sign-in page" "answers ${code}: the page crashes when it is drawn. /healthz draws nothing, so it can look well beside this" \
           "sudo ${0} logs   # the traceback names the file; if an upgrade just ran: sudo ${0} rescue rollback" ;;
    *) doctor_row warn "sign-in page" "answers ${code} to the front page" "sudo ${0} logs" ;;
  esac
  [ "$code" != 000 ] || return 0
  if [ -z "$(dc_header content-security-policy)" ]; then
    doctor_row warn "page headers" "no content-security-policy: either another program answers on port ${DC_PORT} or something strips it" \
      "curl -sI ${DC_WEB}/ | head -20"
  else
    doctor_row ok "page headers" "content-security-policy and the other protections are sent"
  fi
  dc_http /static/style.css
  code="$DC_CODE"
  type="$(dc_header content-type)"
  case "$code" in
    200) case "$type" in
           text/css*) doctor_row ok "styles" "style.css is served" ;;
           *) doctor_row bad "styles" "style.css comes back as ${type:-nothing}, not CSS: the page shows as bare text" "sudo ${0} logs" ;;
         esac ;;
    404) doctor_row bad "styles" "style.css is not found: the page would appear without any layout" \
           "sudo git -C ${TARGET} checkout -- src/familydb/web/static   # puts the static files back" ;;
    000) ;;
    *) doctor_row bad "styles" "style.css answers ${code}" "sudo ${0} logs" ;;
  esac
}

dc_https() {
  local site port ip days end issuer addr closed rules cert out rc=0 upstream code
  site="$(env_file_value WEB_DOMAIN)"
  if [ -z "$site" ] && ! have caddy && [ ! -f /etc/caddy/Caddyfile ] && [ ! -d "${TARGET}/caddy" ]; then
    return 0
  fi
  doctor_section "HTTPS"
  port="$(env_file_value WEB_PUBLIC_PORT)"; port="${port:-443}"
  if [ -z "$site" ]; then
    doctor_row warn "address" "Caddy is installed but no WEB_DOMAIN is set in .env" "sudo ${0} https"
    return 0
  fi
  case "$site" in
    *[!0-9.]*)
      addr="$(getent ahostsv4 "$site" 2>/dev/null | awk 'NR==1 {print $1}' || true)"
      if [ -z "$addr" ]; then
        doctor_row bad "dns" "${site} does not resolve from this machine, so no certificate can be obtained and nobody can reach it" \
          "Add an A record for ${site} pointing at this server (see: sudo ${0} https)"
      else
        ip="$(this_address 2>/dev/null || true)"
        if [ -n "$ip" ] && [ "$addr" != "$ip" ]; then
          doctor_row warn "dns" "${site} resolves to ${addr}, and this server's address is ${ip}: right behind a proxy or NAT, wrong otherwise" \
            "Point the A record at ${ip} (or ignore this if a proxy or NAT is meant to sit between)"
        else
          doctor_row ok "dns" "${site} resolves to ${addr}"
        fi
      fi ;;
    *) doctor_row ok "address" "${site} (an address, not a name; Caddy makes its own certificate)" ;;
  esac
  if [ "$DOCKER_MODE" = 0 ]; then
    if ! have caddy; then
      doctor_row bad "caddy" "a domain is set but Caddy is not installed, so nothing serves HTTPS" "sudo ${0} https"
      return 0
    fi
    if have systemctl && systemctl is-active --quiet caddy 2>/dev/null; then
      doctor_row ok "caddy" "running"
    else
      doctor_row bad "caddy" "not running, so nobody can open the page from outside" \
        "sudo systemctl restart caddy; sudo journalctl -u caddy -n 30 --no-pager   # why"
    fi
    if [ -f /etc/caddy/Caddyfile ]; then
      out="$(as_root caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1)" || rc=$?
      if [ "$rc" != 0 ]; then
        doctor_row bad "caddyfile" "Caddy rejects /etc/caddy/Caddyfile: $(dc_last "$out")" "sudo ${0} https ${site}   # writes it again"
      else
        upstream="$(grep -oE 'reverse_proxy[[:space:]]+[^[:space:]]+' /etc/caddy/Caddyfile | head -1 | awk '{print $2}')"
        if [ -n "$upstream" ] && [ "${upstream##*:}" != "$DC_PORT" ]; then
          doctor_row bad "caddyfile" "Caddy passes the page on to ${upstream}, but FamilyDB is on port ${DC_PORT}: every visitor gets a bad gateway" \
            "sudo ${0} port ${DC_PORT}   # points Caddy at it again"
        else
          doctor_row ok "caddyfile" "valid, passing the page on to ${upstream:-the right port}"
        fi
      fi
    else
      doctor_row bad "caddyfile" "no /etc/caddy/Caddyfile" "sudo ${0} https ${site}"
    fi
  else
    if as_root docker compose --project-directory "$TARGET" ps --format '{{.Service}}' 2>/dev/null | grep -qx caddy; then
      doctor_row ok "caddy" "the container is up"
    else
      doctor_row bad "caddy" "the Caddy container is not running" "sudo docker compose --project-directory ${TARGET} --profile tls up -d"
    fi
  fi
  if have ss; then
    if as_root ss -lnt 2>/dev/null | awk -v p=":${port}" '$4 ~ p"$" {found = 1} END {exit !found}'; then
      doctor_row ok "https port" "something listens on ${port}"
    else
      doctor_row bad "https port" "nothing listens on ${port}, so the address cannot open" "sudo systemctl restart caddy"
    fi
  fi
  if have openssl; then
    cert="$(echo | timeout 8 openssl s_client -connect "127.0.0.1:${port}" -servername "$site" 2>/dev/null | openssl x509 -noout -enddate -issuer 2>/dev/null || true)"
    if [ -z "$cert" ]; then
      doctor_row bad "certificate" "none is served on port ${port}: Caddy could not get one. Port 80 shut, or the name pointing elsewhere, are the usual causes" \
        "sudo journalctl -u caddy -n 20 --no-pager | grep -i -e error -e acme"
    else
      end="$(printf '%s\n' "$cert" | sed -n 's/^notAfter=//p')"
      issuer="$(printf '%s\n' "$cert" | sed -n 's/^issuer=.*CN *= *//p' | head -1)"
      days="$(( ($(date -d "$end" +%s 2>/dev/null || echo 0) - $(date +%s)) / 86400 ))"
      if [ "$days" -lt 0 ]; then
        doctor_row bad "certificate" "expired ${end}: browsers refuse the page" "sudo systemctl restart caddy; sudo journalctl -u caddy -n 20 --no-pager"
      elif [ "$days" -lt 14 ]; then
        doctor_row warn "certificate" "expires in ${days} days (${issuer:-unknown issuer}), and Caddy renews well before that: it has not" "sudo journalctl -u caddy -n 30 --no-pager | grep -i -e error -e renew"
      else
        doctor_row ok "certificate" "valid for ${days} more days${issuer:+ (${issuer})}"
      fi
    fi
  fi
  if have curl; then
    code="$(curl -sk --max-time 6 -o /dev/null -w '%{http_code}' --resolve "${site}:${port}:127.0.0.1" "https://${site}:${port}/healthz" 2>/dev/null || true)"
    case "$code" in
      200) doctor_row ok "through https" "https://${site}:${port}/healthz answers from this machine" ;;
      000|'') doctor_row bad "through https" "nothing answered https://${site}:${port}/healthz from this machine" "sudo systemctl restart caddy; sudo ${0} logs" ;;
      502|503|504) doctor_row bad "through https" "Caddy is up but the page behind it is not (${code})" "sudo ${0} restart" ;;
      *) doctor_row warn "through https" "answers ${code}" "sudo ${0} logs" ;;
    esac
  fi
  if have ufw; then
    rules="$(as_root ufw status 2>/dev/null || true)"
    case "$rules" in
      *"Status: active"*)
        closed=""
        printf '%s\n' "$rules" | grep -qE "^80(/tcp)?[[:space:]]+ALLOW" || closed="80"
        printf '%s\n' "$rules" | grep -qE "^${port}(/tcp)?[[:space:]]+ALLOW" || closed="${closed}${closed:+ and }${port}"
        if [ -n "$closed" ]; then
          doctor_row warn "firewall" "ufw is on and does not allow port ${closed}" "sudo ufw allow ${closed%% *}/tcp   # and any other port named"
        else
          doctor_row ok "firewall" "ufw allows 80 and ${port}"
        fi ;;
      *) doctor_row skip "firewall" "ufw is off; a provider's own firewall may still apply" ;;
    esac
  fi
}

# --- the host -------------------------------------------------------------------------------------

dc_host() {
  doctor_section "Host"
  local line total_mb used_mb free_mb pct inode opts mem_total avail swap tmp count="" latest=""
  line="$(df -Pm "$TARGET" 2>/dev/null | awk 'NR==2 {print $2, $3, $4}')"
  if [ -n "$line" ]; then
    read -r total_mb used_mb free_mb <<<"$line"
    pct=$((100 * used_mb / (total_mb > 0 ? total_mb : 1)))
    if [ "$free_mb" -lt 100 ]; then
      doctor_row bad "disk space" "$(dc_meter "$used_mb" "$total_mb") ${pct}% used, only $(dc_mb "$free_mb") free: writes are failing or about to" \
        "sudo ${0} rescue space"
    elif [ "$free_mb" -lt 500 ]; then
      doctor_row warn "disk space" "$(dc_meter "$used_mb" "$total_mb") ${pct}% used, $(dc_mb "$free_mb") free" "sudo ${0} rescue space"
    else
      doctor_row ok "disk space" "$(dc_meter "$used_mb" "$total_mb") ${pct}% used, $(dc_mb "$free_mb") free of $(dc_mb "$total_mb")"
    fi
  fi
  inode="$(df -Pi "$TARGET" 2>/dev/null | awk 'NR==2 {gsub("%", "", $5); print $5}')"
  case "$inode" in
    ''|*[!0-9]*) ;;
    *) if [ "$inode" -ge 98 ]; then
         doctor_row bad "inodes" "${inode}% of the file slots are used: nothing new can be created even with free space" "sudo ${0} rescue space"
       elif [ "$inode" -ge 90 ]; then
         doctor_row warn "inodes" "${inode}% of the file slots are used" "sudo ${0} rescue space"
       fi ;;
  esac
  opts="$(findmnt -no OPTIONS -T "$TARGET" 2>/dev/null || true)"
  case ",${opts}," in
    *,ro,*) doctor_row bad "file system" "${TARGET} is on a read-only file system, which is what the kernel does after a disk error" \
              "sudo dmesg | tail -20   # then remount or reboot: sudo mount -o remount,rw /" ;;
  esac
  mem_total="$(awk '/^MemTotal:/ {print int($2 / 1024)}' "${FAMILYDB_MEMINFO:-/proc/meminfo}" 2>/dev/null || true)"
  avail="$(awk '/^MemAvailable:/ {print int($2 / 1024)}' "${FAMILYDB_MEMINFO:-/proc/meminfo}" 2>/dev/null || true)"
  swap="$(awk '/^SwapTotal:/ {print int($2 / 1024)}' "${FAMILYDB_MEMINFO:-/proc/meminfo}" 2>/dev/null || true)"
  if [ -n "$mem_total" ] && [ -n "$avail" ]; then
    if [ "$avail" -lt 100 ]; then
      doctor_row warn "memory" "$(dc_meter $((mem_total - avail)) "$mem_total") only ${avail} MB of ${mem_total} MB is free: the kernel will kill something" \
        "free -h; ps aux --sort=-%mem | head -5   # then add swap"
    elif [ "$mem_total" -lt 1000 ] && [ "${swap:-0}" -eq 0 ]; then
      doctor_row warn "memory" "$(dc_meter $((mem_total - avail)) "$mem_total") ${mem_total} MB and no swap: an install or upgrade that ends with only \"Killed\" ran out of memory" \
        "sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
    else
      doctor_row ok "memory" "$(dc_meter $((mem_total - avail)) "$mem_total") ${avail} MB free of ${mem_total} MB${swap:+, swap ${swap} MB}"
    fi
  fi
  if have timedatectl; then
    case "$(timedatectl show -p NTPSynchronized --value 2>/dev/null || true)" in
      yes) doctor_row ok "clock" "synchronised with a time server" ;;
      no) doctor_row warn "clock" "not synchronised: certificates, reminders and the digest all depend on the time being right" "sudo timedatectl set-ntp true" ;;
    esac
  fi
  tmp="${TMPDIR:-/tmp}"
  dc_try sh -c 'f=$(mktemp "$1/.doctor.XXXXXX") && rm -f "$f"' sh "$tmp"
  if [ "$_DC_RC" != 0 ] && [ "$_DC_ASIS" = 0 ]; then
    doctor_row bad "temp folder" "${SERVICE_USER} cannot write in ${tmp}: $(dc_last "$_DC_OUT")" "ls -ld ${tmp}; sudo chmod 1777 ${tmp}"
  fi
  if [ "$DOCKER_MODE" = 1 ]; then
    count="$(as_root docker compose --project-directory "$TARGET" logs --since 24h bot 2>/dev/null | grep -c -E 'ERROR|Traceback|CRITICAL' || true)"
    latest="$(as_root docker compose --project-directory "$TARGET" logs --since 24h bot 2>/dev/null | grep -E 'ERROR|Traceback|CRITICAL' | tail -1 | cut -c1-140 || true)"
  elif service_installed && have journalctl; then
    count="$(as_root journalctl -u familydb --since '24 hours ago' -p err -q --no-pager 2>/dev/null | grep -c . || true)"
    latest="$(as_root journalctl -u familydb --since '24 hours ago' -p err -q --no-pager 2>/dev/null | tail -1 | cut -c1-140 || true)"
  fi
  if [ -n "$count" ]; then
    if [ "$count" -gt 0 ] 2>/dev/null; then
      doctor_row warn "log" "${count} error line(s) in the last day; the latest: ${latest}" "sudo ${0} logs"
    else
      doctor_row ok "log" "no errors logged in the last day"
    fi
  fi
}

dc_backups() {
  doctor_section "Backups"
  local newest epoch age cronline
  newest="$(as_root find "$BACKUP_DIR" -maxdepth 1 -name 'familydb-*.sqlite3' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)"
  if [ -n "$newest" ]; then
    epoch="$(as_root stat -c %Y "$newest" 2>/dev/null || echo 0)"
    age=$(( $(date +%s) - epoch ))
    if [ "$age" -gt "$BACKUP_STALE_SECONDS" ]; then
      doctor_row warn "backup files" "$(dc_meter "$BACKUP_STALE_SECONDS" "$BACKUP_STALE_SECONDS") newest $(ago "$age"): the nightly one should keep it under 36 hours" \
        "sudo ${0} backup; sudo ${0} schedule-backups"
    else
      doctor_row ok "backup files" "$(dc_meter "$age" "$BACKUP_STALE_SECONDS") newest $(ago "$age"), $(as_root du -h "$newest" 2>/dev/null | cut -f1)"
    fi
  else
    doctor_row warn "backup files" "none in ${BACKUP_DIR}" "sudo ${0} backup"
  fi
  cronline="$(as_root crontab -u root -l 2>/dev/null | grep 'familydb-maintain-backup' | head -1 || true)"
  if [ -n "$cronline" ]; then
    doctor_row ok "backup schedule" "nightly, in root's crontab"
  elif as_root crontab -u "$SERVICE_USER" -l 2>/dev/null | grep -q 'familydb db backup'; then
    doctor_row ok "backup schedule" "nightly, in ${SERVICE_USER}'s crontab (an older setup)"
  else
    doctor_row warn "backup schedule" "nothing is scheduled, so a backup exists only when someone takes one" "sudo ${0} schedule-backups"
  fi
}

# Every section in turn, with a bar under way when the terminal can show one. A check that goes wrong
# is a row and never the end of the report.
dc_progress() { # dc_progress DONE TOTAL WHAT
  _live_ok || return 0
  local meter
  _bar meter 20 "$1" "$2" "$1" "$CYN" 1
  printf '\r  %s%s%s [%s] %s%3d%%%s  %s\033[K' "$CYN" "${SPIN_FRAMES[$1 % ${#SPIN_FRAMES[@]}]}" "$OFF" "$meter" "$DIM" $((100 * $1 / $2)) "$OFF" "$3"
}

dc_all() {
  dc_setup
  local -a steps=(dc_files dc_git dc_config dc_python dc_database dc_service dc_web dc_https dc_host dc_backups)
  local -a words=(files git config python database service "the page" https host backups)
  local total=${#steps[@]} i=0 fn
  for fn in "${steps[@]}"; do
    dc_progress "$i" "$total" "Looking at ${words[i]}"
    "$fn" || true
    i=$((i + 1))
  done
  if _live_ok; then printf '\r\033[K'; fi
}
