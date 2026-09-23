#!/usr/bin/env bash
# Shared machinery for the FamilyDB scripts: output, logging, error reporting, retries and
# undo. Source it, do not run it.
#
# The point of this file is that a script using it cannot fail quietly. Every step runs through
# `step`, which captures the command's output, and any failure prints what was being done, the
# command, its exit code, the last lines of what it said, and the one thing to try next. The
# whole run is also written to a log file that the failure message names, so somebody who needs
# help has one file to send.
#
#   source "$(dirname "$0")/lib/common.sh"
#   log_to /var/log/familydb-install.log
#   step "Installing the dependencies" apt-get install -y git
#   retry 3 "Downloading uv" curl -fsSL https://example -o /tmp/uv
#   on_failure_hint "Read RUNBOOK section 13."

# Guard against being sourced twice.
[ -n "${FAMILYDB_COMMON_SOURCED:-}" ] && return 0
FAMILYDB_COMMON_SOURCED=1

# ---------------------------------------------------------------- output ----
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; OFF=$'\033[0m'
else
  B=""; DIM=""; RED=""; YEL=""; GRN=""; OFF=""
fi

say()   { printf '%s\n' "$*"; }
head2() { printf '\n%s%s%s\n' "$B" "$*" "$OFF"; log_line "== $*"; }
note()  { printf '%s%s%s\n' "$DIM" "$*" "$OFF"; log_line "-- $*"; }
ok()    { printf '%s✓%s %s\n' "$GRN" "$OFF" "$*"; log_line "ok: $*"; }
warn()  { printf '%s!%s %s\n' "$YEL" "$OFF" "$*" >&2; log_line "warn: $*"; WARNINGS=$((WARNINGS + 1)); }

WARNINGS=0
LOG_FILE=""
HINT=""
DRY_RUN="${DRY_RUN:-0}"

# ----------------------------------------------------------------- log ----
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

on_failure_hint() { HINT="$*"; }  # what to say at the bottom of any failure from here on

# --------------------------------------------------------------- failure ----
# Things to undo if the script dies part-way. Registered as shell commands, run in reverse.
UNDO=()
undo_on_failure() { UNDO+=("$*"); }
forget_undo() { UNDO=(); }

_run_undo() {
  [ ${#UNDO[@]} -gt 0 ] || return 0
  printf '\n%sPutting things back%s\n' "$B" "$OFF" >&2
  local i
  for (( i=${#UNDO[@]}-1 ; i>=0 ; i-- )); do
    log_line "undo: ${UNDO[i]}"
    if eval "${UNDO[i]}" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      printf '  undone: %s\n' "${UNDO[i]}" >&2
    else
      printf '  %scould not undo:%s %s\n' "$YEL" "$OFF" "${UNDO[i]}" >&2
    fi
  done
  UNDO=()
}

die() { # die MESSAGE [MORE...] - a failure we diagnosed ourselves
  EXPLAINED=1
  printf '\n%s✗ %s%s\n' "$RED" "$1" "$OFF" >&2
  log_line "FAIL: $1"
  shift
  local line
  for line in "$@"; do
    printf '   %s\n' "$line" >&2
    log_line "   $line"
  done
  _report_tail
  _run_undo
  exit 1
}

_report_tail() {
  [ -n "$HINT" ] && printf '\n   %s\n' "$HINT" >&2
  if [ -n "$LOG_FILE" ]; then
    printf '\n   The full transcript is at %s%s%s\n' "$B" "$LOG_FILE" "$OFF" >&2
    printf '   Send that file if you need someone to look.\n' >&2
  fi
}

EXPLAINED=0
FAILED_STEP=""

_exit_trap() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$EXPLAINED" = 0 ]; then
    printf '\n%s✗ stopped unexpectedly%s\n' "$RED" "$OFF" >&2
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

# ----------------------------------------------------------------- steps ----
# `step "What this is" cmd args...` runs a command with its output captured. On success it
# prints a tick. On failure it prints everything needed to understand why, then stops.
step() {
  local what="$1"; shift
  _run_step "$what" 1 "$@"
}

# Same, but a failure is a warning and the script carries on. It always returns 0, so that a
# bare call cannot trip `set -e` and stop a script that was written to survive this exact
# failure. The command's own exit code is left in LAST_STEP_STATUS for anyone who cares.
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
  local what="$1" fatal="$2"; shift 2
  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] ${what}"
    log_line "would run: $*"
    return 0
  fi
  FAILED_STEP="$what"
  log_line "step: $what :: $*"
  # `|| status=$?` rather than a bare assignment: under `set -e` a failing command substitution
  # would exit the script before its status could be read, and none of this reporting would run.
  # It must not be `if ! ...` either, because there $? is the negation, which is always 0.
  local output status=0
  output="$("$@" 2>&1)" || status=$?
  if [ -n "$output" ]; then
    printf '%s\n' "$output" >>"${LOG_FILE:-/dev/null}" 2>/dev/null || true
  fi
  if [ "$status" = 0 ]; then
    ok "$what"
    FAILED_STEP=""
    return 0
  fi
  if [ "$fatal" = 1 ]; then
    EXPLAINED=1
    printf '\n%s✗ %s%s\n' "$RED" "$what — failed" "$OFF" >&2
    printf '   command: %s\n' "$*" >&2
    printf '   exit code: %s\n' "$status" >&2
    if [ -n "$output" ]; then
      printf '   what it said:\n' >&2
      printf '%s\n' "$output" | tail -12 | sed 's/^/     /' >&2
      diagnose "$output" || true
    fi
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

# `retry N "What this is" cmd args...` for anything that touches the network. Waits 2, 4, 8...
# seconds between attempts, because a VPS that has just booted often has no DNS for a moment.
retry() {
  local tries="$1" what="$2"; shift 2
  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] ${what}"
    log_line "would run: $*"
    return 0
  fi
  local attempt=1 wait=2 output status=0
  while : ; do
    FAILED_STEP="$what (attempt ${attempt})"
    log_line "try ${attempt}/${tries}: $what :: $*"
    status=0
    output="$("$@" 2>&1)" || status=$?
    [ -n "$output" ] && { printf '%s\n' "$output" >>"${LOG_FILE:-/dev/null}" 2>/dev/null || true; }
    if [ "$status" = 0 ]; then
      ok "$what"
      FAILED_STEP=""
      return 0
    fi
    if [ "$attempt" -ge "$tries" ]; then
      EXPLAINED=1
      printf '\n%s✗ %s — failed %s times%s\n' "$RED" "$what" "$tries" "$OFF" >&2
      printf '   command: %s\n' "$*" >&2
      printf '   exit code: %s\n' "$status" >&2
      if [ -n "$output" ]; then
        printf '   what it said the last time:\n' >&2
        printf '%s\n' "$output" | tail -12 | sed 's/^/     /' >&2
      fi
      if ! diagnose "${output:-}"; then
        printf '\n   %sWhat this means:%s it needs the network and could not get there.\n' "$B" "$OFF" >&2
        printf '   %sWhat to try:%s\n' "$B" "$OFF" >&2
        printf '     curl -fsS https://pypi.org/simple/ >/dev/null && echo reachable\n' >&2
        printf '     ping -c1 1.1.1.1\n' >&2
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

# ---------------------------------------------------------- preconditions ----
have() { command -v "$1" >/dev/null 2>&1; }

SYSTEM_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
on_system_path() { # every user has to find it, not just whoever is running this
  # `command` is a shell builtin, so it needs a shell: env cannot exec it.
  env -i PATH="$SYSTEM_PATH" sh -c 'command -v "$1" >/dev/null 2>&1' _ "$1"
}

as_root() { if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi; }

require_command() { # require_command NAME "how to get it"
  have "$1" && return 0
  die "${1} is not installed, and this cannot go on without it" "$2"
}

require_writable() { # require_writable PATH
  local path="$1"
  [ -e "$path" ] || path="$(dirname -- "$path")"
  [ -w "$path" ] && return 0
  die "cannot write to ${path}" \
      "Run this as the user that owns it, or with sudo." \
      "Who owns it: $(stat -c '%U:%G %a' "$path" 2>/dev/null || echo unknown)"
}

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

# ------------------------------------------------------------- diagnosis ----
# A failing command usually says why in a way only somebody who has seen it before can read.
# `diagnose` matches what it printed against the handful of things that actually go wrong on a
# fresh server, and turns each into: what this means, how to check, how to fix.
diagnose() { # diagnose "<the command's output>"
  local text="$1" matched=0
  _explain() { # _explain "meaning" "how to check" "how to fix"...
    matched=1
    printf '\n   %sWhat this means:%s %s\n' "$B" "$OFF" "$1" >&2
    shift
    printf '   %sWhat to try:%s\n' "$B" "$OFF" >&2
    local line
    for line in "$@"; do printf '     %s\n' "$line" >&2; done
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
        "docs/INSTALL.md, 'Getting the code onto the box', has the whole flow." ;;
    *"Permission denied"*|*"Operation not permitted"*)
      _explain "The account running this may not touch that file or directory." \
        "ls -ld <the path it named>    # who owns it, and what the mode is" \
        "id                            # who you are running as" \
        "Re-run with sudo, or give the path to the right user with chown." ;;
    *"address already in use"*|*"Address already in use"*)
      _explain "The port is taken by something else already running." \
        "sudo ss -ltnp | grep ':<port>'    # what is on it" \
        "Stop that, or set WEB_PORT in .env to a free port above 1024." ;;
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

# ------------------------------------------------- saying what will change ----
# Nothing that changes the machine should be a surprise. A script declares its system-level
# changes up front with `plan_item`, shows them with `show_plan`, and then says again, at the
# moment each one happens, what it is doing and why.

PLAN_WHAT=()
PLAN_WHY=()
PLAN_UNTOUCHED=()

plan_item()      { PLAN_WHAT+=("$1"); PLAN_WHY+=("$2"); }
plan_untouched() { PLAN_UNTOUCHED+=("$1"); }

plan_is_empty() { [ ${#PLAN_WHAT[@]} -eq 0 ]; }

show_plan() { # show_plan "heading"
  plan_is_empty && return 0
  head2 "${1:-What this will change on this machine}"
  local i
  for i in "${!PLAN_WHAT[@]}"; do
    printf '  %s%s%s
' "$B" "${PLAN_WHAT[i]}" "$OFF"
    printf '      %swhy: %s%s
' "$DIM" "${PLAN_WHY[i]}" "$OFF"
    log_line "plan: ${PLAN_WHAT[i]} :: ${PLAN_WHY[i]}"
  done
  if [ ${#PLAN_UNTOUCHED[@]} -gt 0 ]; then
    printf '
  %sIt does not touch:%s
' "$DIM" "$OFF"
    local item
    for item in "${PLAN_UNTOUCHED[@]}"; do
      printf '      %s· %s%s
' "$DIM" "$item" "$OFF"
    done
  fi
  printf '
'
}

# Announce one system-level change as it happens: what, and why, in a sentence.
system_change() { # system_change "what" "why"
  printf '  %s→%s %s
' "$B" "$OFF" "$1"
  printf '    %s%s%s
' "$DIM" "$2" "$OFF"
  log_line "change: $1 :: $2"
}

# ------------------------------------------------------------- questions ----
# Two different questions, deliberately kept apart:
#
#   confirm  — a preference, where --yes means "take the default you offered".
#   approve  — an action that needs someone to say so, where --yes means yes. With no terminal
#              and no --yes there is nobody to ask, so it is a no.
approve() { # approve "question"
  local question="$1" reply
  if [ "${ASSUME_YES:-0}" = 1 ]; then
    note "${question} — yes, because --yes was given."
    return 0
  fi
  if [ ! -t 0 ]; then
    warn "${question}"
    note "There is no terminal here to answer, so the answer is no. Pass --yes if you mean it."
    return 1
  fi
  read -r -p "${question} [y/N]: " reply || reply=""
  case "$reply" in [Yy]*|yes) return 0 ;; *) return 1 ;; esac
}

confirm() { # confirm "question" yes|no  - honours ASSUME_YES and a missing terminal
  local question="$1" default="${2:-yes}" reply
  if [ "${ASSUME_YES:-0}" = 1 ] || [ ! -t 0 ]; then [ "$default" = yes ]; return; fi
  read -r -p "$question [$([ "$default" = yes ] && echo 'Y/n' || echo 'y/N')]: " reply || reply=""
  reply="${reply:-$default}"
  case "$reply" in [Yy]*|yes) return 0 ;; *) return 1 ;; esac
}

# --------------------------------------------------------- which version ----
# While the newest version in CHANGELOG.md is still being built, its heading says so
# ("## v0.1.0 — in progress") and an install follows the default branch, where it is being
# built. Once it is released the heading carries a date instead, and an install follows the
# release tags. Either way, an upgrade only ever moves forward.

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
