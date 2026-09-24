#!/usr/bin/env bash
# FamilyDB bootstrap: a bare server to a running bot.
#
# This is the only script that assumes nothing is installed. It installs the system packages,
# puts the code in /opt/familydb, hands over to scripts/install.sh for the configuration, starts
# the service and checks the result. Running it again installs what is missing and leaves the
# rest alone.
#
#   scp -r scripts you@server:~/          # or clone the repository on the server
#   less scripts/bootstrap.sh             # read it: it is about to run as root
#   sudo bash scripts/bootstrap.sh --help
#
# Before it changes anything it prints exactly what it will change on this machine and why, and
# asks. When a step fails it says which step, what the command was, what the command printed,
# what that usually means and what to try.
#
# FamilyDB lives in a private repository, so the code has to be let onto the machine somehow: a
# deploy key (--deploy-key), a token (GITHUB_TOKEN), or a copy you put there yourself (--from).
# docs/INSTALL.md walks through each one.
set -euo pipefail

# shellcheck disable=SC2034  # read by lib/common.sh when it opens the transcript.
SCRIPT_ARGS="$*"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -r "${HERE}/lib/common.sh" ]; then
  # shellcheck source=lib/common.sh
  . "${HERE}/lib/common.sh"
else
  printf 'This script needs scripts/lib/common.sh beside it.\n' >&2
  printf 'Copy the whole scripts/ folder across, or run it from a clone of the repository.\n' >&2
  exit 1
fi

VERSION="1.1"
TARGET="/opt/familydb"
REPO="https://github.com/atate911/FamilyDB.git"
REF=""
SOURCE_DIR=""
MODE=""
SERVICE_USER="familydb"
DEPLOY_KEY=""
START=1
RUN_INSTALL=1
PACKAGES=1
ASSUME_YES=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
FamilyDB bootstrap: a bare server to a running bot.

  sudo bash bootstrap.sh [options]

It prints what it will change on this machine, and why, before it changes anything.

Where the code comes from (a private repository needs one of these)
  --deploy-key FILE    An SSH private key with read access to the repository.
  GITHUB_TOKEN=...     A token in the environment. Used for the clone only, never written down.
  --from PATH          A copy already on this machine: a directory, or a .tar.gz.
                       With nothing else given, and this script inside a checkout, that
                       checkout is what gets installed.
  --repo URL           Clone from somewhere other than the default GitHub URL.
  --ref NAME           Tag, branch or commit. Default: the newest release, or the default
                       branch while CHANGELOG.md says the next version is in progress.

Where it goes
  --target DIR         Default: /opt/familydb. Keep it out of a home directory: the service
                       runs as its own user, which cannot enter one.
  --user NAME          The system user that runs the bot. Default: familydb.

How it runs
  --mode docker|venv   Default: venv, the smaller install. Docker is installed for you if you
                       ask for it and it is missing.
  --no-packages        Install nothing with apt; stop instead if something is missing.
  --no-start           Install and configure, but leave it stopped.
  --no-install         Prepare the machine and fetch the code, then stop before configuring.
  --yes                Take every default and do not ask before changing the machine.
  --dry-run            Say what would happen; change nothing at all.
  -h, --help           This text.

Anything else is passed to scripts/install.sh, which asks one question. Its answers can
come from the environment instead (WEB_DOMAIN, WEB_PASSWORD, ADMIN_NAME, BACKUPS and more).
Everything else is set on the web page. See scripts/install.sh --help.

Afterwards
  scripts/maintain.sh   backups, restores, upgrades, logs, status
  scripts/uninstall.sh  remove it, keeping the data or not
  familydb doctor       check the install and say what is wrong

Examples
  sudo bash bootstrap.sh                          # ask, install, start
  sudo bash bootstrap.sh --from ~/familydb.tar.gz # code already copied onto this box
  sudo --preserve-env=GITHUB_TOKEN bash bootstrap.sh --ref NAME   # token exported first
  sudo bash bootstrap.sh --deploy-key /root/familydb_deploy --mode docker
USAGE
}

PASS_THROUGH=()
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --repo=*) REPO="${1#*=}"; shift ;;
    --ref) REF="${2:-}"; shift 2 ;;
    --ref=*) REF="${1#*=}"; shift ;;
    --deploy-key) DEPLOY_KEY="${2:-}"; shift 2 ;;
    --deploy-key=*) DEPLOY_KEY="${1#*=}"; shift ;;
    --from) SOURCE_DIR="${2:-}"; shift 2 ;;
    --from=*) SOURCE_DIR="${1#*=}"; shift ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --user) SERVICE_USER="${2:-}"; shift 2 ;;
    --user=*) SERVICE_USER="${1#*=}"; shift ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --mode=*) MODE="${1#*=}"; shift ;;
    --no-packages) PACKAGES=0; shift ;;
    --no-start) START=0; shift ;;
    --no-install) RUN_INSTALL=0; shift ;;
    --yes|-y) ASSUME_YES=1; PASS_THROUGH+=("--yes"); shift ;;
    --dry-run) DRY_RUN=1; PASS_THROUGH+=("--dry-run"); shift ;;
    --non-interactive) ASSUME_YES=1; PASS_THROUGH+=("--non-interactive"); shift ;;
    -h|--help) usage; exit 0 ;;
    *) PASS_THROUGH+=("$1"); shift ;;
  esac
done
case "$MODE" in ""|docker|venv) ;; *) die "--mode must be docker or venv, not '${MODE}'" ;; esac
[ -n "$MODE" ] || MODE=venv
export ASSUME_YES DRY_RUN

log_to "/var/log/familydb-bootstrap.log"
checkpoint_to "/var/log/familydb-bootstrap.progress"
enable_failure_reporting
on_failure_hint "Everything that already worked is still in place; fix what is above and run this again. docs/INSTALL.md has a section on each failure."

as_service_user() {
  if have sudo; then
    as_root sudo -u "$SERVICE_USER" "$@"
  elif [ "$(id -u)" = 0 ]; then
    su -s /bin/sh "$SERVICE_USER" -c "$(printf '%q ' "$@")"
  else
    die "cannot run anything as ${SERVICE_USER} from here"
  fi
}

# ------------------------------------------------------------- preflight ----
head2 "FamilyDB bootstrap ${VERSION}"

[ "$(uname -s)" = Linux ] \
  || die "this installs a Linux service, and this is $(uname -s)" \
         "On macOS, follow docs/INSTALL.md by hand instead."
if [ "$(id -u)" != 0 ]; then
  have sudo || die "this changes system files, so it needs root, and sudo is not installed" \
    "Run it as root instead: su - , then bash ${BASH_SOURCE[0]}"
  sudo -n true 2>/dev/null || note "sudo will ask for your password."
fi

OS_FAMILY=""
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${ID:-} ${ID_LIKE:-}" in
    *debian*|*ubuntu*) OS_FAMILY=debian ;;
  esac
  say "Machine: ${PRETTY_NAME:-unknown} on $(uname -m), $(nproc 2>/dev/null || echo '?') CPU(s)"
fi
if [ "$OS_FAMILY" != debian ]; then
  warn "only Debian and Ubuntu are tested, so nothing will be installed with apt here."
  note "Install git, curl, and either Docker or Python 3.11+ yourself, then run this again."
  PACKAGES=0
fi
case "$(uname -m)" in
  x86_64|aarch64|arm64) ;;
  *) warn "$(uname -m) is untested. The virtualenv path is the more likely to work." ;;
esac

MEM_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo "")"
if [ -n "$MEM_MB" ] && [ "$MEM_MB" -lt 900 ]; then
  warn "${MEM_MB} MB of memory. The bot needs about 200 MB, but building the install wants more."
  note "If a step is killed for no reason, that is why. Add swap and run this again:"
  note "  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile"
  note "  sudo mkswap /swapfile && sudo swapon /swapfile"
fi
require_free_mb "$(dirname -- "$TARGET")" 900 "the install and its virtualenv"

if previous="$(last_checkpoint 2>/dev/null)" && [ -n "$previous" ] && [ "$previous" != "checked" ]; then
  note "A previous run of this script got as far as '${previous}'. This one will pick up from there."
fi

# ------------------------------------------------- what this will change ----
PACKAGE_LIST="ca-certificates curl git tzdata"
if [ "$PACKAGES" = 1 ]; then
  plan_item "Install these system packages, if missing: ${PACKAGE_LIST}" \
    "git and curl fetch the code, ca-certificates is what lets HTTPS be verified, and tzdata is how it knows what 'this weekend' means where you live"
fi
if [ "$MODE" = docker ]; then
  on_system_path docker || plan_item "Install Docker Engine and the compose plugin, from Docker's own apt repository" \
    "the distribution's docker.io package does not include compose, and the bot is started with compose"
else
  on_system_path uv || plan_item "Install uv into /usr/local/bin" \
    "uv fetches the right Python version and builds a virtualenv for this one program; the system Python is not changed, replaced or upgraded"
fi
plan_item "Create a system user called '${SERVICE_USER}', with no password and no login shell" \
  "the bot runs as its own account rather than as root or as you, so a mistake in it cannot reach the rest of the machine"
plan_item "Create ${TARGET} and put the code in it" \
  "one directory holds the program, the configuration and the database, which is what makes backing it up and removing it simple"
if [ "$RUN_INSTALL" = 1 ]; then
  plan_item "Write ${TARGET}/.env, readable only by ${SERVICE_USER}" \
    "your API keys and the web page password are kept there"
  plan_item "Create a SQLite database at ${TARGET}/data/familydb.sqlite3" \
    "everything the family tells it lives in that one file, which is also the thing to back up"
  if [ "$MODE" = venv ]; then
    plan_item "Write /etc/systemd/system/familydb.service and enable it" \
      "so the bot starts when the machine boots, and is restarted if it ever stops"
  fi
fi
plan_untouched "your firewall, your SSH configuration, and any existing user"
plan_untouched "the system Python, and every other service on this machine"
plan_untouched "anything inside a home directory"
plan_untouched "inbound ports: the bot makes outgoing connections only, unless you turn the web page on"

show_plan "What this will change on this machine"
if [ "$DRY_RUN" = 0 ] && ! confirm "Go ahead?" yes; then
  say "Nothing was changed."
  forget_undo
  exit 0
fi
checkpoint "started"

# -------------------------------------------------------------- packages ----
apt_install() {
  [ "$PACKAGES" = 1 ] || return 0
  local missing=() pkg
  for pkg in "$@"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
  done
  if [ ${#missing[@]} -eq 0 ]; then
    ok "System packages: already installed ($*)"
    return 0
  fi
  head2 "System packages"
  system_change "apt-get install ${missing[*]}" \
    "the pieces this install needs that this machine does not have yet"
  retry 3 "Updating the package lists" \
    as_root env DEBIAN_FRONTEND=noninteractive apt-get update -qq
  retry 3 "Installing ${missing[*]}" \
    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing[@]}"
}

# shellcheck disable=SC2086  # our own list, deliberately word-split
apt_install $PACKAGE_LIST
checkpoint "packages"

install_docker() {
  if on_system_path docker && docker compose version >/dev/null 2>&1; then
    ok "Docker is already installed."
    return 0
  fi
  [ "$PACKAGES" = 1 ] || die "Docker is missing, and --no-packages was given" \
    "Install Docker Engine and its compose plugin, then run this again."
  head2 "Docker"
  system_change "Add Docker's apt repository and install docker-ce with the compose plugin" \
    "compose is what runs the bot, and optionally the HTTPS front; the distribution's docker.io has no compose"
  if [ "$DRY_RUN" = 1 ]; then note "would install Docker"; return 0; fi

  local codename distro="ubuntu" maybe_sudo=""
  [ "$(id -u)" = 0 ] || maybe_sudo="sudo"
  codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-}")"
  [ -n "$codename" ] || die "cannot tell which Debian or Ubuntu release this is" \
    "Install Docker yourself, then run this again with --no-packages."
  case "${ID:-ubuntu}" in debian) distro=debian ;; esac

  step "Making a folder for the repository's signing key" as_root install -m 0755 -d /etc/apt/keyrings
  undo_on_failure "rm -f /etc/apt/keyrings/docker.gpg /etc/apt/sources.list.d/docker.list"
  retry 3 "Fetching Docker's signing key" sh -c \
    "curl -fsSL 'https://download.docker.com/linux/${distro}/gpg' | ${maybe_sudo} gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
  step "Making the key readable" as_root chmod a+r /etc/apt/keyrings/docker.gpg
  step "Adding the repository to apt" sh -c \
    "echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${distro} ${codename} stable' | ${maybe_sudo} tee /etc/apt/sources.list.d/docker.list >/dev/null"
  retry 3 "Updating the package lists" as_root env DEBIAN_FRONTEND=noninteractive apt-get update -qq
  retry 3 "Installing Docker" as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  try_step "Setting Docker to start at boot" as_root systemctl enable --now docker
  on_system_path docker || die "Docker installed but is not on the system PATH"
  forget_undo
}

install_uv() {
  if on_system_path uv; then
    ok "uv is already installed ($(uv --version 2>/dev/null || echo 'version unknown'))."
    return 0
  fi
  [ "$PACKAGES" = 1 ] || die "uv is missing, and --no-packages was given" \
    "Install it from https://docs.astral.sh/uv/ into /usr/local/bin, then run this again."
  head2 "uv, the Python installer"
  if have uv; then
    note "uv exists for $(id -un) only, in a place the ${SERVICE_USER} account cannot reach."
  fi
  system_change "Install uv into /usr/local/bin" \
    "it fetches the Python this program needs and builds its virtualenv; your system Python is left exactly as it is"
  if [ "$DRY_RUN" = 1 ]; then note "would install uv"; return 0; fi
  local script
  script="$(mktemp)"
  undo_on_failure "rm -f ${script}"
  retry 3 "Downloading the uv installer" curl -LsSf https://astral.sh/uv/install.sh -o "$script"
  step "Running the uv installer" as_root env UV_INSTALL_DIR=/usr/local/bin sh "$script"
  rm -f "$script"
  export PATH="/usr/local/bin:$PATH"
  on_system_path uv \
    || die "uv was installed but is not in /usr/local/bin, where every account can find it" \
           "Install it there by hand:" \
           "  curl -LsSf https://astral.sh/uv/install.sh | sudo UV_INSTALL_DIR=/usr/local/bin sh"
  forget_undo
}

if [ "$MODE" = docker ]; then install_docker; else install_uv; fi
checkpoint "runtime"

# -------------------------------------------------------------- the code ----
# A deploy key or a token means "clone it", so upgrades have a credential: then the checkout this
# runs from is only where the script came from.
if [ -z "$SOURCE_DIR" ] && [ -z "$DEPLOY_KEY" ] && [ -z "${GITHUB_TOKEN:-}" ] \
   && [ -f "${HERE}/../pyproject.toml" ] \
   && grep -q 'name = "familydb"' "${HERE}/../pyproject.toml" 2>/dev/null; then
  SOURCE_DIR="$(cd -- "${HERE}/.." && pwd -P)"
  note "Running from a checkout at ${SOURCE_DIR}, so that is what will be installed."
fi

fetch_code() {
  head2 "The code"
  if [ -d "${TARGET}/.git" ] || [ -f "${TARGET}/pyproject.toml" ]; then
    ok "Already in ${TARGET}, so it is left alone."
    note "To update it instead: ${TARGET}/scripts/maintain.sh upgrade"
    return 0
  fi
  system_change "Create ${TARGET} and put the code in it" \
    "apart from one systemd unit, this is the only place on the machine the install writes to"
  if [ "$DRY_RUN" = 1 ]; then note "would put the code in ${TARGET}"; return 0; fi
  step "Creating ${TARGET}" as_root mkdir -p "$TARGET"
  # A half-written directory is worse than none: undo it if anything below fails.
  undo_on_failure "rm -rf ${TARGET}"

  if [ -n "$SOURCE_DIR" ]; then
    if [ -d "$SOURCE_DIR" ]; then
      if [ "$(cd "$SOURCE_DIR" && pwd -P)" = "$(cd "$TARGET" && pwd -P)" ]; then
        ok "The source is the target, so there is nothing to copy."
        forget_undo
        return 0
      fi
      step "Copying ${SOURCE_DIR} into ${TARGET}" as_root cp -a "${SOURCE_DIR}/." "${TARGET}/"
      # cp -a keeps the owner of the copy (you), and the code is meant to be root's.
      step "Making the code root's" as_root chown -R root:root "$TARGET"
    elif [ -f "$SOURCE_DIR" ]; then
      step "Unpacking ${SOURCE_DIR}" as_root tar -xzf "$SOURCE_DIR" -C "$TARGET" --strip-components=1 \
        --no-same-owner
    else
      die "--from ${SOURCE_DIR} is neither a directory nor a file" \
          "Point it at a checkout, or at a .tar.gz of one."
    fi
    [ -f "${TARGET}/pyproject.toml" ] || die "${SOURCE_DIR} does not contain a FamilyDB checkout" \
      "There should be a pyproject.toml at the top of it."
    forget_undo
    return 0
  fi

  local url="$REPO"
  local -a git_env=()
  if [ -n "$DEPLOY_KEY" ]; then
    [ -r "$DEPLOY_KEY" ] || die "cannot read the deploy key at ${DEPLOY_KEY}" \
      "Check the path, and that this account can read the file."
    as_root chmod 600 "$DEPLOY_KEY" 2>/dev/null || true
    case "$url" in https://github.com/*) url="git@github.com:${url#https://github.com/}" ;; esac
    git_env=(GIT_SSH_COMMAND="ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new")
    note "Cloning over SSH with the deploy key."
  elif [ -n "${GITHUB_TOKEN:-}" ]; then
    case "$url" in
      https://github.com/*) url="https://x-access-token:${GITHUB_TOKEN}@github.com/${url#https://github.com/}" ;;
      *) die "GITHUB_TOKEN only helps with an https://github.com/... repository" ;;
    esac
    note "Cloning over HTTPS with the token from the environment."
  else
    note "No deploy key and no GITHUB_TOKEN, so this only works if the repository is public."
  fi

  local -a clone=(git clone --quiet)
  [ -n "$REF" ] && clone+=(--branch "$REF")
  on_failure_hint "A private repository needs credentials: --deploy-key FILE, GITHUB_TOKEN=..., or --from PATH for a copy you put on the machine yourself. docs/INSTALL.md, 'Getting the code onto the box', walks through all three."
  if as_root env "${git_env[@]}" "${clone[@]}" "$url" "$TARGET" 2>>"${LOG_FILE:-/dev/null}"; then
    ok "Cloned ${REPO}"
  elif [ -n "$REF" ]; then
    # --branch will not take a commit sha, so clone everything and check it out afterwards.
    retry 2 "Cloning the repository" as_root env "${git_env[@]}" git clone --quiet "$url" "$TARGET"
    step "Checking out ${REF}" as_root env "${git_env[@]}" git -C "$TARGET" checkout --quiet "$REF"
  else
    die "could not clone ${REPO}" \
        "Nothing was left behind. The usual causes:" \
        "  · the repository is private and no credentials were given" \
        "  · the deploy key has no access, or is the wrong key" \
        "  · the token has expired, or cannot read this repository" \
        "Check a deploy key with:  ssh -T git@github.com -i ${DEPLOY_KEY:-<key>}"
  fi
  on_failure_hint "Everything that already worked is still in place; fix what is above and run this again. docs/INSTALL.md has a section on each failure."
  if [ -n "$DEPLOY_KEY" ]; then
    # Keep the deploy key wired up, so `maintain.sh upgrade` can fetch later. The key itself
    # stays where it is; only the path to it is written down.
    step "Remembering the deploy key for future upgrades" \
      as_root git -C "$TARGET" config core.sshCommand \
        "ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes"
    note "Upgrades will use ${DEPLOY_KEY}. Keep that file where it is, readable by root."
  else
    # Never leave a token sitting in .git/config for whoever reads it next. The cost is that
    # upgrades have no credential; maintain.sh says so plainly when a fetch fails.
    step "Clearing any credential out of the saved remote" \
      as_root git -C "$TARGET" remote set-url origin "$REPO"
    [ -n "${GITHUB_TOKEN:-}" ] && note "The token was not written down, so an upgrade will ask for one again."
  fi
  if [ -z "$REF" ]; then
    local kind name
    read -r kind name <<<"$(wanted_version "$TARGET")"
    if [ "$kind" = tag ]; then
      step "Checking out ${name}, the newest release" as_root git -C "$TARGET" checkout --quiet "$name"
    elif [ "$kind" = branch ]; then
      note "The newest version is still being built, so this is ${name}, where it is being built."
    fi
  fi
  forget_undo
}

fetch_code
checkpoint "code"

INSTALLER="${TARGET}/scripts/install.sh"
if [ "$DRY_RUN" = 0 ]; then
  [ -f "$INSTALLER" ] || die "there is no installer at ${INSTALLER}" \
    "The copy in ${TARGET} is incomplete. Remove it and run this again."
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  head2 "The service account"
  system_change "Create the system user '${SERVICE_USER}'" \
    "no password, no login shell, and it owns only the configuration and the database"
  step "Creating ${SERVICE_USER}" \
    as_root useradd --system --home-dir "$TARGET" --shell /usr/sbin/nologin "$SERVICE_USER"
else
  ok "The ${SERVICE_USER} account already exists."
fi
# The code stays owned by root and world readable, so the bot can run it but cannot rewrite it.
try_step "Making sure the code is not writable by anyone but root" as_root chmod -R go-w "$TARGET"
checkpoint "user"

if [ "$RUN_INSTALL" = 0 ]; then
  head2 "Stopping here, as asked"
  say "The machine is ready and the code is in ${TARGET}."
  say "Configure it whenever you like with: sudo ${INSTALLER}"
  forget_undo
  exit 0
fi

# ------------------------------------------------------------- configure ----
head2 "Configuring"
say "scripts/install.sh takes over now. It asks where the web page will be reached and who you"
say "are, writes ${TARGET}/.env, installs, and adds you as the first family member."
say ""

INSTALL_ARGS=("--mode" "$MODE")
[ ${#PASS_THROUGH[@]} -gt 0 ] && INSTALL_ARGS+=("${PASS_THROUGH[@]}")

# sudo scrubs the environment, so anything the installer should see has to be named: the answers
# it documents, and the proxy and certificate settings a machine behind one needs to reach PyPI.
FORWARD_VARS=(
  PROVIDER ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY
  FAMILYDB_TZ HOME_AREA HOME_LAT HOME_LON WEATHER_UNITS
  TELEGRAM_BOT_TOKEN WEB_ENABLED WEB_HOST WEB_PORT WEB_PASSWORD WEB_TOOLS_ENABLED
  WEB_DOMAIN DIGEST_CHAT_ID BACKUPS ADMIN_NAME NO_COLOR TERM
  HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
  SSL_CERT_FILE SSL_CERT_DIR REQUESTS_CA_BUNDLE CURL_CA_BUNDLE GIT_SSL_CAINFO
)
forwarded=(HOME="$TARGET" PATH="$SYSTEM_PATH")
for name in "${FORWARD_VARS[@]}"; do
  [ -n "${!name:-}" ] && forwarded+=("${name}=${!name}")
done

# The installer runs as root because it writes a systemd unit. It ends by handing .env and data/
# to the service account; the code itself stays root-owned, so the bot cannot rewrite its program.
if [ "$DRY_RUN" = 1 ]; then
  note "would run: ${INSTALLER} ${INSTALL_ARGS[*]}"
else
  # Not wrapped in `step`: this one asks questions, so its output must reach the terminal.
  # shellcheck disable=SC2034  # lib/common.sh names this in its failure report.
  FAILED_STEP="running scripts/install.sh"
  if ! (cd "$TARGET" && as_root env "${forwarded[@]}" "$INSTALLER" "${INSTALL_ARGS[@]}"); then
    die "the configuration step failed, and it explained why above" \
        "Everything before it is still in place. Fix what it reported, then run just that part:" \
        "  sudo ${INSTALLER}" \
        "There is no need to run this bootstrap again."
  fi
  # shellcheck disable=SC2034  # cleared so a later failure does not name this step.
  FAILED_STEP=""
fi
checkpoint "configured"

# --------------------------------------------------------------- service ----
if [ "$START" = 1 ] && [ "$DRY_RUN" = 0 ]; then
  head2 "Starting it"
  if [ "$MODE" = docker ]; then
    step "Starting the containers" as_root docker compose --project-directory "$TARGET" up -d
    note "Watch them with: docker compose --project-directory ${TARGET} logs -f bot"
  elif [ -f /etc/systemd/system/familydb.service ]; then
    try_step "Setting it to start at boot" as_root systemctl enable familydb
    step "Starting the service" as_root systemctl restart familydb
    sleep 3
    if as_root systemctl is-active --quiet familydb; then
      ok "Running, and it will start again by itself after a reboot."
    else
      warn "The service started and then stopped. The last 20 lines of its log:"
      as_root journalctl -u familydb -n 20 --no-pager >&2 || true
      note ""
      note "What this usually means: a setting it will not accept, or a file it cannot write."
      note "What to try:"
      note "  cd ${TARGET} && sudo -u ${SERVICE_USER} .venv/bin/familydb doctor"
      note "  sudo systemctl status familydb"
      note "Then: sudo systemctl restart familydb"
    fi
  else
    warn "No systemd unit was installed, so nothing has been started."
    note "The installer says why above. Run it in the foreground meanwhile:"
    note "  cd ${TARGET} && sudo -u ${SERVICE_USER} .venv/bin/familydb run"
  fi
fi
checkpoint "started"

# -------------------------------------------------------------- checking ----
if [ "$DRY_RUN" = 0 ]; then
  head2 "Checking it over"
  say "Every line below is something that was actually looked at. A '!' is usually just"
  say "something not set up yet, which is normal on a first install."
  say ""
  FAMILYDB="${TARGET}/.venv/bin/familydb"
  if [ "$MODE" = docker ]; then
    as_root docker compose --project-directory "$TARGET" run --rm -T bot familydb doctor || true
  elif [ -x "$FAMILYDB" ]; then
    (cd "$TARGET" && as_service_user env "${forwarded[@]}" "$FAMILYDB" doctor) || true
  else
    warn "There is no familydb command at ${FAMILYDB}, so nothing could be checked."
    note "The install did not finish. Run: sudo ${INSTALLER}"
  fi
fi
checkpoint "checked"

# ----------------------------------------------------------- what is next ----
head2 "Done"
if [ "$DRY_RUN" = 1 ]; then
  say "Nothing was changed. Run it again without --dry-run to do it for real."
  forget_undo
  exit 0
fi

WEB_LINE=""; host=""; port=""; domain=""
if as_root test -r "${TARGET}/.env"; then
  read_env() { as_root grep -E "^${1}=" "${TARGET}/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "'\"" || true; }
  enabled="$(read_env WEB_ENABLED)"
  port="$(read_env WEB_PORT)"
  host="$(read_env WEB_HOST)"
  domain="$(read_env WEB_DOMAIN)"
  if [ -n "$domain" ]; then
    WEB_LINE="https://${domain}/"
  elif [ "$enabled" = true ]; then
    shown="${host:-127.0.0.1}"
    case "$shown" in 0.0.0.0|::) shown="$(hostname -I 2>/dev/null | awk '{print $1}')" ;; esac
    WEB_LINE="http://${shown:-127.0.0.1}:${port:-8080}/"
  fi
fi

if [ -n "$WEB_LINE" ]; then
  say "The web page: ${B}${WEB_LINE}${OFF}"
  say "  Sign in with the family password. Its home page lists what is left to set up, in the"
  say "  order it matters: a model key, Telegram, Google Calendar and where home is."
  if [ -n "$domain" ]; then
    note "  The domain must point at this machine, with ports 80 and 443 open (sudo ufw allow 80,443/tcp)."
  else
    case "${host:-}" in
      127.0.0.1|localhost|"")
        note "  It is bound to this machine only, which is the safe default. Reach it over SSH:"
        note "    ssh -L ${port:-8080}:127.0.0.1:${port:-8080} ${SUDO_USER:-$(id -un)}@$(hostname -I 2>/dev/null | awk '{print $1}')"
        note "  then open http://127.0.0.1:${port:-8080}/ on your own computer."
        ;;
    esac
  fi
  say ""
fi

if [ "$MODE" = docker ]; then
  say "Watch it:      docker compose --project-directory ${TARGET} logs -f bot"
  say "Check it:      docker compose --project-directory ${TARGET} run --rm bot familydb doctor"
else
  say "Watch it:      sudo journalctl -u familydb -f"
  say "Check it:      cd ${TARGET} && sudo -u ${SERVICE_USER} .venv/bin/familydb doctor"
fi
say "Look after it: sudo ${TARGET}/scripts/maintain.sh --help"
say "Remove it:     sudo ${TARGET}/scripts/uninstall.sh --help"
say "Read up:       ${TARGET}/RUNBOOK.md, and ${TARGET}/docs/INSTALL.md"
if [ "$WARNINGS" -gt 0 ]; then
  say ""
  warn "${WARNINGS} warning(s) above are worth reading before you walk away."
fi
[ -n "$LOG_FILE" ] && note "A transcript of this run is at ${LOG_FILE}"

forget_undo
