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
  BADGE=$'\033[1;30;43m'; BADGE_G=$'\033[1;30;42m'; BADGE_R=$'\033[1;37;41m'; OFF=$'\033[0m'
else
  B=""; DIM=""; RED=""; YEL=""; GRN=""; CYN=""; BADGE=""; BADGE_G=""; BADGE_R=""; OFF=""
fi
if _wants_colour 2; then
  E_B=$'\033[1m'; E_DIM=$'\033[2m'; E_RED=$'\033[31m'; E_YEL=$'\033[33m'; E_CYN=$'\033[36m'; E_OFF=$'\033[0m'
else
  E_B=""; E_DIM=""; E_RED=""; E_YEL=""; E_CYN=""; E_OFF=""
fi

# The marks that say how a line went. They differ in shape as well as colour, so a screen with no
# colour reads the same. FAMILYDB_ASCII=1 is for a terminal that cannot draw the others.
# Locale decides whether the glyphs below can be drawn: a person at a terminal whose locale is not
# UTF-8 would be shown the bytes of them. A pipe or a log is not asked, since it is read elsewhere.
_utf8_locale() {
  case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *[Uu][Tt][Ff]-8*|*[Uu][Tt][Ff]8*) return 0 ;; esac
  return 1
}
# shellcheck disable=SC2034  # some are read only by the scripts that source this file.
if [ -n "${FAMILYDB_ASCII:-}" ] || { [ -z "${FAMILYDB_UNICODE:-}" ] && [ -t 1 ] && ! _utf8_locale; }; then
  S_OK='+'; S_WARN='!'; S_BAD='x'; S_GO='>'; S_DOT='-'; S_RULE='-'; S_TODO='[ ]'; S_OFF='o'; S_TO='->'; S_ELLIPSIS='...'; S_SECTION='>'
  BAR_FULL='#'; BAR_EMPTY='-'; BAR_PULSE_A='='; BAR_PULSE_B='#'
  F_TL='+'; F_TR='+'; F_BL='+'; F_BR='+'; F_H='='; F_BOX='#'
  SPIN_FRAMES=('|' '/' '-' '\')
else
  S_OK='✓'; S_WARN='!'; S_BAD='✗'; S_GO='→'; S_DOT='·'; S_RULE='─'; S_TODO='☐'; S_OFF='○'; S_TO='→'; S_ELLIPSIS='…'; S_SECTION='▸'
  BAR_FULL='█'; BAR_EMPTY='░'; BAR_PULSE_A='▓'; BAR_PULSE_B='▒'
  F_TL='╔'; F_TR='╗'; F_BL='╚'; F_BR='╝'; F_H='═'; F_BOX='■'
  SPIN_FRAMES=('|' '/' '-' '\')
fi

# What a command prints under a heading can be indented with this; `head2` and `finish` go back to the margin.
INDENT=""
WARNED=()   # every warning this run said, for the recap at the end
SCRIPT_STARTED=$SECONDS

say()   { printf '%s\n' "$*"; }
head2() { INDENT=""; printf '\n%s%s%s\n' "$B" "$*" "$OFF"; log_line "== $*"; }
note()  { printf '%s%s%s%s\n' "$INDENT" "$DIM" "$*" "$OFF"; log_line "-- $*"; }
ok()    { _ok_line "$*" ""; }
_ok_line() { # _ok_line TEXT [TIME] - a tick, what was done with its first word bold, and how long it took at the right edge
  local text="$1" took="${2:-}" first rest="" pad=" " used width
  first="${text%% *}"
  [ "$first" = "$text" ] || rest=" ${text#* }"
  # "Backed up" is one verb.
  case "$rest" in " up "*) first="$first up"; rest="${rest# up}" ;; esac
  if [ -n "$took" ]; then
    width="$(ui_width)"
    used=$((${#INDENT} + 2 + ${#text} + ${#took}))
    [ "$used" -ge $((width - 1)) ] || printf -v pad '%*s' $((width - used)) ''
  fi
  printf '%s%s%s%s%s %s%s%s%s%s%s%s%s\n' "$INDENT" "$B" "$GRN" "$S_OK" "$OFF" "$B" "$first" "$OFF" "$rest" \
    "${took:+$pad}" "${took:+$DIM}" "$took" "${took:+$OFF}"
  log_line "ok: ${text}${took:+ ($took)}"
}
warn()  {
  printf '%s%s%s%s%s %s\n' "$INDENT" "$E_B" "$E_YEL" "$S_WARN" "$E_OFF" "$*" >&2
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
  local line="$*"
  case "$line" in *$'\033'*) line="$(printf '%s' "$line" | sed $'s/\033\\[[0-9;]*m//g')" ;; esac
  printf '%s %s\n' "$(date -u '+%H:%M:%S')" "$line" >>"$LOG_FILE" 2>/dev/null || true
}

# --- Layout -------------------------------------------------------------------------------------
# What a command shows, in the order a person reads it: a banner (what, where, how), a plan (what
# it is about to do and why, for the installers), a line per thing done, and a last word that says
# how it went and what to do next. Everything here is for the eye: the transcript in the log file
# has the same facts, with no colour.

# The steps of a run, counted, so a bar can say how far along it is. A command that has a fixed
# list of steps says how many (progress_total) and how many are done before each (progress_to).
PROGRESS_TOTAL=0
PROGRESS_DONE=0
LIVE_LIMIT=""   # seconds a step is given, for a bar that fills toward it instead
progress_total() { PROGRESS_TOTAL="$1"; PROGRESS_DONE=0; }
progress_to() { PROGRESS_DONE="$1"; }

_bar() { # _bar VAR WIDTH DONE TOTAL FRAME COLOUR PULSE [DIM OFF] - [█████▓▒▓░░░░]: done, the one under way (pulsing), the rest
  local name="$1" width="$2" done_n="$3" total="$4" frame="$5" colour="$6" pulse="$7" dim="${8-$DIM}" off="${9-$OFF}"
  local cells active i filled="" rest=""
  [ "$total" -gt 0 ] || total=1
  [ "$done_n" -le "$total" ] || done_n=$total
  cells=$((width * done_n / total))
  active=0
  if [ "$pulse" = 1 ] && [ "$done_n" -lt "$total" ]; then
    active=$((width / total))
    [ "$active" -ge 1 ] || active=1
    [ $((cells + active)) -le "$width" ] || active=$((width - cells))
  fi
  for ((i = 0; i < cells; i++)); do filled+="$BAR_FULL"; done
  for ((i = 0; i < active; i++)); do
    if (((i + frame) % 2)); then filled+="$BAR_PULSE_A"; else filled+="$BAR_PULSE_B"; fi
  done
  for ((i = cells + active; i < width; i++)); do rest+="$BAR_EMPTY"; done
  printf -v "$name" '%s%s%s%s%s%s' "$colour" "$filled" "$off" "$dim" "$rest" "$off"
}

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
    ok)   mark="${B}${GRN}${S_OK}${OFF} " ;;
    warn) mark="${B}${YEL}${S_WARN}${OFF} " ;;
    bad)  mark="${B}${RED}${S_BAD}${OFF} " ;;
    off)  mark="${DIM}${S_OFF}${OFF} " ;;
  esac
  printf -v pad '%*s' $((${#base} + 15)) ''
  WRAP_FIRST="$(printf '%s%s%s%-12s%s ' "$base" "$mark" "$DIM" "$1" "$OFF")" wrap "$pad" "" "$2"
  log_line "   $1: $2"
}

# One line, like the title bar of an old DOS window, with where it is on the right: it replaces the
# heading and the rule under it, so it costs nothing in height.
banner() { # banner "Upgrade" ["where, and how it runs"]
  INDENT=""
  local width detail="${2:-}" base right fill bar="" i out frame="${DIM}${CYN}"
  width="$(ui_width)"
  base=$((19 + ${#1}))                      # "╔═[■]═ FamilyDB ═ <name> " before the fill
  if [ -n "$detail" ]; then
    [ $((base + ${#detail} + 6)) -le "$width" ] \
      || detail="${S_ELLIPSIS}${detail: -$((width - base - 6 - ${#S_ELLIPSIS}))}"
    right=$((${#detail} + 4))               # " <detail> ═╗"
  else
    right=2
  fi
  fill=$((width - base - right))
  [ "$fill" -ge 1 ] || fill=1
  for ((i = 0; i < fill; i++)); do bar+="$F_H"; done
  out="${frame}${F_TL}${F_H}[${F_BOX}]${F_H}${OFF} ${B}FamilyDB${OFF} ${frame}${F_H}${OFF} ${B}${CYN}${1}${OFF} ${frame}${bar}${OFF}"
  if [ -n "$detail" ]; then
    out="${out} ${DIM}${detail}${OFF} ${frame}${F_H}${F_TR}${OFF}"
  else
    out="${out}${frame}${F_H}${F_TR}${OFF}"
  fi
  printf '\n%s\n' "$out"
  log_line "== $1 ${2:-}"
  if [ "${DRY_RUN:-0}" = 1 ]; then
    printf '  %s[ DRY RUN ]%s %sNothing below is done; it only shows what would be.%s\n' "$BADGE" "$OFF" "$B" "$OFF"
  fi
}

# The foot of the window: the run's bar when it had steps to count, full when every one ran and short,
# and in the colour of what went wrong, where a run that stopped got to. FRAME, DIM and OFF are the
# colours of the stream it is for, so a copy on stderr follows stderr's rules.
frame_bottom() { # frame_bottom STATE COLOUR [FRAME DIM OFF]
  local state="$1" colour="$2" frame="${3-${DIM}${CYN}}" dim="${4-$DIM}" off="${5-$OFF}"
  local width i fill="" meter="" done_n pct barw label
  width="$(ui_width)"
  if [ "$PROGRESS_TOTAL" -gt 0 ]; then
    done_n="$PROGRESS_TOTAL"
    [ "$state" != bad ] || done_n="$PROGRESS_DONE"
    pct=$((100 * done_n / PROGRESS_TOTAL))
    label=" ${pct}%  ${done_n}/${PROGRESS_TOTAL} "
    barw=$((width - ${#label} - 5))
    [ "$barw" -le 40 ] || barw=40
    [ "$barw" -ge 8 ] || barw=8
    _bar meter "$barw" "$done_n" "$PROGRESS_TOTAL" 0 "$colour" 0 "$dim" "$off"
    for ((i = 0; i < width - barw - ${#label} - 5; i++)); do fill+="$F_H"; done
    printf '%s%s%s[%s%s%s]%s%s%s%s%s%s%s\n' "$frame" "$F_BL" "$F_H" "$off" "$meter" "$frame" "$off" "$dim" "$label" "$off" "$frame" "${fill}${F_BR}" "$off"
  else
    for ((i = 0; i < width - 2; i++)); do fill+="$F_H"; done
    printf '%s%s%s%s\n' "$frame" "$F_BL" "${fill}${F_BR}" "$off"
  fi
}

_verdict_badge() { # _verdict_badge ok|warn|bad - [ OK ], [WARN], [FAIL]: a block of colour on a terminal, brackets without one
  local text colour
  case "$1" in
    ok)   text=" OK "; colour="$BADGE_G" ;;
    warn) text="WARN"; colour="$BADGE" ;;
    *)    text="FAIL"; colour="$BADGE_R" ;;
  esac
  if [ -n "$colour" ]; then printf '%s %s %s' "$colour" "$text" "$OFF"; else printf '[%s]' "$text"; fi
}

FINISH_BAD=0   # set by a last line that says it failed, so the script can exit with it
FINISH_EMBEDDED=0   # 1 while one command runs inside another: its last word is one line, and the outer one has the last
FINISH_LAST=""      # how that line went: ok, warn or bad
# shellcheck disable=SC2034  # FINISH_BAD is read by the scripts that source this file.
finish() { # finish ok|warn|bad "Headline" - the last word: how it went, with the time it took
  local state="$1" headline="$2" colour count=${#WARNED[@]} took
  INDENT=""
  if [ "${FINISH_EMBEDDED:-0}" = 1 ]; then
    FINISH_LAST="$state"
    case "$state" in ok) colour="$GRN"; took="$S_OK" ;; warn) colour="$YEL"; took="$S_WARN" ;; *) colour="$RED"; took="$S_BAD" ;; esac
    printf '%s%s%s%s %s\n' "$B" "$colour" "$took" "$OFF" "$headline"
    log_line "== result: $state: $headline"
    return 0
  fi
  if [ "${DRY_RUN:-0}" = 1 ] && [ "$state" != bad ]; then
    state=ok
    headline="Dry run finished: nothing was changed"
  fi
  [ "$state" != ok ] || [ "$count" -eq 0 ] || state=warn
  case "$state" in
    ok)   colour="$GRN" ;;
    warn) colour="$YEL"
          [ "$count" -eq 0 ] || headline="${headline}, with ${count} warning$([ "$count" -eq 1 ] || echo s)" ;;
    *)    colour="$RED"; FINISH_BAD=1 ;;
  esac
  took=$((SECONDS - SCRIPT_STARTED))
  printf '\n'
  frame_bottom "$state" "$colour"
  printf '%s %s%s%s' "$(_verdict_badge "$state")" "$B" "$headline" "$OFF"
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

repo_web_base() { # repo_web_base REMOTE - https://github.com/owner/repo for a GitHub remote, else nothing
  local rest
  case "$1" in
    git@github.com:*) rest="${1#git@github.com:}" ;;
    ssh://git@github.com/*) rest="${1#ssh://git@github.com/}" ;;
    https://github.com/*) rest="${1#https://github.com/}" ;;
    *) return 0 ;;
  esac
  rest="${rest%/}"
  printf 'https://github.com/%s' "${rest%.git}"
}

# TEXT as a link a terminal can click (the escape sequence most of them understand, and the rest
# ignore), only where a person is looking at one: never in a pipe, a log or a mail.
hyperlink() { # hyperlink URL TEXT
  if [ -n "$1" ] && [ -n "$CYN" ] && [ -t 1 ] && [ -z "${FAMILYDB_NO_LINKS:-}" ]; then
    printf '\033]8;;%s\a%s\033]8;;\a' "$1" "$2"
  else
    printf '%s' "$2"
  fi
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
  local what="$1" parent="$2" i=0 start=$SECONDS max elapsed meter="" counter="" room
  # Beside the words: the run's bar when it has steps to count, a bar filling toward the time a step
  # is given when there is one, and otherwise only the seconds.
  room=$(( $(ui_width) - ${#INDENT} - 14 ))
  if [ -n "$LIVE_LIMIT" ]; then room=$((room - 28)); elif [ "$PROGRESS_TOTAL" -gt 0 ]; then room=$((room - 34)); fi
  max=$room
  [ "${#what}" -le "$max" ] || what="${what:0:$((max - 3))}${S_ELLIPSIS}"
  while kill -0 "$parent" 2>/dev/null; do
    elapsed=$((SECONDS - start))
    if [ -n "$LIVE_LIMIT" ]; then
      _bar meter 14 "$elapsed" "$LIVE_LIMIT" "$i" "$CYN" 0
      counter="${elapsed}s/${LIVE_LIMIT}s"
      printf '\r%s%s%s%s [%s] %s%-8s%s %s\033[K' "$INDENT" "$CYN" "${SPIN_FRAMES[i % ${#SPIN_FRAMES[@]}]}" "$OFF" \
        "$meter" "$DIM" "$counter" "$OFF" "$what"
    elif [ "$PROGRESS_TOTAL" -gt 0 ]; then
      _bar meter 20 "$PROGRESS_DONE" "$PROGRESS_TOTAL" "$i" "$CYN" 1
      counter="$((PROGRESS_DONE + 1))/${PROGRESS_TOTAL}"
      printf '\r%s%s%s%s [%s] %s%3d%%  %-4s%s %s %s%s%s\033[K' "$INDENT" "$CYN" "${SPIN_FRAMES[i % ${#SPIN_FRAMES[@]}]}" "$OFF" \
        "$meter" "$DIM" $((100 * PROGRESS_DONE / PROGRESS_TOTAL)) "$counter" "$OFF" "$what" "$DIM" "$(fmt_secs "$elapsed")" "$OFF"
    else
      printf '\r%s%s%s%s %s %s%s%s\033[K' "$INDENT" "$CYN" "${SPIN_FRAMES[i % ${#SPIN_FRAMES[@]}]}" "$OFF" \
        "$what" "$DIM" "$(fmt_secs "$elapsed")" "$OFF"
    fi
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
LEDGER_DIR="${FAMILYDB_LEDGER_DIR:-/var/lib/familydb-install}"   # the override is for tests
LEDGER="${LEDGER_DIR}/ledger"
# Where the install's SSH keeps GitHub's host key, rather than root's own known_hosts.
# shellcheck disable=SC2034  # read by bootstrap.sh, which sources this
KNOWN_HOSTS="${LEDGER_DIR}/known_hosts"

# Only a root install changes the system; a run as somebody else is a development checkout and
# must not ask for a sudo password.
_ledger_on() { [ "$(id -u)" = 0 ] && [ "${DRY_RUN:-0}" != 1 ]; }

# One command that changes an install at a time: two upgrades from two terminals, or the nightly
# backup landing while a restore runs, would each work on what the other is changing. The lock is
# held on an open file for as long as the process (and anything it started) lives, so there is no
# stale lock to clear. A reader (status, check, logs) takes none.
LOCK_FILE="${FAMILYDB_LOCK_FILE:-${LEDGER_DIR}/maintain.lock}"
take_lock() { # take_lock WHAT - or die naming the command that holds it
  local file="$LOCK_FILE" holder
  have flock || return 0
  if ! { mkdir -p "$(dirname -- "$file")" && exec 9>>"$file"; } 2>/dev/null; then
    # Not root, so not a server: a lock of this user's own, for this install alone, keeps two
    # of their runs apart without two installs (the tests run many at once) sharing one.
    file="${TMPDIR:-/tmp}/familydb-maintain-$(id -u)-$(printf '%s' "${TARGET:-}" | cksum | cut -d' ' -f1).lock"
    exec 9>>"$file" 2>/dev/null || return 0
  fi
  if ! flock -n 9; then
    holder="$(head -1 "$file" 2>/dev/null || true)"
    die "another maintain.sh is already working on ${TARGET:-this install}${holder:+: ${holder}}" \
        "Wait for it to finish, then run this again. Nothing was changed."
  fi
  printf '%s (pid %s, since %s)\n' "$1" "$$" "$(date '+%Y-%m-%d %H:%M')" >"$file" 2>/dev/null || true
  log_line "lock: $1"
}

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

UNDO_SAID=""   # an undo command that wants to be reported in its own words sets this
_run_undo() {
  [ ${#UNDO[@]} -gt 0 ] || return 0
  # Taken off the list before any runs: an undo that fails inside a step would otherwise run the
  # list again from inside itself.
  local -a todo=("${UNDO[@]}")
  UNDO=()
  printf '\n%sPutting things back%s\n' "$E_B" "$E_OFF" >&2
  local i
  for (( i=${#todo[@]}-1 ; i>=0 ; i-- )); do
    log_line "undo: ${todo[i]}"
    UNDO_SAID=""
    if eval "${todo[i]}" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      printf '  %s%s%s %s\n' "$E_B" "$S_OK" "$E_OFF" "${UNDO_SAID:-undone: ${todo[i]}}" >&2
    else
      printf '  %scould not undo:%s %s\n' "$E_YEL" "$E_OFF" "${UNDO_SAID:-${todo[i]}}" >&2
    fi
  done
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

# Where a run that did not finish got to, drawn before the words on what went wrong.
_where_it_stopped() {
  [ "$PROGRESS_TOTAL" -gt 0 ] || return 0
  printf '\n' >&2
  frame_bottom bad "$E_RED" "${E_DIM}${E_CYN}" "$E_DIM" "$E_OFF" >&2
}

die() { # die MESSAGE [MORE...] - a failure we diagnosed ourselves
  EXPLAINED=1
  INDENT=""
  _where_it_stopped
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
  [ "$1" -lt 3 ] || fmt_secs "$1"
}

_failure() { # _failure HEADLINE STATUS OUTPUT COMMAND LINES LABEL - what stopped, and what it said
  INDENT=""
  _where_it_stopped
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

SYSTEM_PATH="${FAMILYDB_SYSTEM_PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"   # the override is for tests
on_system_path() { # every user has to find it, not just whoever is running this
  # `command` is a shell builtin, so it needs a shell: env cannot exec it.
  env -i PATH="$SYSTEM_PATH" sh -c 'command -v "$1" >/dev/null 2>&1' _ "$1"
}

as_root() { if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi; }

# uv keeps its cache and the Python it fetches inside the install, in the same two places on every
# path (install, upgrade, doctor, rescue). A sync that keeps the virtualenv does not care, but one
# that builds it again (the doctor's rebuild, a deleted .venv, a newer Python wanted) and is told
# nothing does not find the Python the installer fetched: on a server whose own Python is too old it
# fetches another into the caller's home and builds on that, which under /root the service account
# cannot run, and which removing the install would not remove.
uv_vars() { # uv_vars DIR - the environment uv runs with for the install at DIR, one assignment a line
  printf 'UV_CACHE_DIR=%s/.cache/uv\nUV_PYTHON_INSTALL_DIR=%s/.local/share/uv/python\n' "$1" "$1"
}
uv_sync() { # uv_sync DIR - install the packages uv.lock pins into DIR/.venv, as root
  local -a vars
  mapfile -t vars < <(uv_vars "$1")
  as_root env "PATH=${SYSTEM_PATH:-$PATH}" "${vars[@]}" uv sync --frozen --no-dev --project "$1"
}
uv_sync_line() { # uv_sync_line DIR - the same, as one line a person can paste
  printf 'sudo env %s uv sync --frozen --no-dev --project %s' "$(uv_vars "$1" | tr '\n' ' ' | sed 's/ $//')" "$1"
}

# .env is read the way the program reads it (python-dotenv), so that what the script decides from
# a value is what the program does with it: `export` and spaces around = are allowed, a value in
# single quotes is taken as written, one in double quotes with \" and \\ undone, a bare one ends at
# " #" and loses trailing spaces, the last line for a name wins, and Windows line ends are ignored.
env_value() { # env_value FILE KEY - KEY's value in FILE as the program sees it; empty when unset
  as_root cat "$1" 2>/dev/null | env LC_ALL=C awk -v key="$2" -v sq="'" '
    { sub(/\r$/, "") }
    /^[ \t]*(export[ \t]+)?[A-Za-z_][A-Za-z0-9_]*[ \t]*=/ {
      line = $0
      sub(/^[ \t]*(export[ \t]+)?/, "", line)
      name = line
      sub(/[ \t]*=.*$/, "", name)
      if (name != key) next
      v = line
      sub(/^[^=]*=[ \t]*/, "", v)
      q = substr(v, 1, 1)
      if (q == "\"" || q == sq) {
        out = ""
        for (i = 2; i <= length(v); i++) {
          c = substr(v, i, 1)
          if (q == "\"" && c == "\\" && i < length(v)) {
            n = substr(v, i + 1, 1)
            if (n == "\"" || n == "\\") { out = out n; i++; continue }
          }
          if (c == q) break
          out = out c
        }
        found = out
      } else {
        sub(/[ \t]+#.*$/, "", v)
        sub(/[ \t]+$/, "", v)
        found = v
      }
      seen = 1
    }
    END { if (seen) printf "%s", found }' || true
}

quote_env() { # quote_env VALUE -> how that value must be written so .env reads it back whole
  # A bare value loses everything from '#' and any trailing space: a password with either would
  # silently change. Single quotes are literal to python-dotenv, systemd and compose alike; a
  # value with an apostrophe falls back to double quotes.
  local value="$1"
  case "$value" in
    "") printf '' ;;
    *[!A-Za-z0-9_.:/@+,=-]*)
      case "$value" in
        *\'*)
          case "$value" in
            *[\$\`\\]*)
              warn "a value with both an apostrophe and one of \$ \` \\ cannot be stored safely; edit .env by hand if this one matters"
              ;;
          esac
          printf '"%s"' "$(printf '%s' "$value" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
          ;;
        *) printf "'%s'" "$value" ;;
      esac
      ;;
    *) printf '%s' "$value" ;;
  esac
}

env_file_write() { # env_file_write FILE KEY VALUE - set KEY in FILE as root, keeping its owner and mode
  # The last line that sets the key is the one the program reads, so that is the one replaced;
  # a missing key is added at the end, on a line of its own whether or not the file ended with
  # one. The value goes through the environment, where awk reads no escapes in it. The file is
  # rewritten beside itself and moved into place, so a failure part-way leaves it as it was.
  local file="$1" tmp
  case "$3" in *$'\n'*) die "${2} contains a line break, which .env cannot hold. Use a value on one line." ;; esac
  tmp="${file}.tmp.$$"
  if as_root test -f "$file"; then
    as_root cp -p "$file" "$tmp"
  else
    # A new one is the service account's to read, like the one the installer writes.
    as_root install -m 600 ${SERVICE_USER:+-o "$SERVICE_USER"} /dev/null "$tmp"
  fi
  as_root cat "$file" 2>/dev/null | KEY="$2" WRITTEN="$(quote_env "$3")" env LC_ALL=C awk '
    { lines[NR] = $0; probe = $0; sub(/\r$/, "", probe)
      if (probe ~ "^[ \t]*(export[ \t]+)?" ENVIRON["KEY"] "[ \t]*=") last = NR }
    END {
      for (i = 1; i <= NR; i++) {
        if (i == last) print ENVIRON["KEY"] "=" ENVIRON["WRITTEN"]; else print lines[i]
      }
      if (!last) print ENVIRON["KEY"] "=" ENVIRON["WRITTEN"]
    }' | as_root tee "$tmp" >/dev/null \
    && as_root mv -f "$tmp" "$file" \
    || { as_root rm -f "$tmp"; die "could not write ${file}" "Nothing in it was changed."; }
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
    printf '\n  %sIt does not touch:%s\n' "$DIM" "$OFF"
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
  # Nobody is there to answer, so nothing was agreed to: that is a failure, not a quiet no, so a
  # cron job or a script that forgot --yes does not read "nothing was changed" as success.
  [ -t 0 ] || die "${question} There is no terminal here to answer, so nothing was done." \
                  "Pass --yes to answer yes without being asked."
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

# --- the health report ---------------------------------------------------------------------------
# One report from two sources: what this script can see of the machine (scripts/lib/doctor.sh, which
# works when the program does not) and `familydb doctor`, which prints
#   ▸ Heading
#   MARK name: detail          MARK is ✓ fine, ! worth a look, ✗ must be fixed, · not checked
#       → what to do
#   the verdict
# Rows are gathered first, so the names line up across the whole report, each heading can say how its
# checks went, and the summary can lead the eye to the first thing to fix.
#   doctor_begin; doctor_section "Install"; doctor_row bad "venv" "no interpreter" "sudo ... upgrade"
#   doctor_feed "$(familydb doctor)"; doctor_show all|problems|failures; doctor_summary
# A name is reported once, the first time: the machine's word on "service" beats the program's.
DOCTOR_FINE=0; DOCTOR_WARN=0; DOCTOR_BAD=0; DOCTOR_SKIP=0; DOCTOR_VERDICT=""
DOCTOR_FIRST=""; DOCTOR_FIRST_FIX=""
_DR_GROUP=(); _DR_STATE=(); _DR_NAME=(); _DR_DETAIL=(); _DR_FIX=()
_DR_SEEN=$'\n'
_DR_NOW=""

doctor_begin() {
  DOCTOR_FINE=0; DOCTOR_WARN=0; DOCTOR_BAD=0; DOCTOR_SKIP=0; DOCTOR_VERDICT=""
  DOCTOR_FIRST=""; DOCTOR_FIRST_FIX=""
  _DR_GROUP=(); _DR_STATE=(); _DR_NAME=(); _DR_DETAIL=(); _DR_FIX=()
  _DR_SEEN=$'\n'; _DR_NOW=""
}

doctor_section() { _DR_NOW="$1"; }   # doctor_section "Install" - the heading the next rows go under

# shellcheck disable=SC2034  # the counts and the first failure are read by the scripts that source this file.
doctor_row() { # doctor_row ok|warn|bad|skip NAME DETAIL [FIX]
  local state="$1" name="$2" detail="$3" fix="${4:-}"
  case "$_DR_SEEN" in *$'\n'"$name"$'\n'*) return 0 ;; esac
  _DR_SEEN+="${name}"$'\n'
  _DR_GROUP+=("$_DR_NOW"); _DR_STATE+=("$state"); _DR_NAME+=("$name"); _DR_DETAIL+=("$detail"); _DR_FIX+=("$fix")
  case "$state" in
    ok)   DOCTOR_FINE=$((DOCTOR_FINE + 1)) ;;
    warn) DOCTOR_WARN=$((DOCTOR_WARN + 1)) ;;
    bad)  DOCTOR_BAD=$((DOCTOR_BAD + 1))
          if [ -z "$DOCTOR_FIRST" ]; then DOCTOR_FIRST="${name}: ${detail}"; DOCTOR_FIRST_FIX="$fix"; fi ;;
    *)    DOCTOR_SKIP=$((DOCTOR_SKIP + 1)) ;;
  esac
}

# shellcheck disable=SC2034  # the verdict is read by the scripts that source this file.
doctor_feed() { # doctor_feed "the report" - rows from what `familydb doctor` printed
  local line state="" name="" detail="" fix="" last="" mark
  _doctor_pending() {
    [ -z "$state" ] || doctor_row "$state" "$name" "$detail" "$fix"
    state=""; name=""; detail=""; fix=""
  }
  while IFS= read -r line; do
    mark=""
    case "$line" in
      "▸ "*) _doctor_pending; doctor_section "${line#▸ }"; continue ;;
      "✓ "*) mark=ok; line="${line#✓ }" ;;
      "! "*) mark=warn; line="${line#! }" ;;
      "✗ "*) mark=bad; line="${line#✗ }" ;;
      "· "*) mark=skip; line="${line#· }" ;;
      "→ "*|"    →"*) fix="${line#*→}"; fix="${fix# }"; continue ;;
      "    fixed:"*) continue ;;
      "") _doctor_pending; continue ;;
      *) _doctor_pending; last="$line"; continue ;;
    esac
    _doctor_pending
    state="$mark"
    case "$line" in
      *": "*) name="${line%%: *}"; detail="${line#*: }" ;;
      *) name="${line%:}"; detail="" ;;
    esac
  done <<<"$1"
  _doctor_pending
  unset -f _doctor_pending
  case "$last" in [0-9]*|*"WARNING"*|*"ERROR"*) ;; *) DOCTOR_VERDICT="$last" ;; esac
}

_doctor_mark() { # _doctor_mark STATE - the mark in front of a row, in its colour
  case "$1" in
    ok)   printf '%s%s%s%s' "$B" "$GRN" "$S_OK" "$OFF" ;;
    warn) printf '%s%s%s%s' "$B" "$YEL" "$S_WARN" "$OFF" ;;
    bad)  printf '%s%s%s%s' "$B" "$RED" "$S_BAD" "$OFF" ;;
    *)    printf '%s%s%s' "$DIM" "$S_OFF" "$OFF" ;;
  esac
}

_doctor_width() { # the widest check name, kept between 8 and 24
  local w=8 i
  for i in "${!_DR_NAME[@]}"; do [ "${#_DR_NAME[i]}" -le "$w" ] || w="${#_DR_NAME[i]}"; done
  [ "$w" -le 24 ] || w=24
  printf '%s' "$w"
}

_doctor_line() { # _doctor_line INDEX NAMEWIDTH - a row, its detail wrapped under itself, its fix beneath
  local i="$1" w="$2" state label pad fixpad style=""
  state="${_DR_STATE[i]}"
  printf -v label '%-*s' "$w" "${_DR_NAME[i]}"
  printf -v pad '%*s' $((w + 6)) ''
  printf -v fixpad '%*s' 6 ''
  case "$state" in ok|skip) style="$DIM" ;; esac
  [ "$state" != bad ] || label="${B}${label}${OFF}"
  if [ -n "${_DR_DETAIL[i]}" ]; then
    WRAP_FIRST="  $(_doctor_mark "$state") ${label}  " wrap "$pad" "$style" "${_DR_DETAIL[i]}"
  else
    printf '  %s %s\n' "$(_doctor_mark "$state")" "$label"
  fi
  if [ -n "${_DR_FIX[i]}" ] && [ "$state" != ok ] && [ "$state" != skip ]; then
    WRAP_FIRST="${fixpad}${CYN}${S_TO}${OFF} " wrap "${fixpad}  " "$CYN" "${_DR_FIX[i]}"
  fi
  log_line "doctor: ${state} ${_DR_NAME[i]}: ${_DR_DETAIL[i]}${_DR_FIX[i]:+ -> ${_DR_FIX[i]}}"
}

_doctor_names() { # _doctor_names START END ROOM - the names of the fine checks in a section, as many as fit
  local i out="" name
  for ((i = $1; i < $2; i++)); do
    [ "${_DR_STATE[i]}" = ok ] || continue
    name="${_DR_NAME[i]}"
    [ $((${#out} + ${#name} + 3)) -le "$3" ] || { out="${out}${S_ELLIPSIS}"; break; }
    out="${out}${out:+ ${S_DOT} }${name}"
  done
  printf '%s' "$out"
}

_doctor_heading() { # _doctor_heading TITLE FINE WARN BAD - the section's name, a rule, and how its checks went
  local title="$1" fine="$2" warn="$3" bad="$4" total tally colour fill room
  total=$((fine + warn + bad))
  if [ "$total" -eq 0 ]; then tally="$S_DOT"; colour="$DIM"
  else
    tally="${fine}/${total}"
    if [ "$bad" -gt 0 ]; then colour="$RED"; elif [ "$warn" -gt 0 ]; then colour="$YEL"; else colour="$GRN"; fi
  fi
  room=$(( $(ui_width) - 5 - ${#title} - ${#tally} ))
  [ "$room" -ge 2 ] || room=2
  printf -v fill '%*s' "$room" ''
  printf '%s%s%s %s%s%s %s%s%s %s%s%s\n' "$CYN" "$S_SECTION" "$OFF" "$B" "$title" "$OFF" "$DIM" "${fill// /$S_RULE}" "$OFF" "$colour" "$tally" "$OFF"
}

_doctor_section() { # _doctor_section MODE START END WIDTH - one heading's rows
  local mode="$1" start="$2" end="$3" w="$4" i title fine=0 warn=0 bad=0 skip=0 names
  title="${_DR_GROUP[start]}"
  for ((i = start; i < end; i++)); do
    case "${_DR_STATE[i]}" in ok) fine=$((fine + 1)) ;; warn) warn=$((warn + 1)) ;; bad) bad=$((bad + 1)) ;; *) skip=$((skip + 1)) ;; esac
  done
  if [ "$mode" = issues ] && [ $((warn + bad)) -eq 0 ]; then
    for ((i = start; i < end; i++)); do log_line "doctor: ${_DR_STATE[i]} ${_DR_NAME[i]}: ${_DR_DETAIL[i]}"; done
    return 0
  fi
  if [ "$mode" = problems ] && [ $((warn + bad)) -eq 0 ]; then
    # Everything fine: one line that still says what was looked at.
    names="$(_doctor_names "$start" "$end" $(( $(ui_width) - 20 )))"
    if [ "$fine" -gt 0 ]; then
      printf '%s %s%-14s%s %s%s%s\n' "$(_doctor_mark ok)" "$B" "${title:-Checks}" "$OFF" "$DIM" "$names" "$OFF"
    else
      printf '%s %s%-14s%s %snot checked%s\n' "$(_doctor_mark skip)" "$B" "${title:-Checks}" "$OFF" "$DIM" "$OFF"
    fi
    for ((i = start; i < end; i++)); do log_line "doctor: ${_DR_STATE[i]} ${_DR_NAME[i]}: ${_DR_DETAIL[i]}"; done
    return 0
  fi
  [ -z "$title" ] || _doctor_heading "$title" "$fine" "$warn" "$bad"
  for ((i = start; i < end; i++)); do
    if [ "$mode" = problems ] || [ "$mode" = issues ]; then
      case "${_DR_STATE[i]}" in
        ok|skip) log_line "doctor: ${_DR_STATE[i]} ${_DR_NAME[i]}: ${_DR_DETAIL[i]}"; continue ;;
      esac
    fi
    _doctor_line "$i" "$w"
  done
  if [ "$mode" = problems ] && [ "$fine" -gt 0 ]; then
    names="$(_doctor_names "$start" "$end" $(( $(ui_width) - 20 )))"
    printf '  %s %s%s fine: %s%s\n' "$(_doctor_mark ok)" "$DIM" "$fine" "$names" "$OFF"
  fi
}

doctor_show() { # doctor_show all|problems|issues|failures - "problems" folds a section with nothing wrong into one line and shows only what is not fine in the rest; "issues" leaves the sections with nothing wrong out; "failures" only what must be fixed
  local mode="$1" w i n=${#_DR_STATE[@]} start
  w="$(_doctor_width)"
  if [ "$mode" = failures ]; then
    for i in "${!_DR_STATE[@]}"; do [ "${_DR_STATE[i]}" != bad ] || _doctor_line "$i" "$w"; done
    return 0
  fi
  i=0
  while [ "$i" -lt "$n" ]; do
    start=$i
    while [ "$i" -lt "$n" ] && [ "${_DR_GROUP[i]}" = "${_DR_GROUP[start]}" ]; do i=$((i + 1)); done
    _doctor_section "$mode" "$start" "$i" "$w"
  done
}

_tally_bar() { # _tally_bar VAR WIDTH FINE WARN BAD SKIP - a bar cut in the colours of how the checks went
  local name="$1" width="$2" f="$3" w="$4" b="$5" s="$6" total cf cw cb cs rest i out=""
  total=$((f + w + b + s)); [ "$total" -gt 0 ] || total=1
  cf=$((width * f / total)); cw=$((width * w / total)); cb=$((width * b / total)); cs=$((width * s / total))
  # What happened shows, however small.
  [ "$w" -eq 0 ] || [ "$cw" -ge 1 ] || cw=1
  [ "$b" -eq 0 ] || [ "$cb" -ge 1 ] || cb=1
  [ "$s" -eq 0 ] || [ "$cs" -ge 1 ] || cs=1
  rest=$((width - cf - cw - cb - cs))
  # What is left over (or taken back) goes to the biggest part.
  if [ "$f" -ge "$w" ] && [ "$f" -ge "$b" ] && [ "$f" -ge "$s" ]; then cf=$((cf + rest))
  elif [ "$w" -ge "$b" ] && [ "$w" -ge "$s" ]; then cw=$((cw + rest))
  elif [ "$b" -ge "$s" ]; then cb=$((cb + rest))
  else cs=$((cs + rest)); fi
  [ "$cf" -ge 0 ] || cf=0
  out="${GRN}"; for ((i = 0; i < cf; i++)); do out+="$BAR_FULL"; done
  out+="${OFF}${YEL}"; for ((i = 0; i < cw; i++)); do out+="$BAR_FULL"; done
  out+="${OFF}${RED}"; for ((i = 0; i < cb; i++)); do out+="$BAR_FULL"; done
  out+="${OFF}${DIM}"; for ((i = 0; i < cs; i++)); do out+="$BAR_EMPTY"; done
  printf -v "$name" '%s%s' "$out" "$OFF"
}

doctor_summary() { # doctor_summary - how many were checked, in one bar, and where to start
  local total=$((DOCTOR_FINE + DOCTOR_WARN + DOCTOR_BAD + DOCTOR_SKIP)) meter width=24
  _tally_bar meter "$width" "$DOCTOR_FINE" "$DOCTOR_WARN" "$DOCTOR_BAD" "$DOCTOR_SKIP"
  printf '\n'
  rule
  printf '  %sChecked %s%s  %s[%s%s]%s  %s%s%s%s' "$B" "$total" "$OFF" "$DIM" "$OFF" "$meter" "$DIM" "$GRN" "$DOCTOR_FINE" "$S_OK" "$OFF"
  [ "$DOCTOR_WARN" -eq 0 ] || printf '  %s%s%s%s' "$YEL" "$DOCTOR_WARN" "$S_WARN" "$OFF"
  [ "$DOCTOR_BAD" -eq 0 ] || printf '  %s%s%s%s' "$RED" "$DOCTOR_BAD" "$S_BAD" "$OFF"
  [ "$DOCTOR_SKIP" -eq 0 ] || printf '  %s%s%s%s' "$DIM" "$DOCTOR_SKIP" "$S_OFF" "$OFF"
  printf '\n'
  log_line "doctor: ${total} checked: ${DOCTOR_FINE} fine, ${DOCTOR_WARN} to look at, ${DOCTOR_BAD} to fix, ${DOCTOR_SKIP} not checked"
  if [ "$DOCTOR_BAD" -gt 0 ]; then
    printf '\n  %sStart here%s\n' "$B" "$OFF"
    WRAP_FIRST="  ${RED}${S_BAD}${OFF} " wrap "    " "" "$DOCTOR_FIRST"
    [ -z "$DOCTOR_FIRST_FIX" ] || WRAP_FIRST="    ${CYN}${S_TO}${OFF} " wrap "      " "$CYN" "$DOCTOR_FIRST_FIX"
  fi
}

show_doctor() { # show_doctor all|problems|failures|count "the report" - one report from `familydb doctor`, printed and counted
  doctor_begin
  doctor_feed "$2"
  [ "$1" = count ] || doctor_show "$1"
}

render_unit() { # render_unit TARGET USER [UNIT] - the service file for an install at TARGET running as USER, on stdout; UNIT is the file to start from
  local target="$1" user="$2" unit="${3:-$1/deploy/familydb.service}"
  [ -f "$unit" ] || return 1
  sed -e "s#/opt/familydb#${target}#g" -e "s#^User=.*#User=${user}#" -e "s#^Group=.*#Group=${user}#" "$unit" \
    | {
      # ProtectHome=true hides /home, so a checkout there would start empty; read-only keeps the
      # hardening, and ReadWritePaths still lets the data folder through.
      case "$target" in
        /home/*|/root/*) sed -e 's#^ProtectHome=true#ProtectHome=read-only#' ;;
        *) cat ;;
      esac
    }
}

# An install follows the default branch, so an upgrade brings in everything merged there whether or
# not a release has been tagged. The newest release tag is only the fallback for a remote that
# names no default branch. An upgrade only ever moves forward.

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
  if [ -n "$branch" ]; then
    printf 'branch %s\n' "$branch"
    return 0
  fi
  tag="$(as_root git -C "$1" tag -l 'v*' --sort=-v:refname 2>/dev/null | head -1 || true)"
  if [ -n "$tag" ]; then
    printf 'tag %s\n' "$tag"
  else
    printf 'none\n'
  fi
}

refresh_default_branch() { # refresh_default_branch DIR REMOTE - origin/HEAD follows the remote's default branch as it is now
  # A clone writes origin/HEAD once and a fetch never moves it, so a default branch renamed on
  # the remote would be followed by nobody: ask the remote each time, and leave it when it cannot say.
  local head
  head="$(as_root env GIT_TERMINAL_PROMPT=0 git -C "$1" ls-remote --symref "$2" HEAD 2>/dev/null \
    | sed -n 's|^ref: refs/heads/\(.*\)[[:space:]]HEAD$|\1|p' | head -1 || true)"
  [ -n "$head" ] || return 0
  as_root git -C "$1" rev-parse --verify --quiet "refs/remotes/origin/${head}" >/dev/null 2>&1 || return 0
  as_root git -C "$1" symbolic-ref refs/remotes/origin/HEAD "refs/remotes/origin/${head}" 2>/dev/null || true
}

fetch_trouble() { # fetch_trouble OUTPUT - what a failed fetch said, as one word: credential, network, missing, ownership or unknown
  case "$1" in
    *"dubious ownership"*) printf ownership ;;
    *"Authentication failed"*|*"could not read Username"*|*"terminal prompts disabled"*|*"Permission denied (publickey"*|\
    *"Repository not found"*|*"returned error: 401"*|*"returned error: 403"*|*"Invalid username or password"*|\
    *"Host key verification failed"*) printf credential ;;
    *"Could not resolve host"*|*"Couldn't connect"*|*"Could not connect"*|*"Connection timed out"*|*"Connection refused"*|\
    *"Network is unreachable"*|*"Failed to connect"*|*"No route to host"*|*"Operation timed out"*|*"Temporary failure"*|\
    *"ssh: connect to host"*|*"SSL"*|*"TLS"*|*"Connection reset"*|*"unexpected disconnect"*|*"RPC failed"*|\
    *"The remote end hung up"*) printf network ;;
    *"does not appear to be a git repository"*|*"not found"*|*"No such file"*) printf missing ;;
    *) printf unknown ;;
  esac
}

moves_forward() { # moves_forward DIR TARGET - succeeds when TARGET holds everything installed now, and more
  as_root git -C "$1" merge-base --is-ancestor HEAD "$2" \
    && ! as_root git -C "$1" merge-base --is-ancestor "$2" HEAD
}
