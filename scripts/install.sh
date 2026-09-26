#!/usr/bin/env bash
# FamilyDB installer. Works on a home server or a VPS, with Docker or a virtualenv.
# Safe to run again: it never overwrites a .env without asking, and never replaces your database,
# only migrates it.
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

VERSION="1.1"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV_FILE="${REPO_ROOT}/.env"
EXAMPLE_FILE="${REPO_ROOT}/.env.example"

MODE=""              # docker | venv
HAND_OVER_TO_SERVICE=0   # give data/ and .env to the familydb user, once the checks have run
SKIP_UNIT=0          # the service user cannot reach this checkout, so a unit would not start
SUDO=""              # set when the systemd unit is installed
ASSUME_YES=0         # --yes: take every default, ask nothing
NON_INTERACTIVE=0    # --non-interactive: never prompt; fail if something required is missing
DRY_RUN=0
SKIP_INSTALL=0       # --config-only: write .env and stop
LOCAL_ONLY=0         # --local-only: keep the page on this machine, reached over an SSH tunnel

run() { if [ "$DRY_RUN" = 1 ]; then note "[dry run] $*"; else "$@"; fi; }

usage() {
  cat <<'USAGE'
FamilyDB installer

  scripts/install.sh [options]

It asks at most one thing: a domain name for the web page, if it has one. Without one the page is
served over HTTPS at this server's own address. Everything else (yourself
and the family, the model and its key, Telegram, Google Calendar, where home is, what it may
spend) is set on the web page once it is running.

Options
  --mode docker|venv   How to run it. Default: docker when available, else a virtualenv.
                       (bootstrap.sh always passes this explicitly: venv unless told otherwise.)
  --yes                Accept every default.
  --non-interactive    Never prompt. Every answer comes from the environment (below).
  --config-only        Write .env and stop, installing nothing.
  --local-only         Keep the page on this machine, reached from your own computer over an
                       SSH tunnel, instead of on HTTPS at this server's address.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Answers can be supplied as environment variables, which is what --non-interactive reads:
  WEB_DOMAIN           the page's domain name; empty uses this server's own address
  WEB_PUBLIC_PORT      the port the page is served on over HTTPS: 443 unless given, or a
                       number from 1024 to 65535, or random, for one that scans rarely try
  WEB_PASSWORD         the first password into the page (12 characters or more); made up
                       when not given, and replaced by each person's own on the page
  ADMIN_NAME           the first family member (otherwise added on the Family page)
  BACKUPS              yes (the default) schedules a nightly backup; no leaves it to you
and, for a scripted build that wants them in .env rather than set on the page:
  PROVIDER  OPENAI_API_KEY  ANTHROPIC_API_KEY  GEMINI_API_KEY  TELEGRAM_BOT_TOKEN
  FAMILYDB_TZ  HOME_AREA  HOME_LAT  HOME_LON  WEATHER_UNITS  WEB_TOOLS_ENABLED
  WEB_HOST  WEB_PORT  DIGEST_CHAT_ID

Examples
  scripts/install.sh                          # one question, then install
  scripts/install.sh --yes                    # HTTPS at this address, a generated password
  WEB_DOMAIN=family.example.com ADMIN_NAME=Sam \
    scripts/install.sh --non-interactive --mode docker
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --mode=*) MODE="${1#*=}"; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --non-interactive) NON_INTERACTIVE=1; ASSUME_YES=1; shift ;;
    --config-only) SKIP_INSTALL=1; shift ;;
    --local-only) LOCAL_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done
case "$MODE" in ""|docker|venv) ;; *) die "--mode must be docker or venv, not '$MODE'" ;; esac
export ASSUME_YES DRY_RUN

log_to "/var/log/familydb-install.log"
enable_failure_reporting
on_failure_hint "Nothing after the failed step ran, and .env and the database were not touched by it. docs/INSTALL.md, under Troubleshooting, has a section on each failure."
again_hint "run it again: sudo bash ${REPO_ROOT}/scripts/install.sh"

# ----------------------------------------------------------------- input ----
ask() { # ask VAR "question" "default"
  local var="$1" question="$2" default="${3:-}" current reply
  current="${!var:-}"
  if [ -n "$current" ]; then printf -v "$var" '%s' "$current"; return 0; fi
  if [ "$ASSUME_YES" = 1 ] || [ ! -t 0 ]; then printf -v "$var" '%s' "$default"; return 0; fi
  if [ -n "$default" ]; then
    read -r -p "$question [$default]: " reply || reply=""
  else
    read -r -p "$question: " reply || reply=""
  fi
  printf -v "$var" '%s' "${reply:-$default}"
}

# --------------------------------------------------------------- helpers ----
quote_env() { # quote_env VALUE -> how that value must be written so .env reads it back whole
  # A bare value loses everything from a '#' onwards and any trailing space, so a password with
  # either in it silently becomes a different password. Single quotes are literal to all three
  # readers of this file (python-dotenv, systemd EnvironmentFile, docker compose env_file), and
  # a value with an apostrophe in it cannot use them, so that one falls back to double quotes.
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

set_env() { # set_env KEY VALUE
  local key="$1" value="$2" written line replaced=0
  [ "$DRY_RUN" = 1 ] && { note "would set $key"; return 0; }
  # One setting per line is the whole format; a value with a line break in it cannot be stored
  # here at all, and quietly storing half of it is worse than stopping.
  case "$value" in
    *$'\n'*) die "${key} contains a line break, which .env cannot hold. Use a value on one line." ;;
  esac
  written="$(quote_env "$value")"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # The temporary file holds the keys too, so it is owner-only before a byte goes into it.
    rm -f "${ENV_FILE}.tmp"
    (umask 077; : > "${ENV_FILE}.tmp")
    # Read and write by hand: awk -v would read a backslash in the value as an escape.
    while IFS= read -r line || [ -n "$line" ]; do
      if [ "$replaced" = 0 ] && [ "${line%%=*}" = "$key" ] && [ "$line" != "${line#*=}" ]; then
        printf '%s=%s\n' "$key" "$written"
        replaced=1
      else
        printf '%s\n' "$line"
      fi
    done < "$ENV_FILE" >> "${ENV_FILE}.tmp"
    mv "${ENV_FILE}.tmp" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$written" >> "$ENV_FILE"
  fi
}

service_can_reach_checkout() { # can the familydb user get to the files it has to run?
  # A home directory is closed to other users on most systems (0750), and no amount of unit
  # hardening changes that: the service would start into a path it cannot enter. /opt is the
  # documented home for exactly this reason.
  [ "$(id -un)" = familydb ] && return 0   # running as that user, from inside it: yes
  have sudo || return 0                    # no way to ask from here; assume the admin knows
  sudo -n true 2>/dev/null || return 0     # sudo would ask for a password; do not hang on it
  sudo -n -u familydb sh -c 'test -x "$1" && test -r "$1"' _ "$REPO_ROOT" 2>/dev/null
}

random_password() {
  if have openssl; then openssl rand -base64 18 | tr -d '/+=' | cut -c1-20
  elif [ -r /dev/urandom ]; then LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20
  else
    # A password made from the clock is guessable from the install time; better none at all.
    die "no source of randomness (openssl or /dev/urandom) to make a password with" \
        "Set WEB_PASSWORD yourself and run this again."
  fi
}

valid_host() { # an address to bind: an IP, or localhost. A typo means the page never serves.
  case "$1" in localhost|"") return 0 ;; esac
  python3 - "$1" <<'HOSTPY' 2>/dev/null
import ipaddress, sys
try:
    ipaddress.ip_address(sys.argv[1].strip("[]"))
except ValueError:
    sys.exit(1)
HOSTPY
}

valid_timezone() {
  [ -n "$1" ] || return 1
  [ -e "/usr/share/zoneinfo/$1" ] && return 0
  python3 - "$1" <<'PY' 2>/dev/null
import sys, zoneinfo
try:
    zoneinfo.ZoneInfo(sys.argv[1])
except Exception:
    sys.exit(1)
PY
}

detect_timezone() {
  local zone=""
  if [ -r /etc/timezone ]; then zone="$(tr -d '[:space:]' < /etc/timezone)"; fi
  if [ -z "$zone" ] && have timedatectl; then
    zone="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
  fi
  if [ -z "$zone" ] && [ -L /etc/localtime ]; then
    zone="$(readlink -f /etc/localtime | sed 's#.*/zoneinfo/##')"
  fi
  valid_timezone "$zone" && printf '%s' "$zone" || printf 'UTC'
}

look_up_place() { # look_up_place "Vancouver, WA" -> "lat lon label" on stdout, or nothing
  have curl || return 1
  local query response
  query="$(printf '%s' "$1" | sed 's/ /%20/g')"
  response="$(curl -fsS --max-time 10 \
    "https://geocoding-api.open-meteo.com/v1/search?name=${query}&count=1&language=en&format=json" \
    2>/dev/null)" || return 1
  printf '%s' "$response" | python3 -c '
import json, sys
try:
    hit = (json.load(sys.stdin).get("results") or [None])[0]
except Exception:
    sys.exit(1)
if not hit:
    sys.exit(1)
bits = [hit.get("name"), hit.get("admin1"), hit.get("country")]
print(hit["latitude"], hit["longitude"], ", ".join(b for b in bits if b))
' 2>/dev/null
}

# -------------------------------------------------------------- preflight ----
head2 "FamilyDB installer ${VERSION}"

# Everything below is relative to the checkout, and so is the default FAMILYDB_PATH, so the
# directory this was called from must not decide where the database lands.
cd "$REPO_ROOT"

[ -f "${REPO_ROOT}/pyproject.toml" ] || die "run this from a FamilyDB checkout (no pyproject.toml above scripts/)"
grep -q 'name = "familydb"' "${REPO_ROOT}/pyproject.toml" || die "${REPO_ROOT} does not look like FamilyDB"
[ -f "$EXAMPLE_FILE" ] || die "missing .env.example; the checkout is incomplete"
[ -w "$REPO_ROOT" ] || die "cannot write to ${REPO_ROOT}. Run as the user that owns it."

case "$(uname -s)" in
  Linux) ;;
  Darwin) note "macOS: fine for trying it out, but the service setup below is Linux only." ;;
  *) warn "$(uname -s) is untested. The Docker path is the more likely to work." ;;
esac

if [ -z "$MODE" ]; then
  if have docker && docker compose version >/dev/null 2>&1; then MODE=docker; else MODE=venv; fi
fi
note "Installing into ${REPO_ROOT} using the ${MODE} path."
if [ ! -t 0 ] && [ "$NON_INTERACTIVE" = 0 ] && [ "$ASSUME_YES" = 0 ]; then
  note "Not running from a terminal, so every question takes its default or the environment."
fi

if [ "$SKIP_INSTALL" = 1 ]; then
  plan_item "Write ${ENV_FILE}, readable only by its owner" \
    "your answers, including the API keys and the page password, are kept there"
else
  plan_item "Write ${ENV_FILE}, readable only by its owner" \
    "your answers, including the API keys and the page password, are kept there"
  if [ "$MODE" = docker ]; then
    plan_item "Build a Docker image called familydb:local" \
      "the bot and its dependencies, so nothing is installed into the system Python"
  else
    plan_item "Create a virtualenv at ${REPO_ROOT}/.venv with uv" \
      "the dependencies are installed there at the exact versions in uv.lock, and nowhere else"
  fi
  plan_item "Create ${REPO_ROOT}/data and the SQLite database inside it" \
    "everything the family tells it lives in that one file"
  if [ -n "${ADMIN_NAME:-}" ]; then
    plan_item "Add ${ADMIN_NAME} to the family list" \
      "the bot only answers people it knows; everyone else is added on the page"
  fi
  if [ "$MODE" = venv ] && [ "$LOCAL_ONLY" = 0 ]; then
    web_ports="80 and 443"
    case "${WEB_PUBLIC_PORT:-443}" in 443) ;; random) web_ports="80 and a port picked at random" ;; *) web_ports="80 and ${WEB_PUBLIC_PORT}" ;; esac
    plan_item "Put Caddy in front of the page, for HTTPS, and open ports ${web_ports} if ufw is on" \
      "so the page can be opened from any browser without a tunnel, and nothing crosses the network in the clear"
  fi
  if [ "$MODE" = venv ] && have systemctl && [ -d /run/systemd/system ]; then
    plan_item "Offer to create the 'familydb' user and write /etc/systemd/system/familydb.service" \
      "so it starts at boot and restarts if it stops; you are asked before this happens"
  fi
fi
plan_untouched "the system Python, your SSH configuration, and every other service"
plan_untouched "any database that is already here: an existing one is migrated, never replaced"
show_plan "What this installer changes"

if [ "$SKIP_INSTALL" = 1 ]; then
  note "Writing configuration only, so the ${MODE} tooling is not checked."
elif [ "$MODE" = docker ]; then
  have docker || die "docker not found. Install Docker, or re-run with --mode venv."
  docker compose version >/dev/null 2>&1 || die "the docker compose plugin is missing. Install it, or use --mode venv."
  if ! docker info >/dev/null 2>&1; then
    die "the Docker daemon is not reachable. Start it (systemctl start docker), or add yourself to the docker group, or use --mode venv."
  fi
else
  if ! have uv; then
    # The most common reason by far: uv was installed into somebody's home directory, so it is
    # on their PATH and on nobody else's. Say that, rather than "not installed", which sends
    # people off to install it a second time.
    if on_system_path uv; then
      die "uv is installed but not on this PATH" \
          "PATH is: ${PATH}" \
          "Run this with the system PATH, or use scripts/bootstrap.sh, which sorts this out."
    fi
    for home in /root "${SUDO_USER:+/home/${SUDO_USER}}"; do
      [ -n "$home" ] && [ -x "${home}/.local/bin/uv" ] && {
        die "uv is installed at ${home}/.local/bin/uv, where this account cannot see it" \
            "A tool in a home directory cannot be used by a service account. Install it for" \
            "everyone, then run this again:" \
            "  curl -LsSf https://astral.sh/uv/install.sh | sudo UV_INSTALL_DIR=/usr/local/bin sh" \
            "Or use scripts/bootstrap.sh, which does that for you."
      }
    done
    if [ "$NON_INTERACTIVE" = 1 ]; then
      die "uv is not installed, and this path needs it" \
          "Install it for every account on the machine:" \
          "  curl -LsSf https://astral.sh/uv/install.sh | sudo UV_INSTALL_DIR=/usr/local/bin sh" \
          "Or run scripts/bootstrap.sh, which installs it and everything else."
    fi
    say "This path needs uv, which manages the Python version and the virtualenv."
    if confirm "Install uv now (downloads and runs the official installer)?" yes; then
      have curl || die "curl is needed to install uv. Install curl, or install uv yourself."
      # Into /usr/local/bin, where the service account can see it, and nowhere else: no receipt
      # in a home directory and no line in anybody's shell profile.
      noting_new /usr/local/bin/uv
      noting_new /usr/local/bin/uvx
      run as_root sh -c 'curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL=/usr/local/bin sh'
      export PATH="/usr/local/bin:$PATH"
      have uv || die "uv still not on PATH. Open a new shell and run this script again."
    else
      die "uv is required for the virtualenv path. Use --mode docker instead."
    fi
  fi
  python_ok=0
  if have python3; then
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' && python_ok=1
  fi
  [ "$python_ok" = 1 ] || note "System Python is older than 3.11; uv will fetch a suitable one."
fi

free_mb="$(df -Pm "$REPO_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')" || free_mb=""
if [ -n "$free_mb" ] && [ "$free_mb" -lt 600 ]; then
  warn "only ${free_mb} MB free here; the install needs roughly 600 MB."
  confirm "Carry on anyway?" no || die "stopped: not enough disk space"
fi

# ------------------------------------------------------------------ .env ----
head2 "Configuration"

KEEP_ENV=0
if [ -f "$ENV_FILE" ]; then
  say "There is already a .env here."
  if [ "$NON_INTERACTIVE" = 1 ] || [ "${FROM_BOOTSTRAP:-0}" = 1 ]; then
    KEEP_ENV=1
    note "Keeping it as it is."
  elif confirm "Keep it and skip the questions?" yes; then
    KEEP_ENV=1
  else
    backup="${ENV_FILE}.$(date +%Y%m%d%H%M%S).bak"
    run cp "$ENV_FILE" "$backup"
    ok "Saved the old one as $(basename "$backup")"
  fi
fi

if [ "$KEEP_ENV" = 0 ]; then
  [ "$DRY_RUN" = 1 ] || { cp "$EXAMPLE_FILE" "$ENV_FILE"; chmod 600 "$ENV_FILE"; }

  say ""
  say "Almost everything is set on the web page once it is running: which model answers and its"
  say "key, Telegram, Google Calendar, where the family lives, and what it may spend a day. This"
  say "asks only what the page cannot answer for itself: how you will reach it."

  # A scripted build can still give any of these; they are written as given, and the page can
  # change them later. Asked for, none of them is: the page does it better.
  case "${PROVIDER:-}" in
    claude|Claude|anthropic) PROVIDER=anthropic ;;
    openai|OpenAI|OPENAI|gpt|GPT) PROVIDER=openai ;;
    gemini|Gemini|GEMINI|google|Google|GOOGLE) PROVIDER=gemini ;;
  esac
  for var in PROVIDER ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY HOME_AREA HOME_LAT HOME_LON \
             WEATHER_UNITS TELEGRAM_BOT_TOKEN DIGEST_CHAT_ID; do
    [ -n "${!var:-}" ] && set_env "$var" "${!var}"
  done
  if [ -n "${HOME_AREA:-}" ] && [ -z "${HOME_LAT:-}" ]; then
    if place="$(look_up_place "$HOME_AREA")"; then
      set_env HOME_LAT "$(printf '%s' "$place" | cut -d' ' -f1)"
      set_env HOME_LON "$(printf '%s' "$place" | cut -d' ' -f2)"
    fi
  fi
  # Looking ideas up is most of what makes a suggestion good, and the daily spending limit keeps
  # it bounded, so it starts on. The page turns it off.
  set_env WEB_TOOLS_ENABLED "${WEB_TOOLS_ENABLED:-true}"
  # The page's own chat can be spoken to from the first Thursday; a Telegram group cannot until
  # someone has written in it. Moved to Telegram on the page later.
  [ -z "${DIGEST_CHAT_ID:-}" ] && set_env DIGEST_CHAT_ID web

  FAMILYDB_TZ="${FAMILYDB_TZ:-$(detect_timezone)}"
  if ! valid_timezone "$FAMILYDB_TZ"; then
    warn "'${FAMILYDB_TZ}' is not an IANA zone name. Using $(detect_timezone)."
    FAMILYDB_TZ="$(detect_timezone)"
  fi
  set_env FAMILYDB_TZ "$FAMILYDB_TZ"
  note "Timezone: ${FAMILYDB_TZ}, from this machine. The settings page changes it."

  # --- the web page, which is how everything else gets set ---
  set_env WEB_ENABLED true
  say ""
  ADDRESS="$(this_address)"
  if [ "$LOCAL_ONLY" = 1 ] || [ "${WEB_DOMAIN:-}" = local ]; then
    WEB_DOMAIN=""
    note "The page stays on this machine, reached over an SSH tunnel, as asked."
  else
    if [ -z "${WEB_DOMAIN:-}" ]; then
      say ""
      if [ -n "$ADDRESS" ] && [ "$MODE" = venv ]; then
        say "The page will be at ${B}https://${ADDRESS}/${OFF}, this server's address, over HTTPS."
      fi
      say "If you have a domain name for it, pointed at this server, type it. Otherwise press Enter."
    fi
    ask WEB_DOMAIN "Domain name (optional)" ""
    WEB_DOMAIN="${WEB_DOMAIN#https://}"; WEB_DOMAIN="${WEB_DOMAIN#http://}"; WEB_DOMAIN="${WEB_DOMAIN%%/*}"
    WEB_DOMAIN="${WEB_DOMAIN%:*}"   # a port typed after it means nothing here: WEB_PUBLIC_PORT says
    if [ -n "$WEB_DOMAIN" ] && ! is_ipv4 "$WEB_DOMAIN" \
       && ! printf '%s' "$WEB_DOMAIN" | grep -Eq '^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'; then
      warn "'${WEB_DOMAIN}' does not look like a domain name, so the page uses this server's address."
      WEB_DOMAIN=""
    fi
    [ -n "$WEB_DOMAIN" ] || WEB_DOMAIN="$ADDRESS"
    if [ -n "$WEB_DOMAIN" ] && is_ipv4 "$WEB_DOMAIN" && [ "$MODE" = docker ]; then
      warn "With Docker the page needs a domain name to be on HTTPS; keeping it on this machine."
      note "docs/INSTALL.md, 'A domain name instead of the address', says how to give it one."
      WEB_DOMAIN=""
    fi
  fi
  # Another port than 443 when one is given: a number, or "random" (lib/https.sh says why).
  if [ -n "$WEB_DOMAIN" ] && [ -n "${WEB_PUBLIC_PORT:-}" ]; then
    if PUBLIC_PORT="$(choose_public_port "$WEB_PUBLIC_PORT" "${WEB_PORT:-8080}")"; then
      set_env WEB_PUBLIC_PORT "$PUBLIC_PORT"
    else
      warn "WEB_PUBLIC_PORT=${WEB_PUBLIC_PORT} will not do, so the page is on 443."
      PUBLIC_PORT=443
    fi
  fi
  if [ -n "$WEB_DOMAIN" ] && is_ipv4 "$WEB_DOMAIN"; then
    # Caddy in front, with a certificate for the address itself (see lib/https.sh). Never plain
    # HTTP on the open internet: that would send the family password in the clear.
    set_env WEB_DOMAIN "$WEB_DOMAIN"
    set_env WEB_TRUST_PROXY true
    ok "The page will be $(public_url "$WEB_DOMAIN")"
  elif [ -n "$WEB_DOMAIN" ]; then
    # Caddy can only get a certificate for a name that points here. Not a reason to stop, since
    # DNS may simply be catching up, but worth saying now rather than as a silent Caddy retry.
    resolved="$(getent ahostsv4 "$WEB_DOMAIN" 2>/dev/null | awk 'NR==1 {print $1}' || true)"
    if [ -z "$resolved" ]; then
      warn "${WEB_DOMAIN} does not resolve yet. Point an A record at this server; Caddy keeps trying."
    elif ! hostname -I 2>/dev/null | tr ' ' '\n' | grep -qx "$resolved"; then
      note "${WEB_DOMAIN} points at ${resolved}, which is not an address of this machine. Fine behind"
      note "a NAT or a load balancer; otherwise correct the DNS record before expecting HTTPS."
    fi
    set_env WEB_DOMAIN "$WEB_DOMAIN"
    # A proxy in front terminates HTTPS and says who the visitor really is.
    set_env WEB_TRUST_PROXY true
    # Compose reads this from .env, so every `docker compose up` brings Caddy up too.
    [ "$MODE" = docker ] && set_env COMPOSE_PROFILES tls
    ok "The page will be $(public_url "$WEB_DOMAIN") once the domain points here."
  fi
  if [ "$MODE" = docker ]; then
    WEB_HOST="${WEB_HOST:-0.0.0.0}"   # inside the container; the compose file keeps it to this machine
  else
    WEB_HOST="${WEB_HOST:-127.0.0.1}"
    valid_host "$WEB_HOST" || { warn "'${WEB_HOST}' is not an address to bind; using 127.0.0.1."; WEB_HOST=127.0.0.1; }
  fi
  WEB_PORT="${WEB_PORT:-8080}"
  if ! printf '%s' "$WEB_PORT" | grep -Eq '^[0-9]+$' || [ "$WEB_PORT" -lt 1025 ] || [ "$WEB_PORT" -gt 65535 ]; then
    warn "port must be a number between 1025 and 65535; using 8080."
    WEB_PORT=8080
  fi
  set_env WEB_HOST "$WEB_HOST"
  set_env WEB_PORT "$WEB_PORT"

  # Always a password: the page is where the keys are typed in. Twelve characters at least.
  if [ -n "${WEB_PASSWORD:-}" ] && [ "${#WEB_PASSWORD}" -lt 12 ]; then
    die "WEB_PASSWORD is ${#WEB_PASSWORD} characters; the page needs 12 or more."
  fi
  if [ -z "${WEB_PASSWORD:-}" ]; then
    WEB_PASSWORD="$(random_password)"
    say ""
    say "  A password to get into the page the first time: ${B}${WEB_PASSWORD}${OFF}"
    say "  The page then asks you to choose your own."
  fi
  set_env WEB_PASSWORD "$WEB_PASSWORD"

  if [ "$DRY_RUN" = 1 ]; then
    note "[dry run] would write $(basename "$ENV_FILE"), readable only by you"
  else
    chmod 600 "$ENV_FILE"
    ok "Wrote $(basename "$ENV_FILE") (readable only by you)."
  fi
fi

if [ "$SKIP_INSTALL" = 1 ]; then
  head2 "Done"
  say "Configuration written. Nothing installed, as asked."
  say "When you are ready to install for real: ${0}"
  exit 0
fi

# --------------------------------------------------------------- install ----
head2 "Installing"

run mkdir -p "${REPO_ROOT}/data"
# Every message the family sends is in there, and any key typed into the settings page.
run chmod 700 "${REPO_ROOT}/data"

# Both of these download a few hundred megabytes, which is where a new server most often fails:
# a network that is not up yet, a proxy, a full disk.
on_failure_hint "It never touches .env or the database twice, so running it again is safe."
if [ "$MODE" = docker ]; then
  retry 2 "Building the image" docker compose --project-directory "$REPO_ROOT" build
  FAMILYDB=(docker compose --project-directory "$REPO_ROOT" run --rm -T bot familydb)
  # The container runs as uid 1000 and needs to write the database into data/.
  if [ "$DRY_RUN" = 0 ] && ! chown -R 1000:1000 "${REPO_ROOT}/data" 2>/dev/null; then
    note "Could not give data/ to uid 1000. If the container cannot write, run:"
    note "  sudo chown -R 1000:1000 ${REPO_ROOT}/data"
  fi
else
  # uv's download cache and the Python it fetches stay inside the install, whoever runs this, so
  # removing the install removes them too.
  retry 3 "Installing the dependencies" env UV_CACHE_DIR="${REPO_ROOT}/.cache/uv" \
    UV_PYTHON_INSTALL_DIR="${REPO_ROOT}/.local/share/uv/python" \
    uv sync --frozen --no-dev --project "$REPO_ROOT"
  FAMILYDB=("${REPO_ROOT}/.venv/bin/familydb")
fi

runfamilydb() { if [ "$DRY_RUN" = 1 ]; then note "would run: familydb $*"; else "${FAMILYDB[@]}" "$@"; fi; }

head2 "Setting up the database"
step "Creating the database" runfamilydb db migrate

# --- the first family member ---
have_members=0
if [ "$DRY_RUN" = 0 ] && runfamilydb members list 2>/dev/null | grep -qv 'no members yet'; then
  have_members=1
fi
if [ "$have_members" = 0 ]; then
  # Not asked: the page's Family page adds the first person, as an admin, and its setup list
  # says so. A scripted install can still name them here.
  if [ -n "${ADMIN_NAME:-}" ]; then
    runfamilydb members add "$ADMIN_NAME" --role admin >/dev/null && ok "Added ${ADMIN_NAME} as an admin."
  else
    note "Add yourself, and then the family, on the page's Family page."
  fi
else
  ok "Family members already set up."
fi

# --- the service ---
if [ "$MODE" = venv ] && have systemctl && [ -d /run/systemd/system ]; then
  head2 "Running it as a service"
  if [ "$(id -u)" = 0 ] || have sudo; then
    if [ "${FROM_BOOTSTRAP:-0}" = 1 ] || confirm "Install the systemd unit so it starts on boot?" yes; then
      [ "$(id -u)" = 0 ] || SUDO="sudo"
      unit="${REPO_ROOT}/deploy/familydb.service"
      [ -f "$unit" ] || die "missing ${unit}"
      if [ "$DRY_RUN" = 1 ]; then
        note "would create the familydb user and install /etc/systemd/system/familydb.service"
        note "would give ${REPO_ROOT}/data and .env to that user"
      else
        # The unit runs as its own user, so create it here: an installed unit that cannot start
        # because the user it names does not exist is not an install, it is homework.
        if id familydb >/dev/null 2>&1; then
          ok "The familydb user already exists."
        elif $SUDO useradd --system --home-dir "$REPO_ROOT" --shell /usr/sbin/nologin familydb \
             2>/dev/null; then
          noting_user familydb
          ok "Created the familydb system user."
        else
          warn "Could not create the familydb user. Create it, or edit User= in the unit:"
          warn "  sudo useradd --system --home-dir ${REPO_ROOT} --shell /usr/sbin/nologin familydb"
        fi
        if id familydb >/dev/null 2>&1 && ! service_can_reach_checkout; then
          warn "The familydb user cannot get into ${REPO_ROOT}, which is usually because it is"
          warn "inside somebody's home directory. A service running as its own user could not"
          warn "start there, so the unit has not been installed. Move the checkout and run again:"
          warn "  sudo mkdir -p /opt/familydb && sudo chown \"\$USER\" /opt/familydb"
          warn "  cp -a ${REPO_ROOT}/. /opt/familydb/ && cd /opt/familydb && scripts/install.sh"
          note "Everything else is installed. You can run it yourself with .venv/bin/familydb run."
          SKIP_UNIT=1
        fi
        tmp_unit="$(mktemp)"
        sed -e "s#/opt/familydb#${REPO_ROOT}#g" "$unit" > "$tmp_unit"
        # ProtectHome=true hides /home from the service, so a checkout there would start into an
        # empty directory and stop. Read-only keeps the hardening; ReadWritePaths still lets the
        # data folder through.
        case "$REPO_ROOT" in
          /home/*|/root/*)
            sed -i -e 's#^ProtectHome=true#ProtectHome=read-only#' "$tmp_unit"
            note "A checkout under /home or /root needs ProtectHome=read-only; the unit says so."
            ;;
        esac
        if [ "$SKIP_UNIT" = 1 ]; then
          :
        # install, not cp: mktemp made this file 0600, and a unit nobody but root can read is
        # one `systemctl cat` nobody but root can run.
        elif noting_new /etc/systemd/system/familydb.service \
          && noting_new /etc/systemd/system/multi-user.target.wants/familydb.service link \
          && $SUDO install -m 644 "$tmp_unit" /etc/systemd/system/familydb.service \
          && $SUDO systemctl daemon-reload \
          && { $SUDO systemctl enable familydb >/dev/null 2>&1 || true; }; then
          ok "Unit installed. Start it with: sudo systemctl start familydb"
          HAND_OVER_TO_SERVICE=1
        else
          warn "Could not install the systemd unit. Everything else is set up; see RUNBOOK section 2b."
        fi
        rm -f "$tmp_unit"
      fi
    fi
  else
    note "No root and no sudo, so the systemd unit was skipped. See RUNBOOK section 2b."
  fi
fi

# ------------------------------------------------------------- verifying ----
head2 "Checking it over"
if [ "$DRY_RUN" = 1 ]; then
  note "skipped in a dry run"
else
  runfamilydb config >/dev/null && ok "Settings load."
  runfamilydb db status >/dev/null && ok "Database reachable."
  if runfamilydb tool --list >/tmp/familydb-tools.$$ 2>/dev/null; then
    ready="$(grep -c ' available ' /tmp/familydb-tools.$$ || true)"
    waiting="$(grep -c ' unavailable ' /tmp/familydb-tools.$$ || true)"
    rm -f /tmp/familydb-tools.$$
    ok "${ready} tools ready${waiting:+, ${waiting} waiting on a service you have not set up yet}."
  fi
fi

# --------------------------------------------------- handing it to the service ----
# Last, because everything above runs as whoever started this script and needs to be able to
# read .env and write data/. After this, those belong to the service.
if [ "$HAND_OVER_TO_SERVICE" = 1 ] && [ "$DRY_RUN" = 0 ] && id familydb >/dev/null 2>&1; then
  if $SUDO chown -R familydb:familydb "${REPO_ROOT}/data" 2>/dev/null \
     && { [ ! -f "$ENV_FILE" ] || $SUDO chown familydb:familydb "$ENV_FILE"; }; then
    ok "data/ and .env now belong to the familydb user."
  else
    warn "Could not hand data/ and .env to the familydb user. Do it before starting:"
    warn "  sudo chown -R familydb:familydb ${REPO_ROOT}/data ${REPO_ROOT}/.env"
    HAND_OVER_TO_SERVICE=0
  fi
fi

# -------------------------------------------------------------- backups ----
# The database is one file and everything the family has said is in it, so a nightly copy is
# part of installing, not a chore for later. BACKUPS=no skips it for a scripted build.
BACKUPS_SCHEDULED=0
if [ "${BACKUPS:-yes}" != no ] && [ "$DRY_RUN" = 0 ]; then
  head2 "Backups"
  if [ "${FROM_BOOTSTRAP:-0}" = 1 ] || confirm "Back the database up every night at 03:15, keeping two weeks?" yes; then
    # A minimal Debian has no cron; without it the schedule has nowhere to live.
    if ! have crontab && have apt-get; then
      apt_install_noted cron >/dev/null 2>&1 || warn "Could not install cron with apt."
    fi
    if bash "${REPO_ROOT}/scripts/maintain.sh" schedule-backups --target "$REPO_ROOT" --yes; then
      BACKUPS_SCHEDULED=1
    else
      warn "Could not schedule them. Later: sudo ${REPO_ROOT}/scripts/maintain.sh schedule-backups"
    fi
  fi
fi

# ---------------------------------------------------------------- HTTPS ----
# Something has to hold the certificate. In Docker that is the Caddy container
# (COMPOSE_PROFILES=tls above); here it is Caddy on the machine, set up by lib/https.sh.
env_value() { grep -E "^${1}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "'\"" || true; }
DOMAIN="$(env_value WEB_DOMAIN)"
PORT="$(env_value WEB_PORT)"; PORT="${PORT:-8080}"
PUBLIC_PORT="$(env_value WEB_PUBLIC_PORT)"; PUBLIC_PORT="${PUBLIC_PORT:-443}"
HTTPS_READY=0
if [ -n "$DOMAIN" ] && [ "$MODE" = docker ]; then
  HTTPS_READY=1
elif [ -n "$DOMAIN" ] && [ "$MODE" = venv ] && [ "$DRY_RUN" = 0 ]; then
  head2 "HTTPS"
  if setup_https "$DOMAIN" "$PORT"; then
    HTTPS_READY=1
  fi
fi

# ----------------------------------------------------------- what is next ----
# Run by bootstrap.sh, which starts the service and has the last word, with the link in it.
if [ "${FROM_BOOTSTRAP:-0}" = 1 ]; then
  [ -n "$LOG_FILE" ] && note "A transcript of the configuration is at ${LOG_FILE}"
  exit 0
fi

head2 "Done"

if [ "$MODE" = docker ]; then
  START="docker compose up -d"
  LOGS="docker compose logs -f bot"
  CLI="docker compose exec bot familydb"
else
  START="sudo systemctl start familydb   # or, from ${REPO_ROOT}: .venv/bin/familydb run"
  LOGS="journalctl -u familydb -f"
  CLI="cd ${REPO_ROOT} && .venv/bin/familydb"
  # data/ and .env belong to the service now, so a command that reads them has to be that user.
  [ "$HAND_OVER_TO_SERVICE" = 1 ] && CLI="cd ${REPO_ROOT} && sudo -u familydb .venv/bin/familydb"
fi

say "Start it:   ${B}${START}${OFF}"
say "Watch it:   ${LOGS}"
say ""
if [ "$HTTPS_READY" = 1 ]; then
  say "Then open ${B}$(public_url "$DOMAIN")${OFF} and sign in with the password above."
  say_how_to_open
else
  say "Then open the page and sign in with the password above. Run this on your own computer,"
  say "not on this server; it works from anywhere you can reach the server over SSH:"
  say "  ssh -L ${PORT}:127.0.0.1:${PORT} ${SUDO_USER:-$(id -un)}@$(hostname -I 2>/dev/null | awk '{print $1}')"
  say "  and, while it is connected, open ${B}http://127.0.0.1:${PORT}/${OFF} on that computer."
fi
say ""
say "The page walks you through the rest, one step at a time: yourself, your own password, an AI"
say "key, where home is, then Telegram and Google Calendar if you want them."
if [ "$BACKUPS_SCHEDULED" = 1 ]; then
  say "Copy ${REPO_ROOT}/backups off this server now and then: a backup on the same disk is not"
  say "a backup."
else
  say "Schedule nightly backups: sudo ${REPO_ROOT}/scripts/maintain.sh schedule-backups"
fi
say ""
say "What it costs to run: ${CLI} debug cost"
say "Check it over:        ${CLI} doctor"
say "Look after it:        ${REPO_ROOT}/scripts/maintain.sh --help"
say "Everything else:      RUNBOOK.md, and docs/INSTALL.md"
[ -n "$LOG_FILE" ] && note "A transcript of this run is at ${LOG_FILE}"
