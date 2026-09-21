#!/usr/bin/env bash
# FamilyDB installer. Works on a home server or a VPS, with Docker or a virtualenv.
# Safe to run again: it never overwrites a .env without asking, and never touches your database.
set -euo pipefail

VERSION="1.0"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV_FILE="${REPO_ROOT}/.env"
EXAMPLE_FILE="${REPO_ROOT}/.env.example"

MODE=""              # docker | venv
ASSUME_YES=0         # --yes: take every default, ask nothing
NON_INTERACTIVE=0    # --non-interactive: never prompt; fail if something required is missing
DRY_RUN=0
SKIP_INSTALL=0       # --config-only: write .env and stop

# ---------------------------------------------------------------- output ----
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  B=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; OFF=$'\033[0m'
else
  B=""; DIM=""; RED=""; YEL=""; GRN=""; OFF=""
fi

say()  { printf '%s\n' "$*"; }
head2() { printf '\n%s%s%s\n' "$B" "$*" "$OFF"; }
note() { printf '%s%s%s\n' "$DIM" "$*" "$OFF"; }
ok()   { [ "$DRY_RUN" = 1 ] && return 0; printf '%s✓%s %s\n' "$GRN" "$OFF" "$*"; }
warn() { printf '%s!%s %s\n' "$YEL" "$OFF" "$*" >&2; }
die()  { EXPLAINED=1; printf '%s✗%s %s\n' "$RED" "$OFF" "$*" >&2; exit 1; }
run()  { if [ "$DRY_RUN" = 1 ]; then note "would run: $*"; else "$@"; fi; }

FAILED_AT=""
EXPLAINED=0   # die() has already said why, so the trap stays quiet
trap 'FAILED_AT="$BASH_COMMAND"' ERR
# shellcheck disable=SC2154  # `status` is assigned at the start of this same trap.
trap 'status=$?; if [ $status -ne 0 ] && [ "$EXPLAINED" = 0 ]; then printf "\n%s✗%s stopped at: %s\n   Nothing further was changed. Fix that and run this again.\n" "$RED" "$OFF" "${FAILED_AT:-the step above}" >&2; fi' EXIT

usage() {
  cat <<'USAGE'
FamilyDB installer

  scripts/install.sh [options]

Options
  --mode docker|venv   How to run it. Default: docker when available, else a virtualenv.
  --yes                Accept every default. Still asks for the secrets it cannot guess: the
                       API keys and the Telegram token, unless they are in the environment.
  --non-interactive    Never prompt. Every answer must come from the environment (below).
  --config-only        Write .env and stop, installing nothing.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Answers can be supplied as environment variables, which is what --non-interactive reads:
  PROVIDER  ANTHROPIC_API_KEY  OPENAI_API_KEY  GEMINI_API_KEY
  FAMILYDB_TZ  HOME_AREA  HOME_LAT  HOME_LON  WEATHER_UNITS
  TELEGRAM_BOT_TOKEN  WEB_ENABLED  WEB_HOST  WEB_PORT  WEB_PASSWORD  WEB_TOOLS_ENABLED
  ADMIN_NAME

Examples
  scripts/install.sh                          # ask a handful of questions, then install
  scripts/install.sh --yes                    # defaults for everything answerable
  ANTHROPIC_API_KEY=sk-ant-... FAMILYDB_TZ=America/Vancouver ADMIN_NAME=Sam \
    scripts/install.sh --non-interactive --mode venv
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --mode=*) MODE="${1#*=}"; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --non-interactive) NON_INTERACTIVE=1; ASSUME_YES=1; shift ;;
    --config-only) SKIP_INSTALL=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; trap - EXIT; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done
case "$MODE" in ""|docker|venv) ;; *) die "--mode must be docker or venv, not '$MODE'" ;; esac

# ----------------------------------------------------------------- input ----
have() { command -v "$1" >/dev/null 2>&1; }

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

ask_secret() { # ask_secret VAR "question"
  local var="$1" question="$2" reply
  if [ -n "${!var:-}" ]; then return 0; fi
  if [ "$NON_INTERACTIVE" = 1 ] || [ ! -t 0 ]; then printf -v "$var" '%s' ""; return 0; fi
  read -r -s -p "$question: " reply || reply=""
  printf '\n'
  printf -v "$var" '%s' "$reply"
}

confirm() { # confirm "question" yes|no
  local question="$1" default="${2:-yes}" reply
  if [ "$ASSUME_YES" = 1 ] || [ ! -t 0 ]; then [ "$default" = yes ]; return; fi
  read -r -p "$question [$([ "$default" = yes ] && echo 'Y/n' || echo 'y/N')]: " reply || reply=""
  reply="${reply:-$default}"
  case "$reply" in [Yy]*|yes) return 0 ;; *) return 1 ;; esac
}

# --------------------------------------------------------------- helpers ----
ask_key() { # ask_key VAR provider "Label" "where to get one" "what it starts with"
  local var="$1" owner="$2" label="$3" where="$4" prefix="$5"
  if [ -z "${!var:-}" ]; then
    # Explaining where to get a key is only worth doing to somebody who is about to be asked.
    if [ "$NON_INTERACTIVE" = 0 ] && [ -t 0 ]; then
      say ""
      say "A key for ${label}. Create one at ${where}"
      if [ "$PROVIDER" = "$owner" ]; then
        note "This is the one you chose, so this is the key it will answer with."
      else
        note "Optional. With a key here, ${label} answers when the one you chose cannot."
      fi
      note "Leave it blank to fill in later; everything else will still be set up."
    fi
    ask_secret "$var" "${label} key"
  fi
  case "${!var:-}" in
    "") ;;
    ${prefix}*) ok "${label} key stored." ;;
    *) warn "that does not look like a ${label} key (they start ${prefix}). Storing it anyway." ;;
  esac
  set_env "$var" "${!var:-}"
}

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
  written="$(quote_env "$value")"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Read and write by hand: awk -v would read a backslash in the value as an escape.
    while IFS= read -r line || [ -n "$line" ]; do
      if [ "$replaced" = 0 ] && [ "${line%%=*}" = "$key" ] && [ "$line" != "${line#*=}" ]; then
        printf '%s=%s\n' "$key" "$written"
        replaced=1
      else
        printf '%s\n' "$line"
      fi
    done < "$ENV_FILE" > "${ENV_FILE}.tmp"
    mv "${ENV_FILE}.tmp" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$written" >> "$ENV_FILE"
  fi
}

random_password() {
  if have openssl; then openssl rand -base64 18 | tr -d '/+=' | cut -c1-20
  elif [ -r /dev/urandom ]; then LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20
  else date +%s | sha256sum | cut -c1-20
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
  note "Writing configuration only, so the ${MODE} tooling is not checked."
elif [ "$MODE" = docker ]; then
  have docker || die "docker not found. Install Docker, or re-run with --mode venv."
  docker compose version >/dev/null 2>&1 || die "the docker compose plugin is missing. Install it, or use --mode venv."
  if ! docker info >/dev/null 2>&1; then
    die "the Docker daemon is not reachable. Start it (systemctl start docker), or add yourself to the docker group, or use --mode venv."
  fi
else
  if ! have uv; then
    if [ "$NON_INTERACTIVE" = 1 ]; then
      die "uv is not installed. Install it from https://docs.astral.sh/uv/ and run again."
    fi
    say "This path needs uv, which manages the Python version and the virtualenv."
    if confirm "Install uv now (downloads and runs the official installer)?" yes; then
      have curl || die "curl is needed to install uv. Install curl, or install uv yourself."
      run sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
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
  if [ "$NON_INTERACTIVE" = 1 ]; then
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

  # --- who answers ---
  say ""
  say "Which model answers: Claude, OpenAI or Gemini. Give more than one key and it will ask"
  say "another when the first is rate limited or down. All three can be changed later from the"
  say "settings page, so this is not a decision you are stuck with."
  ask PROVIDER "claude, openai or gemini" "${PROVIDER:-claude}"
  case "$PROVIDER" in
    openai|OpenAI|OPENAI|gpt|GPT) PROVIDER=openai ;;
    gemini|Gemini|GEMINI|google|Google|GOOGLE) PROVIDER=gemini ;;
    *) PROVIDER=anthropic ;;
  esac
  set_env PROVIDER "$PROVIDER"

  ask_key ANTHROPIC_API_KEY anthropic "Claude" \
    "https://console.anthropic.com/settings/keys" "sk-ant-"
  ask_key OPENAI_API_KEY openai "OpenAI" "https://platform.openai.com/api-keys" "sk-"
  ask_key GEMINI_API_KEY gemini "Gemini" "https://aistudio.google.com/apikey" "AIza"

  case "$PROVIDER" in
    anthropic) CHOSEN_KEY="${ANTHROPIC_API_KEY:-}" ;;
    openai) CHOSEN_KEY="${OPENAI_API_KEY:-}" ;;
    gemini) CHOSEN_KEY="${GEMINI_API_KEY:-}" ;;
  esac
  if [ -z "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GEMINI_API_KEY:-}" ]; then
    warn "No key at all. The bot will save messages but cannot reply until you add one to .env."
  elif [ -z "$CHOSEN_KEY" ]; then
    warn "You chose ${PROVIDER} but gave no key for it; it will ask one of the others instead."
  fi

  # --- where the family is ---
  detected_tz="$(detect_timezone)"
  ask FAMILYDB_TZ "Timezone" "$detected_tz"
  if ! valid_timezone "$FAMILYDB_TZ"; then
    warn "'${FAMILYDB_TZ}' is not an IANA zone name. Using ${detected_tz}."
    FAMILYDB_TZ="$detected_tz"
  fi
  set_env FAMILYDB_TZ "$FAMILYDB_TZ"

  say ""
  say "Your town or area. It is used for the weather and for searching what is on nearby."
  ask HOME_AREA "Town, region" "${HOME_AREA:-}"
  set_env HOME_AREA "$HOME_AREA"
  if [ -n "$HOME_AREA" ] && [ -z "${HOME_LAT:-}" ]; then
    if place="$(look_up_place "$HOME_AREA")"; then
      HOME_LAT="$(printf '%s' "$place" | cut -d' ' -f1)"
      HOME_LON="$(printf '%s' "$place" | cut -d' ' -f2)"
      ok "Found $(printf '%s' "$place" | cut -d' ' -f3-) at ${HOME_LAT}, ${HOME_LON}"
    else
      note "Could not look that up. The forecast needs coordinates; add HOME_LAT and HOME_LON to .env later."
    fi
  fi
  set_env HOME_LAT "${HOME_LAT:-}"
  set_env HOME_LON "${HOME_LON:-}"
  ask WEATHER_UNITS "Temperatures in metric or imperial" "${WEATHER_UNITS:-metric}"
  case "$WEATHER_UNITS" in metric|imperial) ;; *) WEATHER_UNITS=metric ;; esac
  set_env WEATHER_UNITS "$WEATHER_UNITS"

  # --- Telegram ---
  say ""
  say "Telegram is how the family talks to it. Create a bot with @BotFather and paste the token."
  note "Skip this to use the console for now (familydb repl); you can add it later."
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    ask_secret TELEGRAM_BOT_TOKEN "Bot token"
  fi
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && ! printf '%s' "$TELEGRAM_BOT_TOKEN" | grep -Eq '^[0-9]+:[A-Za-z0-9_-]+$'; then
    warn "that does not look like a BotFather token (digits, a colon, then letters). Storing it anyway."
  fi
  set_env TELEGRAM_BOT_TOKEN "${TELEGRAM_BOT_TOKEN:-}"
  [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && ok "Telegram configured." || note "No Telegram token: console only for now."

  # --- what it is allowed to spend ---
  say ""
  say "Looking ideas up on the web fills in addresses, opening hours and booking links,"
  say "and finds events on nearby. It costs a few searches per new idea."
  if [ -z "${WEB_TOOLS_ENABLED:-}" ]; then
    if confirm "Turn web lookups on?" yes; then WEB_TOOLS_ENABLED=true; else WEB_TOOLS_ENABLED=false; fi
  fi
  set_env WEB_TOOLS_ENABLED "$WEB_TOOLS_ENABLED"

  # --- the web page ---
  say ""
  say "A web page lets you browse the ideas, the restaurants and the plans in a browser, see"
  say "what the models have cost, and change the settings and the keys without editing a file."
  if [ -z "${WEB_ENABLED:-}" ]; then
    if confirm "Turn the web page on?" no; then WEB_ENABLED=true; else WEB_ENABLED=false; fi
  fi
  set_env WEB_ENABLED "$WEB_ENABLED"
  if [ "$WEB_ENABLED" = true ]; then
    if [ "$MODE" = docker ]; then
      WEB_HOST="${WEB_HOST:-0.0.0.0}"
      note "In Docker the page binds every interface inside the container; docker-compose.yml decides who reaches it."
    else
      say "127.0.0.1 keeps the page on this machine. 0.0.0.0 serves the network."
      ask WEB_HOST "Bind address" "${WEB_HOST:-127.0.0.1}"
      if ! valid_host "$WEB_HOST"; then
        warn "'${WEB_HOST}' is not an address to bind. Using 127.0.0.1; change WEB_HOST in .env later."
        WEB_HOST=127.0.0.1
      fi
    fi
    ask WEB_PORT "Port" "${WEB_PORT:-8080}"
    if ! printf '%s' "$WEB_PORT" | grep -Eq '^[0-9]+$' || [ "$WEB_PORT" -lt 1025 ] || [ "$WEB_PORT" -gt 65535 ]; then
      warn "port must be a number between 1025 and 65535; using 8080."
      WEB_PORT=8080
    fi
    set_env WEB_HOST "$WEB_HOST"
    set_env WEB_PORT "$WEB_PORT"

    needs_password=1
    case "$WEB_HOST" in 127.0.0.1|localhost|::1|"") needs_password=0 ;; esac
    if [ -z "${WEB_PASSWORD:-}" ] && [ "$needs_password" = 1 ]; then
      if confirm "Generate a password for the page?" yes; then
        WEB_PASSWORD="$(random_password)"
        say "  Password: ${B}${WEB_PASSWORD}${OFF}"
        say "  Write it down now. It is in .env too, but nowhere else."
      else
        ask_secret WEB_PASSWORD "Password for the page (12 characters or more)"
      fi
    fi
    if [ "$needs_password" = 1 ] && [ "${#WEB_PASSWORD}" -lt 12 ]; then
      if [ "$NON_INTERACTIVE" = 1 ] && [ -n "${WEB_PASSWORD:-}" ]; then
        # A build script gave a password on purpose. Replacing it with one printed to a log
        # nobody reads would leave the family locked out of their own page.
        die "WEB_PASSWORD is ${#WEB_PASSWORD} characters; a page on the network needs 12 or more."
      fi
      warn "a page reachable from other machines needs 12 characters or more; generating one."
      WEB_PASSWORD="$(random_password)"
      say "  Password: ${B}${WEB_PASSWORD}${OFF}"
      say "  Write it down now. It is in .env too, but nowhere else."
    fi
    set_env WEB_PASSWORD "${WEB_PASSWORD:-}"
    if [ "$MODE" = docker ]; then
      note "The page is published to this machine only. To reach it from elsewhere, edit the"
      note "ports line in docker-compose.yml, or put Caddy in front (RUNBOOK section 10)."
    fi
  fi

  # --- things nobody can know yet ---
  note ""
  note "Left empty on purpose, because they cannot be known until the bot is running:"
  note "  DIGEST_CHAT_ID   the family group's chat id, for the weekly digest (RUNBOOK section 9)"
  note "  GOOGLE_CALENDAR_ID and the Google token, which need a browser (RUNBOOK section 5)"

  [ "$DRY_RUN" = 1 ] || chmod 600 "$ENV_FILE"
  ok "Wrote $(basename "$ENV_FILE") (readable only by you)."
fi

if [ "$SKIP_INSTALL" = 1 ]; then
  head2 "Done"
  say "Configuration written. Nothing installed, as asked."
  trap - EXIT
  exit 0
fi

# --------------------------------------------------------------- install ----
head2 "Installing"

run mkdir -p "${REPO_ROOT}/data"

if [ "$MODE" = docker ]; then
  run docker compose --project-directory "$REPO_ROOT" build
  ok "Image built."
  FAMILYDB=(docker compose --project-directory "$REPO_ROOT" run --rm -T bot familydb)
  # The container runs as uid 1000 and needs to write the database into data/.
  if [ "$DRY_RUN" = 0 ] && ! chown -R 1000:1000 "${REPO_ROOT}/data" 2>/dev/null; then
    note "Could not give data/ to uid 1000. If the container cannot write, run:"
    note "  sudo chown -R 1000:1000 ${REPO_ROOT}/data"
  fi
else
  run uv sync --frozen --no-dev --project "$REPO_ROOT"
  ok "Dependencies installed."
  FAMILYDB=("${REPO_ROOT}/.venv/bin/familydb")
fi

runfamilydb() { if [ "$DRY_RUN" = 1 ]; then note "would run: familydb $*"; else "${FAMILYDB[@]}" "$@"; fi; }

head2 "Setting up the database"
runfamilydb db migrate
ok "Schema created."

# --- the first family member ---
have_members=0
if [ "$DRY_RUN" = 0 ] && runfamilydb members list 2>/dev/null | grep -qv 'no members yet'; then
  have_members=1
fi
if [ "$have_members" = 0 ]; then
  ask ADMIN_NAME "Your name, as the family says it" "${ADMIN_NAME:-${SUDO_USER:-${USER:-Admin}}}"
  if [ -n "$ADMIN_NAME" ]; then
    runfamilydb members add "$ADMIN_NAME" --role admin >/dev/null && ok "Added ${ADMIN_NAME} as an admin."
  fi
  note "Add the rest with: familydb members add NAME --role member|kid"
  note "Anyone messaging on Telegram also needs --channel telegram --channel-user-id THEIR_ID,"
  note "which the bot tells them the first time they write (RUNBOOK section 4)."
else
  ok "Family members already set up."
fi

# --- the service ---
if [ "$MODE" = venv ] && have systemctl && [ -d /run/systemd/system ]; then
  head2 "Running it as a service"
  if [ "$(id -u)" = 0 ] || have sudo; then
    if confirm "Install the systemd unit so it starts on boot?" yes; then
      SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
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
          ok "Created the familydb system user."
        else
          warn "Could not create the familydb user. Create it, or edit User= in the unit:"
          warn "  sudo useradd --system --home-dir ${REPO_ROOT} --shell /usr/sbin/nologin familydb"
        fi
        tmp_unit="$(mktemp)"
        sed -e "s#/opt/familydb#${REPO_ROOT}#g" "$unit" > "$tmp_unit"
        # ProtectHome=true hides /home from the service, so a checkout there would start into an
        # empty directory and stop. Read-only keeps the hardening; ReadWritePaths still lets the
        # data folder through.
        case "$REPO_ROOT" in
          /home/*|/root/*)
            sed -i -e 's#^ProtectHome=true#ProtectHome=read-only#' "$tmp_unit"
            note "Checkout is under ${REPO_ROOT%%/*}/, so the unit uses ProtectHome=read-only."
            ;;
        esac
        if $SUDO cp "$tmp_unit" /etc/systemd/system/familydb.service \
          && $SUDO systemctl daemon-reload \
          && { $SUDO systemctl enable familydb >/dev/null 2>&1 || true; }; then
          ok "Unit installed. Start it with: sudo systemctl start familydb"
        else
          warn "Could not install the systemd unit. Everything else is set up; see RUNBOOK section 2b."
        fi
        rm -f "$tmp_unit"
        # The service has to read the secrets and write the database; nobody else should.
        if id familydb >/dev/null 2>&1; then
          if $SUDO chown -R familydb:familydb "${REPO_ROOT}/data" 2>/dev/null \
             && { [ ! -f "$ENV_FILE" ] || $SUDO chown familydb:familydb "$ENV_FILE"; }; then
            ok "data/ and .env now belong to the familydb user."
            note "Run the CLI as that user: sudo -u familydb ${REPO_ROOT}/.venv/bin/familydb repl"
          else
            warn "Could not hand data/ and .env to the familydb user. Do it before starting:"
            warn "  sudo chown -R familydb:familydb ${REPO_ROOT}/data ${REPO_ROOT}/.env"
          fi
        fi
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
  # Only where counting tokens is free: OpenAI has no such endpoint, so there is nothing to ask.
  if [ -n "${CHOSEN_KEY:-}" ] && [ "${PROVIDER:-anthropic}" != openai ]; then
    if runfamilydb debug validate-tools >/dev/null 2>&1; then
      ok "The API accepted the key and every tool definition."
    else
      warn "Could not reach the API. Check the key with: familydb debug validate-tools"
    fi
  fi
fi

# ----------------------------------------------------------- what is next ----
head2 "Done"

if [ "$MODE" = docker ]; then
  START="docker compose up -d"
  LOGS="docker compose logs -f bot"
  CLI="docker compose exec bot familydb"
else
  START="sudo systemctl start familydb   # or: .venv/bin/familydb run"
  LOGS="journalctl -u familydb -f"
  CLI="${REPO_ROOT}/.venv/bin/familydb"
fi

say "Start it:   ${B}${START}${OFF}"
say "Watch it:   ${LOGS}"
say "Talk to it: ${CLI} repl"
say ""
say "Still to do, when you are ready:"
if [ -z "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GEMINI_API_KEY:-}" ]; then
  say "  · add a key in .env or on the settings page, or it cannot reply"
fi
[ -z "${TELEGRAM_BOT_TOKEN:-}" ] && say "  · add a Telegram bot token to chat from your phones (RUNBOOK section 4)"
[ -z "${HOME_LAT:-}" ] && say "  · add HOME_LAT and HOME_LON for the weather (RUNBOOK section 6)"
say "  · connect Google Calendar from a machine with a browser (RUNBOOK section 5)"
say "  · set DIGEST_CHAT_ID once the family group exists (RUNBOOK section 9)"
say ""
say "What it costs to run: ${CLI} debug cost"
say "Everything else:      RUNBOOK.md"

trap - EXIT
