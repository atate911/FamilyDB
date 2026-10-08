#!/usr/bin/env bash
# Shared machinery for the FamilyDB scripts: output, logging, errors, retries, undo, the install
# ledger, which version to install. Source it, do not run it.
# A script using it cannot fail quietly: every step runs through `step` or `retry`, which capture
# output, and a failure prints what was being done, the command, its exit code, the last lines it
# said and what to try next. The run is logged to a file the failure names.
#   log_to FILE; step "What" cmd...; retry 3 "What" cmd...; on_failure_hint "..."

[ -n "${FAMILYDB_COMMON_SOURCED:-}" ] && return 0
FAMILYDB_COMMON_SOURCED=1

# Colour is for a person at a terminal. NO_COLOR turns it off (https://no-color.org); FORCE_COLOR
# turns it on in a pipe, for `| less -R`. Each stream is decided on its own, so a failure sent to a
# file carries no escape codes even when the screen does.
_wants_colour() { # _wants_colour FD
  [ -z "${NO_COLOR:-}" ] || return 1
  [ -z "${FORCE_COLOR:-}" ] || return 0
  [ -t "$1" ] && [ "${TERM:-dumb}" != dumb ]
}
if _wants_colour 1; then
  B=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; CYN=$'\033[36m'
  BADGE=$'\033[1;30;43m'; OFF=$'\033[0m'
else
  B=""; DIM=""; RED=""; YEL=""; GRN=""; CYN=""; BADGE=""; OFF=""
fi
if _wants_colour 2; then
  E_B=$'\033[1m'; E_DIM=$'\033[2m'; E_RED=$'\033[31m'; E_YEL=$'\033[33m'; E_CYN=$'\033[36m'; E_OFF=$'\033[0m'
else
  E_B=""; E_DIM=""; E_RED=""; E_YEL=""; E_CYN=""; E_OFF=""
fi

# shellcheck disable=SC2034  # some are read only by the scripts that source this file.
# The marks that say how a line went. They differ in shape as well as colour, so a screen with no
# colour reads the same. FAMILYDB_ASCII=1 is for a terminal that cannot draw the others.
if [ -n "${FAMILYDB_ASCII:-}" ]; then
  S_OK='+'; S_WARN='!'; S_BAD='x'; S_GO='>'; S_DOT='-'; S_RULE='-'; S_TODO='[ ]'; S_OFF='o'; S_TO='->'; S_ELLIPSIS='...'; S_SEP='>'
  SPIN_FRAMES=('|' '/' '-' '\')
else
  S_OK='✓'; S_WARN='!'; S_BAD='✗'; S_GO='→'; S_DOT='·'; S_RULE='─'; S_TODO='☐'; S_OFF='○'; S_TO='→'; S_ELLIPSIS='…'; S_SEP='›'
  SPIN_FRAMES=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
fi

# What a command prints under a heading can be indented with this; `head2` and `finish` go back to the margin.
INDENT=""
WARNED=()   # every warning this run said, for the recap at the end
SCRIPT_STARTED=$SECONDS

say()   { printf '%s\n' "$*"; }
head2() { INDENT=""; printf '\n%s%s%s\n' "$B" "$*" "$OFF"; log_line "== $*"; }
note()  { printf '%s%s%s%s\n' "$INDENT" "$DIM" "$*" "$OFF"; log_line "-- $*"; }
ok()    { _ok_line "$*" ""; }
_ok_line() { # _ok_line TEXT [SUFFIX] - a tick, what was done, and in dim how long it took
  printf '%s%s%s%s %s%s%s%s\n' "$INDENT" "$GRN" "$S_OK" "$OFF" "$1" "${2:+ $DIM}" "$2" "${2:+$OFF}"
  log_line "ok: $1${2:+ $2}"
}
warn()  {
  printf '%s%s%s%s %s\n' "$INDENT" "$E_YEL" "$S_WARN" "$E_OFF" "$*" >&2
  log_line "warn: $*"
  WARNINGS=$((WARNINGS + 1))
  WARNED+=("$*")
}

WARNINGS=0
LOG_FILE=""
HINT=""
DRY_RUN="${DRY_RUN:-0}"

log_to() { # log_to PATH - start writing a transcript. Falls back to a temp file.
  local wanted="$1" dir
  dir="$(dirname -- "$wanted")"
  if mkdir -p "$dir" 2>/dev/null && : >>"$wanted" 2>/dev/null; then
    LOG_FILE="$wanted"
  else
    LOG_FILE="$(mktemp -t familydb-XXXXXX.log 2>/dev/null || echo "")"
  fi
  [ -n "$LOG_FILE" ] || return 0
  chmod 600 "$LOG_FILE" 2>/dev/null || true
  {
    printf '\n===== %s =====\n' "$(date -u '+%Y-%m-%d %H:%M:%SZ')"
    printf 'script: %s\nargs: %s\n' "${0##*/}" "${SCRIPT_ARGS:-}"
    printf 'user: %s (uid %s)\n' "$(id -un 2>/dev/null || echo '?')" "$(id -u)"
    printf 'machine: %s %s\n' "$(uname -s)" "$(uname -m)"
    [ -r /etc/os-release ] && printf 'os: %s\n' "$(. /etc/os-release && echo "${PRETTY_NAME:-unknown}")"
  } >>"$LOG_FILE" 2>/dev/null || true
}

log_line() { # one line into the transcript, never onto the screen
  [ -n "$LOG_FILE" ] || return 0
  printf '%s %s\n' "$(date -u '+%H:%M:%S')" "$*" >>"$LOG_FILE" 2>/dev/null || true
}

# --- Layout -------------------------------------------------------------------------------------
# What a command shows, in the order a person reads it: a banner (what, where, how), a plan (what
# it is about to do and why, for the installers), a line per thing done, and a last word that says
# how it went and what to do next. Everything here is for the eye: the transcript in the log file
# has the same facts, with no colour.

ui_width() { # the columns to lay out in: the terminal's, kept between 40 and 88
  local w="${COLUMNS:-}"
  case "$w" in ''|*[!0-9]*) w=""; if [ -t 1 ]; then w="$(tput cols 2>/dev/null || true)"; fi ;; esac
  case "$w" in ''|*[!0-9]*) w=80 ;; esac
  [ "$w" -le 88 ] || w=88
  [ "$w" -ge 40 ] || w=40
  printf '%s' "$w"
}

rule() { # a thin line across the layout
  local line
  printf -v line '%*s' "$(ui_width)" ''
  printf '%s%s%s\n' "$DIM" "${line// /$S_RULE}" "$OFF"
}

wrap() { # wrap PAD STYLE TEXT... - TEXT broken at word ends to fit; WRAP_FIRST, if set, starts line one
  local pad="$1" style="$2" off="" width first
  shift 2
  first="${WRAP_FIRST:-$pad}"
  [ -z "$style" ] || off=$'\033[0m'
  width=$(( $(ui_width) - ${#pad} ))
  # fmt keeps a word longer than the line whole, as a path should be; fold would cut it.
  printf '%s\n' "$*" | { fmt -w "$width" 2>/dev/null || fold -s -w "$width"; } \
    | sed -e 's/[[:space:]]*$//' -e "1s/^/${first}${style}/" -e "1!s/^/${pad}${style}/" -e "s/\$/${off}/"
}

para() { # para TEXT... - a sentence or two, wrapped, under the current indent
  wrap "$INDENT" "" "$*"
  log_line "   $*"
}

hint() { # hint TEXT... - the same, dim: the reason behind something, not the thing itself
  wrap "$INDENT" "$DIM" "$*"
  log_line "-- $*"
}

fmt_secs() { # fmt_secs N - 5s, 1m 05s, 2h 03m, 3d 4h
  local n="$1"
  if [ "$n" -lt 60 ]; then
    printf '%ss' "$n"
  elif [ "$n" -lt 3600 ]; then
    printf '%sm %02ds' $((n / 60)) $((n % 60))
  elif [ "$n" -lt 86400 ]; then
    printf '%sh %02dm' $((n / 3600)) $((n % 3600 / 60))
  else
    printf '%sd %sh' $((n / 86400)) $((n % 86400 / 3600))
  fi
}

ago() { # ago SECONDS - how long ago, in the words a person would use
  local n="$1"
  if [ "$n" -lt 90 ]; then
    printf 'just now'
  elif [ "$n" -lt 5400 ]; then
    printf '%s min ago' $(((n + 30) / 60))
  elif [ "$n" -lt 172800 ]; then
    printf '%s hours ago' $(((n + 1800) / 3600))
  else
    printf '%s days ago' $((n / 86400))
  fi
}

kv() { # kv LABEL VALUE [ok|warn|bad|off] - one fact on a line, the labels lined up; a long value wraps under itself
  local mark="  " base="${INDENT:-  }" pad
  case "${3:-}" in
    ok)   mark="${GRN}${S_OK}${OFF} " ;;
    warn) mark="${YEL}${S_WARN}${OFF} " ;;
    bad)  mark="${RED}${S_BAD}${OFF} " ;;
    off)  mark="${DIM}${S_OFF}${OFF} " ;;
  esac
  printf -v pad '%*s' $((${#base} + 15)) ''
  WRAP_FIRST="$(printf '%s%s%s%-12s%s ' "$base" "$mark" "$DIM" "$1" "$OFF")" wrap "$pad" "" "$2"
  log_line "   $1: $2"
}

banner() { # banner "Upgrade" ["where, and how it runs"] - the first thing a command shows
  INDENT=""
  printf '\n%sFamilyDB%s %s%s%s %s%s%s' "$B" "$OFF" "$DIM" "$S_SEP" "$OFF" "$B$CYN" "$1" "$OFF"
  [ -z "${2:-}" ] || printf '  %s%s%s' "$DIM" "$2" "$OFF"
  printf '\n'
  rule
  log_line "== $1 ${2:-}"
  if [ "${DRY_RUN:-0}" = 1 ]; then
    printf '  %s[ DRY RUN ]%s %sNothing below is done; it only shows what would be.%s\n' "$BADGE" "$OFF" "$B" "$OFF"
  fi
}

finish() { # finish ok|warn|bad "Headline" - the last word: how it went, with the time it took
  local state="$1" headline="$2" mark colour count=${#WARNED[@]} took
  INDENT=""
  if [ "${DRY_RUN:-0}" = 1 ] && [ "$state" != bad ]; then
    state=ok
    headline="Dry run finished: nothing was changed"
  fi
  [ "$state" != ok ] || [ "$count" -eq 0 ] || state=warn
  case "$state" in
    ok)   mark="$S_OK"; colour="$GRN" ;;
    warn) mark="$S_WARN"; colour="$YEL"
          [ "$count" -eq 0 ] || headline="${headline}, with ${count} warning$([ "$count" -eq 1 ] || echo s)" ;;
    *)    mark="$S_BAD"; colour="$RED" ;;
  esac
  took=$((SECONDS - SCRIPT_STARTED))
  printf '\n'
  rule
  printf '%s%s %s%s%s' "$colour" "$mark" "$B" "$headline" "$OFF"
  [ "$took" -lt 3 ] || printf '  %s(%s)%s' "$DIM" "$(fmt_secs "$took")" "$OFF"
  printf '\n'
  log_line "== result: $state: $headline"
}

RECAPPED=0   # read by the script that sources this, which calls recap itself when a command did not
# shellcheck disable=SC2034  # RECAPPED is read by the scripts that source this file.
recap() { # every warning this run said, once more, so none is lost in the scroll
  RECAPPED=1
  local line
  [ ${#WARNED[@]} -gt 0 ] || return 0
  printf '\n%sWarnings%s\n' "$B" "$OFF"
  for line in "${WARNED[@]}"; do
    WRAP_FIRST="  ${YEL}${S_WARN}${OFF} " wrap "    " "" "$line"
  done
}

caution() { # caution TEXT - something to know before going on; not a warning of the run, so not said again
  WRAP_FIRST="${INDENT}${YEL}${S_WARN}${OFF} " wrap "${INDENT}  " "" "$*"
  log_line "caution: $*"
}

after() { # after "Heading" - what comes next, or what to do if it went wrong
  printf '\n%s%s%s\n' "$B" "$1" "$OFF"
  log_line "== $1"
}

todo() { # todo TEXT... - a thing left for the person, outside what this could do
  local pad
  printf -v pad '%*s' $((3 + ${#S_TODO})) ''
  WRAP_FIRST="  ${S_TODO} " wrap "$pad" "" "$*"
  log_line "todo: $*"
}

# A line a person would type is cyan, and its trailing "  # comment" dim. The first word decides.
_looks_like_command() {
  local word="${1#"${1%%[![:space:]]*}"}"
  word="${word%%[[:space:]]*}"
  case "$word" in
    sudo|cd|docker|systemctl|journalctl|ssh|scp|git|ls|df|du|curl|ping|cat|ps|free|command|apt|apt-get|ufw|ss|fuser|\
    dpkg|uv|crontab|bash|read|export|fallocate|mkswap|date|echo|id|install|caddy|tail|grep|chown|chmod|nano|vi|\
    cp|mv|rm|mkdir|tar|unzip|wget|FAMILYDB_*|WEB_*|COMPOSE_*|GITHUB_*) return 0 ;;
  esac
  return 1
}

_style_command() { # _style_command CYAN DIM OFF TEXT - TEXT with its command and its comment coloured
  local cyan="$1" dim="$2" off="$3" text="$4"
  local re='^(.*[^[:space:]])([[:space:]]{2,}#[[:space:]].*)$'
  if [[ $text =~ $re ]]; then
    printf '%s%s%s%s%s%s' "$cyan" "${BASH_REMATCH[1]}" "$off" "$dim" "${BASH_REMATCH[2]}" "$off"
  else
    printf '%s%s%s' "$cyan" "$text" "$off"
  fi
}

align_comments() { # commands on stdin with their "  # comment" lined up in one column
  awk '{
    i = index($0, "  # ")
    if (i > 0) { c = substr($0, 1, i - 1); sub(/ +$/, "", c); cmd[NR] = c; note[NR] = substr($0, i + 2); if (length(c) > w) w = length(c) }
    else { cmd[NR] = $0; note[NR] = "" }
  } END {
    for (n = 1; n <= NR; n++) {
      if (note[n] == "") print cmd[n]
      else printf "%s%*s  %s\n", cmd[n], w - length(cmd[n]), "", note[n]
    }
  }'
}

show_commands() { # show_commands - commands on stdin, one a line, as they are to be typed
  local line
  while IFS= read -r line; do
    printf '%s' "$INDENT"
    _style_command "$CYN" "$DIM" "$OFF" "$line"
    printf '\n'
    log_line "   $line"
  done < <(align_comments)
}

cmdline() { # cmdline "command" ["why"] - one command to copy, set apart from the words around it
  local text="$1"
  [ -z "${2:-}" ] || text="$1  # $2"
  printf '%s    ' "$INDENT"
  _style_command "$CYN" "$DIM" "$OFF" "$text"
  printf '\n'
  log_line "   $1"
}

# While a step runs, one line shows what it is and how long it has been going, then becomes the
# tick. Only at a terminal where nothing can ask for a password over it: root, or sudo that has
# its password already, and never in a dry run.
_LIVE=""
_live_ok() {
  if [ -z "$_LIVE" ]; then
    _LIVE=0
    if [ -t 1 ] && [ "${TERM:-dumb}" != dumb ] && [ "${DRY_RUN:-0}" != 1 ] && [ -z "${FAMILYDB_NO_LIVE:-}" ]; then
      if [ "$(id -u)" = 0 ] || sudo -n true 2>/dev/null; then _LIVE=1; fi
    fi
  fi
  [ "$_LIVE" = 1 ]
}

_spin() { # _spin WHAT PARENT - redraw one line, with the time so far, for as long as PARENT lives
  local what="$1" parent="$2" i=0 start=$SECONDS max
  max=$(( $(ui_width) - ${#INDENT} - 14 ))
  [ "${#what}" -le "$max" ] || what="${what:0:$((max - 3))}${S_ELLIPSIS}"
  while kill -0 "$parent" 2>/dev/null; do
    printf '\r%s%s%s%s %s %s%s%s\033[K' "$INDENT" "$CYN" "${SPIN_FRAMES[i % ${#SPIN_FRAMES[@]}]}" "$OFF" \
      "$what" "$DIM" "$(fmt_secs $((SECONDS - start)))" "$OFF"
    i=$((i + 1))
    sleep 0.15
  done
}

_spin_stop() { # _spin_stop PID - stop the line drawing itself, and leave the screen clean for what follows
  kill "$1" 2>/dev/null || true
  wait "$1" 2>/dev/null || true
  printf '\r\033[K'
}

_OUT=""
_STATUS=0
# The command runs where it always did, in the foreground, so Ctrl-C reaches it; only the line that
# shows it working is a background process, and it goes when the command does.
_capture() { # _capture WHAT CMD... - run CMD; its output is left in _OUT and its exit status in _STATUS
  local what="$1" spinner
  shift
  _OUT=""
  _STATUS=0
  if _live_ok; then
    _spin "$what" "$$" &
    spinner=$!
    # shellcheck disable=SC2064  # the spinner's number is wanted now, not when the trap runs
    trap "_spin_stop $spinner; trap - INT; kill -INT $$" INT
    _OUT="$("$@" 2>&1)" || _STATUS=$?
    trap - INT
    _spin_stop "$spinner"
    return 0
  fi
  _OUT="$("$@" 2>&1)" || _STATUS=$?
}

on_failure_hint() { HINT="$*"; }  # what to say at the bottom of any failure from here on
# The foot of every failure. A script names its command with again_hint; FAMILYDB_AGAIN, set by
# the pasted install block, wins: that is what the person actually ran.
AGAIN=""
again_hint() { AGAIN="$*"; }

# Everything the install changes outside its own directory, written down as it happens so
# `uninstall.sh --from-zero` undoes exactly that (packages it added, files, links, replaced files
# with a kept copy, users, cron lines, firewall rules). One line per change: KIND, tab, what.
# Outside /opt/familydb so removing the install cannot lose it; it goes last.
LEDGER_DIR=/var/lib/familydb-install
LEDGER="${LEDGER_DIR}/ledger"
# Where the install's SSH keeps GitHub's host key, rather than root's own known_hosts.
# shellcheck disable=SC2034  # read by bootstrap.sh, which sources this
KNOWN_HOSTS="${LEDGER_DIR}/known_hosts"

# Only a root install changes the system; a run as somebody else is a development checkout and
# must not ask for a sudo password.
_ledger_on() { [ "$(id -u)" = 0 ] && [ "${DRY_RUN:-0}" != 1 ]; }

ledger() { # ledger KIND WHAT - write down one change, once
  _ledger_on || return 0
  mkdir -p "${LEDGER_DIR}/saved" 2>/dev/null || return 0
  chmod 700 "$LEDGER_DIR" 2>/dev/null || true
  ledger_has "$1" "$2" && return 0
  printf '%s\t%s\n' "$1" "$2" >>"$LEDGER"
}

ledger_has() { grep -qxF "$(printf '%s\t%s' "$1" "$2")" "$LEDGER" 2>/dev/null; }

noting_new() { # noting_new PATH [KIND] - before making PATH: note it, unless it is there already
  _ledger_on || return 0
  [ -e "$1" ] || [ -L "$1" ] || ledger "${2:-file}" "$1"
}

noting_replaced() { # noting_replaced PATH - before overwriting PATH: keep the original, once
  _ledger_on || return 0
  if [ ! -f "$1" ]; then
    noting_new "$1"
    return 0
  fi
  ledger_has file "$1" && return 0      # made by an earlier run of the install: ours already
  ledger_has replaced "$1" && return 0  # the original is already kept
  local saved="${LEDGER_DIR}/saved${1}"
  mkdir -p "$(dirname "$saved")" && cp -a "$1" "$saved" && ledger replaced "$1"
}

# The account the bot runs as, written down beside the ledger so maintain.sh and uninstall.sh find
# it again. An install that never wrote it ran as familydb.
SERVICE_USER_FILE="${LEDGER_DIR}/service-user"
DEFAULT_SERVICE_USER="familydb"

valid_user_name() { # a lowercase system account name, as useradd takes without fuss
  case "$1" in ''|[!a-z_]*|*[!a-z0-9_-]*) return 1 ;; esac
  [ "${#1}" -le 32 ]
}

record_service_user() { # record_service_user NAME
  _ledger_on || return 0
  mkdir -p "$LEDGER_DIR" 2>/dev/null && chmod 700 "$LEDGER_DIR" 2>/dev/null || return 0
  printf '%s\n' "$1" >"$SERVICE_USER_FILE" 2>/dev/null || true
}

recorded_service_user() { # recorded_service_user [TARGET] - the recorded account, else who owns TARGET/data, else familydb
  local name="" owner=""
  if [ -r "$SERVICE_USER_FILE" ]; then
    name="$(head -n1 "$SERVICE_USER_FILE" 2>/dev/null || true)"
  elif [ "$(id -u)" != 0 ] && have sudo; then
    name="$(sudo -n cat "$SERVICE_USER_FILE" 2>/dev/null | head -n1 || true)"
  fi
  if ! valid_user_name "$name" && [ -n "${1:-}" ]; then
    owner="$(stat -c %U "${1}/data" 2>/dev/null || true)"
    [ "$owner" != root ] && name="$owner"
  fi
  valid_user_name "$name" || name="$DEFAULT_SERVICE_USER"
  printf '%s\n' "$name"
}

installed_packages() { # every package dpkg has fully installed, one per line, sorted
  dpkg-query -W -f='${db:Status-Abbrev} ${Package}\n' 2>/dev/null | awk '$1 == "ii" {print $2}' | sort
}

apt_install_noted() { # apt_install_noted [OPTIONS] PACKAGE... - install, and note what was new
  local before after package
  before="$(installed_packages)"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@" || return $?
  after="$(installed_packages)"
  for package in $(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after")); do
    ledger package "$package"
  done
}

noting_user() { # noting_user NAME - after creating a system user: it, and the group it came with
  _ledger_on || return 0
  ledger user "$1"
  getent group "$1" >/dev/null 2>&1 && ledger group "$1"
  return 0
}

# Things to undo if the script dies part-way. Registered as shell commands, run in reverse.
UNDO=()
undo_on_failure() { UNDO+=("$*"); }
forget_undo() { UNDO=(); }

_run_undo() {
  [ ${#UNDO[@]} -gt 0 ] || return 0
  printf '\n%sPutting things back%s\n' "$E_B" "$E_OFF" >&2
  local i
  for (( i=${#UNDO[@]}-1 ; i>=0 ; i-- )); do
    log_line "undo: ${UNDO[i]}"
    if eval "${UNDO[i]}" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      printf '  undone: %s\n' "${UNDO[i]}" >&2
    else
      printf '  %scould not undo:%s %s\n' "$E_YEL" "$E_OFF" "${UNDO[i]}" >&2
    fi
  done
  UNDO=()
}

# One line of a failure's explanation, on stderr: prose is wrapped, and a command is cyan.
_detail() {
  if [ -z "$1" ]; then
    printf '\n'
  elif _looks_like_command "$1"; then
    printf '   '
    _style_command "$E_CYN" "$E_DIM" "$E_OFF" "$1"
    printf '\n'
  elif [ "${1# }" = "$1" ]; then
    wrap "   " "" "$1"
  else
    printf '   %s\n' "$1"
  fi
}

die() { # die MESSAGE [MORE...] - a failure we diagnosed ourselves
  EXPLAINED=1
  INDENT=""
  printf '\n%s%s %s%s\n' "$E_B$E_RED" "$S_BAD" "$1" "$E_OFF" >&2
  log_line "FAIL: $1"
  shift
  local line
  for line in "$@"; do
    _detail "$line" >&2
    log_line "   $line"
  done
  _report_tail
  _run_undo
  exit 1
}

_report_tail() {
  if [ -n "$HINT" ]; then
    local line
    printf '\n' >&2
    while IFS= read -r line; do _detail "$line" >&2; done <<<"$HINT"
  fi
  local again="${FAMILYDB_AGAIN:-$AGAIN}"
  if [ -n "$again" ]; then
    printf '\n' >&2
    printf '   %sWhen that is sorted, %s%s\n' "$E_B" "$again" "$E_OFF" >&2
    wrap "   " "" "It keeps everything that already worked and carries on from where it stopped." >&2
  fi
  if [ -n "$LOG_FILE" ]; then
    printf '\n   %sThe full transcript is at%s %s%s%s\n' "$E_DIM" "$E_OFF" "$E_B" "$LOG_FILE" "$E_OFF" >&2
    printf '   %sSend that file if you need someone to look.%s\n' "$E_DIM" "$E_OFF" >&2
  fi
}

EXPLAINED=0
FAILED_STEP=""

_exit_trap() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$EXPLAINED" = 0 ]; then
    printf '\n%s%s stopped unexpectedly%s\n' "$E_B$E_RED" "$S_BAD" "$E_OFF" >&2
    [ -n "$FAILED_STEP" ] && printf '   while: %s\n' "$FAILED_STEP" >&2
    printf '   exit code %s\n' "$status" >&2
    _report_tail
    _run_undo
  fi
  return $status
}

enable_failure_reporting() { # call once, after sourcing
  trap '_exit_trap' EXIT
  trap 'FAILED_STEP="$BASH_COMMAND"' ERR
}

# `step "What this is" cmd args...`: output captured, a tick on success, the full story on failure.
step() {
  local what="$1"; shift
  _run_step "$what" 1 "$@"
}

# Same, but a failure is a warning. Always returns 0 so a bare call cannot trip `set -e`; the
# command's exit code is left in LAST_STEP_STATUS.
# shellcheck disable=SC2034  # read by the scripts that source this file.
LAST_STEP_STATUS=0
try_step() {
  local what="$1"; shift
  LAST_STEP_STATUS=0
  # shellcheck disable=SC2034  # read by the scripts that source this file.
  _run_step "$what" 0 "$@" || LAST_STEP_STATUS=$?
  return 0
}

_run_step() {
  local what="$1" fatal="$2" began=$SECONDS; shift 2
  if [ "$DRY_RUN" = 1 ]; then
    _dry_line "$what"
    log_line "would run: $*"
    return 0
  fi
  FAILED_STEP="$what"
  log_line "step: $what :: $*"
  # `|| status=$?` inside _capture: under `set -e` a bare failing substitution would exit before the
  # report runs, and `if ! ...` would make $? the negation, always 0.
  _capture "$what" "$@"
  local output="$_OUT" status="$_STATUS"
  if [ -n "$output" ]; then
    printf '%s\n' "$output" >>"${LOG_FILE:-/dev/null}" 2>/dev/null || true
  fi
  if [ "$status" = 0 ]; then
    _step_done "$what" "$(_took $((SECONDS - began)))"
    FAILED_STEP=""
    return 0
  fi
  if [ "$fatal" = 1 ]; then
    EXPLAINED=1
    _failure "$what — failed" "$status" "$output" "$*" 12 "what it said:"
    diagnose "$output" || true
    log_line "FAIL: $what (exit $status)"
    _report_tail
    _run_undo
    exit "$status"
  fi
  warn "$what — failed (exit $status), carrying on"
  if [ -n "$output" ]; then
    printf '%s\n' "$output" | tail -6 | sed 's/^/     /' >&2
    diagnose "$output" || true
  fi
  FAILED_STEP=""
  return "$status"
}

# A step that went as expected can say nothing, when a line of the caller's says it better: with
# STEP_QUIET set, only what went wrong is shown (the log has all of it).
_step_done() { # _step_done WHAT [SUFFIX]
  if [ -n "${STEP_QUIET:-}" ]; then
    log_line "ok: $1${2:+ $2}"
  else
    _ok_line "$1" "${2:-}"
  fi
}

_dry_line() { # what a step would have done, in a dry run
  printf '%s%s%s %s — dry run, not done%s\n' "$INDENT" "$DIM" "$S_OFF" "$1" "$OFF"
}

_took() { # _took SECONDS - how long a step took, said only when it was long enough to notice
  [ "$1" -lt 3 ] || printf '(%s)' "$(fmt_secs "$1")"
}

_failure() { # _failure HEADLINE STATUS OUTPUT COMMAND LINES LABEL - what stopped, and what it said
  INDENT=""
  printf '\n%s%s %s%s\n' "$E_B$E_RED" "$S_BAD" "$1" "$E_OFF" >&2
  printf '   %scommand:%s %s\n' "$E_DIM" "$E_OFF" "$4" >&2
  printf '   %sexit code:%s %s\n' "$E_DIM" "$E_OFF" "$2" >&2
  if [ -n "$3" ]; then
    printf '   %s%s%s\n' "$E_DIM" "$6" "$E_OFF" >&2
    printf '%s\n' "$3" | tail -n "$5" | sed 's/^/     /' >&2
  fi
}

# `retry N "What" cmd...` for the network. Waits 2, 4, 8... s: a VPS just booted may lack DNS.
retry() {
  local tries="$1" what="$2" began=$SECONDS; shift 2
  if [ "$DRY_RUN" = 1 ]; then
    _dry_line "$what"
    log_line "would run: $*"
    return 0
  fi
  local attempt=1 wait=2 output status=0
  while : ; do
    FAILED_STEP="$what (attempt ${attempt})"
    log_line "try ${attempt}/${tries}: $what :: $*"
    _capture "$what" "$@"
    output="$_OUT"; status="$_STATUS"
    [ -n "$output" ] && { printf '%s\n' "$output" >>"${LOG_FILE:-/dev/null}" 2>/dev/null || true; }
    if [ "$status" = 0 ]; then
      _step_done "$what" "$(_took $((SECONDS - began)))"
      FAILED_STEP=""
      return 0
    fi
    if [ "$attempt" -ge "$tries" ]; then
      EXPLAINED=1
      _failure "$what — failed ${tries} times" "$status" "$output" "$*" 12 "what it said the last time:"
      if ! diagnose "${output:-}"; then
        printf '\n   %sWhat this means:%s it needs the network and could not get there.\n' "$E_B" "$E_OFF" >&2
        printf '   %sWhat to try:%s\n' "$E_B" "$E_OFF" >&2
        _detail "  curl -fsS https://pypi.org/simple/ >/dev/null && echo reachable" >&2
        _detail "  ping -c1 1.1.1.1" >&2
      fi
      log_line "FAIL: $what after ${tries} attempts (exit $status)"
      _report_tail
      _run_undo
      exit "$status"
    fi
    warn "$what — attempt ${attempt} failed; trying again in ${wait}s"
    sleep "$wait"
    attempt=$((attempt + 1))
    wait=$((wait * 2))
  done
}

have() { command -v "$1" >/dev/null 2>&1; }

SYSTEM_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
on_system_path() { # every user has to find it, not just whoever is running this
  # `command` is a shell builtin, so it needs a shell: env cannot exec it.
  env -i PATH="$SYSTEM_PATH" sh -c 'command -v "$1" >/dev/null 2>&1' _ "$1"
}

as_root() { if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi; }

require_free_mb() { # require_free_mb PATH MB "what for"
  local path="$1" wanted="$2" what="$3" free
  [ -e "$path" ] || path="$(dirname -- "$path")"
  free="$(df -Pm "$path" 2>/dev/null | awk 'NR==2 {print $4}')" || free=""
  [ -n "$free" ] || return 0
  if [ "$free" -lt "$wanted" ]; then
    die "only ${free} MB free on ${path}, and ${what} needs about ${wanted} MB" \
        "Free some space and run this again. The biggest things are usually:" \
        "  sudo journalctl --vacuum-size=200M" \
        "  sudo apt-get clean" \
        "  docker system prune -af   (if Docker is installed)"
  fi
  log_line "free space on ${path}: ${free} MB"
}

# `checkpoint NAME` marks how far a run got, so a second run can say where the first stopped.
CHECKPOINT_FILE=""
checkpoint_to() { CHECKPOINT_FILE="$1"; }
checkpoint() {
  [ -n "$CHECKPOINT_FILE" ] || return 0
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >>"$CHECKPOINT_FILE" 2>/dev/null || true
  log_line "checkpoint: $1"
}
last_checkpoint() {
  [ -r "${CHECKPOINT_FILE:-}" ] || return 1
  tail -1 "$CHECKPOINT_FILE" 2>/dev/null | awk '{print $2}'
}

# `diagnose` matches a failing command's output against what goes wrong on a fresh server and
# gives: what it means, how to check, how to fix.
diagnose() { # diagnose "<the command's output>"
  local text="$1" matched=0
  _explain() { # _explain "meaning" "how to check" "how to fix"...
    matched=1
    printf '\n   %sWhat this means:%s %s\n' "$E_B" "$E_OFF" "$1" >&2
    shift
    printf '   %sWhat to try:%s\n' "$E_B" "$E_OFF" >&2
    local line
    for line in "$@"; do _detail "  $line" >&2; done
  }

  case "$text" in
    *"No space left on device"*|*"no space left"*)
      _explain "The disk is full. Nothing can be written until something is removed." \
        "df -h /            # see which filesystem is full" \
        "sudo journalctl --vacuum-size=200M" \
        "sudo apt-get clean" \
        "docker system prune -af    # if Docker is installed, this often frees the most" ;;
    *"Could not resolve host"*|*"Temporary failure in name resolution"*|*"Name or service not known"*)
      _explain "The machine cannot turn a name into an address, so it cannot reach anything." \
        "ping -c1 1.1.1.1        # does the network work at all?" \
        "cat /etc/resolv.conf    # is there a nameserver listed?" \
        "If this is a VPS that has just booted, wait a minute and run this again." ;;
    *"certificate"*|*"SSL"*|*"self-signed"*|*"UnknownIssuer"*)
      _explain "HTTPS could not be verified. Usually a proxy in the middle, or a wrong clock." \
        "date -u                 # a clock more than a day out breaks every certificate" \
        "sudo apt-get install --reinstall ca-certificates" \
        "Behind a company proxy, point SSL_CERT_FILE at its CA bundle and run this again." ;;
    *"Failed to connect to bus"*|*"System has not been booted with systemd"*)
      _explain "systemd is not running here, so there is no service to start or stop. This is normal inside a container, in WSL, or in a chroot." \
        "ps -p 1 -o comm=       # what is actually running as process 1" \
        "On a normal VPS this should say systemd. In Docker, run the bot with compose instead." ;;
    *"Connection refused"*|*"Failed to connect"*|*"Connection timed out"*)
      _explain "Something would not accept the connection: a firewall, or nothing listening." \
        "curl -fsS https://pypi.org/simple/ >/dev/null && echo 'outbound HTTPS works'" \
        "sudo ufw status         # is an outbound rule blocking it?" ;;
    *"Could not get lock"*|*"dpkg frontend lock"*|*"Unable to acquire the dpkg"*)
      _explain "Another program is installing packages right now. Only one may at a time." \
        "sudo fuser -v /var/lib/dpkg/lock-frontend    # who holds it" \
        "Unattended upgrades often hold it just after a server boots. Wait a minute, run again." \
        "sudo dpkg --configure -a    # if a previous install was interrupted" ;;
    *"Authentication failed"*|*"could not read Username"*|*"Permission denied (publickey)"*|*" 403 "*|*" 401 "*)
      _explain "The server refused the credentials, so the code could not be fetched." \
        "For a deploy key: ssh -T git@github.com -i <the key>   # should name the repository" \
        "For a token: it needs read access to this repository and must not have expired." \
        "docs/INSTALL.md, 'Other ways to get the code onto the server', has the whole flow." ;;
    *"No such file or directory"*)
      _explain "A program or file this step needs is not there." \
        "ls -ld <the path it named>    # does it exist, and who can see it?" \
        "command -v <the program>      # is it installed where the service account looks?" \
        "A tool installed into one person's home directory cannot be seen by anyone else." ;;
    *"Permission denied"*|*"Operation not permitted"*)
      _explain "The account running this may not touch that file or directory." \
        "ls -ld <the path it named>    # who owns it, and what the mode is" \
        "id                            # who you are running as" \
        "Re-run with sudo, or give the path to the right user with chown." ;;
    *"address already in use"*|*"Address already in use"*)
      _explain "The port is taken by something else already running." \
        "sudo ss -ltnp | grep ':<port>'    # what is on it" \
        "Stop that, or move FamilyDB to a free port: sudo scripts/maintain.sh port random" ;;
    *"Killed"*|*"MemoryError"*|*"Cannot allocate memory"*|*"out of memory"*)
      _explain "The machine ran out of memory and the kernel stopped the command." \
        "free -m                 # how much there is" \
        "Add swap, then run this again:" \
        "  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile" \
        "  sudo mkswap /swapfile && sudo swapon /swapfile" ;;
    *"command not found"*|*"not found"*)
      _explain "A program this step needs is not installed, or not on the PATH." \
        "command -v <the program>     # is it anywhere?" \
        "echo \$PATH                  # is its folder listed?" \
        "A tool installed into a home directory cannot be seen by the service account." ;;
    *"database is locked"*)
      _explain "Two processes tried to write the database at once." \
        "sudo systemctl stop familydb     # stop the bot, then run this again" \
        "Only one 'familydb run' may exist at a time." ;;
  esac
  [ "$matched" = 1 ] || return 1
  return 0
}

# System changes are declared up front with `plan_item`, shown by `show_plan`, and said again
# when each happens.

PLAN_WHAT=()
PLAN_WHY=()
PLAN_UNTOUCHED=()

plan_item()      { PLAN_WHAT+=("$1"); PLAN_WHY+=("$2"); }
plan_untouched() { PLAN_UNTOUCHED+=("$1"); }

plan_is_empty() { [ ${#PLAN_WHAT[@]} -eq 0 ]; }

show_plan() { # show_plan "heading" - the numbered steps, why each, and what stays alone
  plan_is_empty && return 0
  head2 "${1:-What this will change on this machine}"
  local i
  for i in "${!PLAN_WHAT[@]}"; do
    printf '  %s%d%s  %s%s%s\n' "$CYN" $((i + 1)) "$OFF" "$B" "${PLAN_WHAT[i]}" "$OFF"
    wrap "     " "$DIM" "${PLAN_WHY[i]}"
    log_line "plan: ${PLAN_WHAT[i]} :: ${PLAN_WHY[i]}"
  done
  local item
  if [ ${#PLAN_UNTOUCHED[@]} -gt 0 ]; then
    printf '\n  %sLeft alone:%s\n' "$DIM" "$OFF"
    for item in "${PLAN_UNTOUCHED[@]}"; do
      WRAP_FIRST="    ${S_DOT} " wrap "      " "$DIM" "$item"
    done
  fi
  printf '\n'
}

# Announce one system-level change as it happens: what, and why, in a sentence.
system_change() { # system_change "what" "why"
  if [ "${DRY_RUN:-0}" = 1 ]; then
    _dry_line "$1"
  else
    printf '%s%s%s%s %s%s%s\n' "$INDENT" "$CYN" "$S_GO" "$OFF" "$B" "$1" "$OFF"
  fi
  wrap "${INDENT}  " "$DIM" "$2"
  log_line "change: $1 :: $2"
}

# Two different questions, deliberately kept apart:
#
#   confirm  — a preference, where --yes means "take the default you offered".
#   approve  — an action that needs someone to say so, where --yes means yes. With no terminal
#              and no --yes there is nobody to ask, so it is a no. Enter takes the default, which
#              is yes for what a person does every week and no for what cannot be undone.
approve() { # approve "question" [yes|no]
  local question="$1" default="${2:-no}" reply hint="y/N"
  [ "$default" != yes ] || hint="Y/n"
  if [ "${ASSUME_YES:-0}" = 1 ]; then
    log_line "approved by --yes: ${question}"
    return 0
  fi
  if [ ! -t 0 ]; then
    warn "${question}"
    note "There is no terminal here to answer, so the answer is no. Pass --yes if you mean it."
    return 1
  fi
  read -r -p "${CYN}?${OFF} ${B}${question}${OFF} [${hint}]: " reply || reply=""
  case "$reply" in
    [Yy]*) return 0 ;;
    [Nn]*) return 1 ;;
    '') [ "$default" = yes ] ;;
    *) return 1 ;;
  esac
}

confirm() { # confirm "question" yes|no  - honours ASSUME_YES and a missing terminal
  local question="$1" default="${2:-yes}" reply
  if [ "${ASSUME_YES:-0}" = 1 ] || [ ! -t 0 ]; then [ "$default" = yes ]; return; fi
  read -r -p "$question [$([ "$default" = yes ] && echo 'Y/n' || echo 'y/N')]: " reply || reply=""
  reply="${reply:-$default}"
  case "$reply" in [Yy]*|yes) return 0 ;; *) return 1 ;; esac
}

# `familydb doctor` prints "MARK name: detail" for each finding, "    → fix" under any that is not fine,
# and its verdict last. This colours that, and counts it. "problems" shows only what is not fine, for
# a run that has something else to say first, "failures" only what must be fixed, "count" nothing at all; "all" shows the lot. The counts are left in
# DOCTOR_FINE, DOCTOR_WARN and DOCTOR_BAD, and its own last line in DOCTOR_VERDICT.
DOCTOR_FINE=0; DOCTOR_WARN=0; DOCTOR_BAD=0; DOCTOR_VERDICT=""
# shellcheck disable=SC2034  # the counts and the verdict are read by the scripts that source this file.
show_doctor() { # show_doctor all|problems|failures|count "the report"
  local mode="$1" report="$2" line showing=0 last=""
  DOCTOR_FINE=0; DOCTOR_WARN=0; DOCTOR_BAD=0; DOCTOR_VERDICT=""
  while IFS= read -r line; do
    case "$line" in
      "✓ "*) DOCTOR_FINE=$((DOCTOR_FINE + 1)); showing=0
             [ "$mode" = all ] && { showing=1; printf '  %s%s%s %s\n' "$GRN" "$S_OK" "$OFF" "${line#✓ }"; } ;;
      "! "*) DOCTOR_WARN=$((DOCTOR_WARN + 1)); showing=0
             case "$mode" in all|problems) showing=1; printf '  %s%s%s %s\n' "$YEL" "$S_WARN" "$OFF" "${line#! }" ;; esac ;;
      "✗ "*) DOCTOR_BAD=$((DOCTOR_BAD + 1)); showing=0
             [ "$mode" = count ] || { showing=1; printf '  %s%s%s %s%s%s\n' "$RED" "$S_BAD" "$OFF" "$B" "${line#✗ }" "$OFF"; } ;;
      "· "*) showing=0
             [ "$mode" = all ] && { showing=1; printf '  %s%s %s%s\n' "$DIM" "$S_DOT" "${line#· }" "$OFF"; } ;;
      "→ "*|"    →"*) [ "$showing" = 1 ] && printf '      %s%s%s\n' "$CYN" "${line#"${line%%→*}"}" "$OFF" ;;
      "") ;;
      *) last="$line"
         [ "$mode" = all ] && printf '  %s%s%s\n' "$DIM" "$line" "$OFF" ;;
    esac
    [ "$mode" = count ] || log_line "doctor: $line"
  done <<<"$report"
  case "$last" in [0-9]*|*"WARNING"*|*"ERROR"*) ;; *) DOCTOR_VERDICT="$last" ;; esac
}

# While CHANGELOG.md's newest heading says "in progress" an install follows the default branch;
# once it carries a date, the release tags. An upgrade only ever moves forward.

in_progress() { # in_progress DIR REF - succeeds when REF's changelog says its newest version is unreleased
  as_root git -C "$1" show "${2}:CHANGELOG.md" 2>/dev/null \
    | grep -m1 '^## v' | grep -qi 'in progress'
}

default_branch() { # default_branch DIR - the remote's default branch, as a bare name
  local ref
  ref="$(as_root git -C "$1" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -z "$ref" ]; then
    as_root git -C "$1" remote set-head origin --auto >/dev/null 2>&1 || true
    ref="$(as_root git -C "$1" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  fi
  printf '%s\n' "${ref#origin/}"
}

wanted_version() { # wanted_version DIR - prints "branch NAME", "tag NAME" or "none"
  local branch tag
  branch="$(default_branch "$1")"
  tag="$(as_root git -C "$1" tag -l 'v*' --sort=-v:refname 2>/dev/null | head -1 || true)"
  if [ -n "$branch" ] && { [ -z "$tag" ] || in_progress "$1" "origin/${branch}"; }; then
    printf 'branch %s\n' "$branch"
  elif [ -n "$tag" ]; then
    printf 'tag %s\n' "$tag"
  else
    printf 'none\n'
  fi
}

moves_forward() { # moves_forward DIR TARGET - succeeds when TARGET holds everything installed now, and more
  as_root git -C "$1" merge-base --is-ancestor HEAD "$2" \
    && ! as_root git -C "$1" merge-base --is-ancestor "$2" HEAD
}
