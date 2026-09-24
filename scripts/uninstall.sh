#!/usr/bin/env bash
# Take FamilyDB off this machine, either keeping what the family said or removing that too.
#
#   scripts/uninstall.sh              stop it, remove the service and the installed code, and
#                                     keep .env, data/ and the backups. This is what you want
#                                     before reinstalling.
#   scripts/uninstall.sh --purge      remove all of that as well, including the database.
#   scripts/uninstall.sh --from-zero everything --purge does, and what the installer put around
#                                     it: Caddy, the ports, the deploy key, uv and the logs. The
#                                     server as it was before FamilyDB, for testing an install.
#
# It prints what it is about to remove, and what it is leaving, before removing anything.
#
# The database is the only copy of everything the family has ever said, so --purge takes a
# backup first unless told not to, will not run without a typed confirmation, and refuses to
# touch a directory that does not look like a FamilyDB install.
set -euo pipefail

# shellcheck disable=SC2034  # read by lib/common.sh when it opens the transcript.
SCRIPT_ARGS="$*"
ORIGINAL_ARGS=("$@")
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -r "${HERE}/lib/common.sh" ]; then
  # shellcheck source=lib/common.sh
  . "${HERE}/lib/common.sh"
else
  printf 'This script needs scripts/lib/common.sh beside it.\n' >&2
  exit 1
fi

TARGET=""
SERVICE_USER="familydb"
PURGE=0
FORCE=0
DRY_RUN=0
ASSUME_YES=0
BACKUP=1
BACKUP_ASKED=0
BACKUP_DIR=""
REMOVE_USER=1
FROM_ZERO=0

usage() {
  cat <<'USAGE'
Remove FamilyDB from this machine.

  scripts/uninstall.sh [options]

What is removed
  (default)            The service and the unit, the virtualenv, the containers and the image.
                       Kept: .env, data/ (the database, the Google token, the login key),
                       backups/ and caddy/. Reinstalling over this picks up where it left off.
  --purge              All of the above, and everything that was kept: the database, the
                       configuration, the backups and the service user. Nothing is left.
  --from-zero          All of --purge, and everything the install did around it, so the server is
                       as it was before FamilyDB: what its ledger in /var/lib/familydb-install
                       recorded (packages it added, files, links, accounts, cron lines, firewall
                       rules; replaced files are put back), plus what older versions and the
                       guide's steps by hand could leave: Caddy when it serves nothing but
                       FamilyDB, uv, the deploy key, copies of the code, backups and logs. Keeps
                       no backup unless --backup-to is given. Asks twice.

Options
  --target DIR         The install to remove. Default: the checkout this script is in.
  --user NAME          The system user to remove on --purge. Default: familydb.
  --keep-user          Leave the system user alone on --purge.
  --backup-to DIR      Where --purge writes its backup. Default: /var/backups/familydb. With
                       --from-zero, the only way to keep one.
  --no-backup          Do not back the database up before --purge. Say this deliberately.
  --force              Do not ask. For scripts; with --purge this deletes the database at once.
  --dry-run            Say what would happen; change nothing.
  -h, --help           This text.

Examples
  scripts/uninstall.sh                          # clean slate for a reinstall
  scripts/uninstall.sh --purge                  # remove it and everything it knows
  scripts/uninstall.sh --purge --backup-to /mnt/usb
  sudo /opt/familydb/scripts/uninstall.sh --from-zero    # back to before FamilyDB
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --user) SERVICE_USER="${2:-}"; shift 2 ;;
    --user=*) SERVICE_USER="${1#*=}"; shift ;;
    --keep-user) REMOVE_USER=0; shift ;;
    --backup-to) BACKUP_DIR="${2:-}"; BACKUP_ASKED=1; shift 2 ;;
    --backup-to=*) BACKUP_DIR="${1#*=}"; BACKUP_ASKED=1; shift ;;
    --no-backup) BACKUP=0; shift ;;
    --purge) PURGE=1; shift ;;
    --from-zero) PURGE=1; FROM_ZERO=1; shift ;;
    --force|--yes|-y) FORCE=1; ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done
export ASSUME_YES DRY_RUN
# From zero means nothing left behind, a backup included, unless one is asked for by name.
[ "$FROM_ZERO" = 1 ] && [ "$BACKUP_ASKED" = 0 ] && BACKUP=0

# Removing everything means removing this script too. Run from a copy outside the install instead,
# so that the last step can take the whole directory, and so nothing is read from a deleted file.
if [ "$PURGE" = 1 ] && [ -z "${FAMILYDB_UNINSTALL_COPY:-}" ]; then
  install_dir="${TARGET:-$(cd -- "${HERE}/.." && pwd -P)}"
  case "$HERE" in
    "${install_dir}"/*)
      copy="$(mktemp -d /tmp/familydb-uninstall.XXXXXX)"
      mkdir -p "${copy}/lib"
      cp "${HERE}/uninstall.sh" "${copy}/uninstall.sh"
      cp "${HERE}/lib/"*.sh "${copy}/lib/"
      FAMILYDB_UNINSTALL_COPY="$copy" exec bash "${copy}/uninstall.sh" --target "$install_dir" \
        "${ORIGINAL_ARGS[@]}"
      ;;
  esac
fi

log_to "/var/log/familydb-uninstall.log"
enable_failure_reporting
on_failure_hint "Nothing is removed until the step that removes it runs, so a failure here leaves the install as it was. docs/INSTALL.md, 'Removing it', covers the rest."

# ---------------------------------------------- what the installer put around it ----
caddy_serves_only_familydb() { # nothing in the Caddyfile but what FamilyDB's setups write
  local file=/etc/caddy/Caddyfile
  as_root test -f "$file" || return 0
  as_root grep -q "FamilyDB" "$file" && return 0
  # Take out the lines FamilyDB's setups write, and the package's own default page. Whatever is
  # left is somebody else's site, and then Caddy is not ours to remove.
  ! as_root sed -e 's/#.*//' "$file" | grep -vE \
    '^[[:space:]]*$|^[[:space:]]*[}{][[:space:]]*$|^[[:space:]]*[^[:space:]]+[[:space:]]*\{[[:space:]]*$|^[[:space:]]*tls([[:space:]]+internal)?([[:space:]]*\{)?[[:space:]]*$|^[[:space:]]*issuer[[:space:]]+acme[[:space:]]*\{[[:space:]]*$|^[[:space:]]*profile[[:space:]]+shortlived[[:space:]]*$|^[[:space:]]*reverse_proxy[[:space:]]+(127\.0\.0\.1|localhost):[0-9]+[[:space:]]*$|^[[:space:]]*root[[:space:]]+\*[[:space:]]+/usr/share/caddy[[:space:]]*$|^[[:space:]]*file_server[[:space:]]*$' \
    | grep -q .
}

# Everything --from-zero removes besides the install itself, found before anything is removed:
# first what the install wrote down in its ledger as it made each change, then everything an older
# version, or the older guide's steps by hand, could have left without writing it down. Each is
# listed in the plan by name before anything happens.
ZERO_PATHS=()     # files, directories and links to delete
ZERO_EMPTY=()     # directories the install made that are deleted only if left empty
ZERO_PACKAGES=()  # packages the install added, dependencies included
ZERO_USERS=()
ZERO_GROUPS=()
ZERO_RESTORE=()   # files the install replaced, put back as they were
ZERO_PROFILES=()  # shell profiles the uv installer added a line to
ZERO_UFW=0
ZERO_CRONTAB=0    # root had no crontab before the install
ZERO_NGINX=()
ZERO_CERT=""
ZERO_KNOWN_HOSTS=0
ZERO_APT_UPDATE=0
ZERO_CADDY="none" # none, remove (it serves only FamilyDB) or keep (it serves something else too)
HAS_LEDGER=0
# A ledger begun by a fresh install is the whole story. Anything less (an install from before the
# ledger, which a newer script then added to) also gets the checks for what older versions did.
WHOLE_LEDGER=0

_add_path() { # _add_path PATH - once, and only if it is there
  local path="$1" seen
  as_root test -e "$path" || as_root test -L "$path" || return 0
  # The install itself, its unit and this run's own log have steps of their own.
  case "$path" in
    "$TARGET"|"${TARGET}"/*|/etc/systemd/system/familydb.service|"${LOG_FILE:-/nonexistent}") return 0 ;;
  esac
  for seen in "${ZERO_PATHS[@]}"; do [ "$seen" = "$path" ] && return 0; done
  ZERO_PATHS+=("$path")
}

_add_package() {
  local seen
  for seen in "${ZERO_PACKAGES[@]}"; do [ "$seen" = "$1" ] && return 0; done
  dpkg -s "${1%%:*}" >/dev/null 2>&1 && ZERO_PACKAGES+=("$1")
  return 0
}

_is_private_key() { as_root test -f "$1" && as_root head -1 "$1" 2>/dev/null | grep -q 'PRIVATE KEY'; }

_is_familydb_copy() { # a copy of the code: its pyproject, or the scripts folder on its own
  as_root test -f "${1}/pyproject.toml" && as_root grep -q 'name = "familydb"' "${1}/pyproject.toml" && return 0
  as_root test -f "${1}/bootstrap.sh" && as_root grep -q 'FamilyDB' "${1}/bootstrap.sh" \
    && as_root test -f "${1}/lib/common.sh"
}

take_inventory() {
  local kind what home file key
  if as_root test -f "$LEDGER"; then
    HAS_LEDGER=1
    while IFS=$'\t' read -r kind what; do
      case "$kind" in
        began) WHOLE_LEDGER=1 ;;
        package) _add_package "$what"; [ "$what" = caddy ] && ZERO_CADDY="remove" ;;
        file|link|keyring) _add_path "$what" ;;
        apt-source) _add_path "$what"; ZERO_APT_UPDATE=1 ;;
        dir)
          case "$what" in
            *familydb*) _add_path "$what" ;;
            *) as_root test -d "$what" && ZERO_EMPTY+=("$what") ;;
          esac ;;
        replaced) ZERO_RESTORE+=("$what") ;;
        user) ZERO_USERS+=("$what") ;;
        group) ZERO_GROUPS+=("$what") ;;
        ufw) ZERO_UFW=1 ;;
        crontab) ZERO_CRONTAB=1 ;;
      esac
    done < <(as_root cat "$LEDGER")
  fi

  # Whatever the ledger says, anything named for FamilyDB is FamilyDB's. The deploy key, wherever
  # the guide ever said to make one:
  for key in "$DEPLOY_KEY_FILE" /root/familydb_deploy /root/.ssh/familydb_deploy \
             /home/*/.ssh/familydb_deploy /home/*/familydb_deploy; do
    [ -n "$key" ] && _is_private_key "$key" && { _add_path "$key"; _add_path "${key}.pub"; }
  done
  # What the guide's steps by hand left in a home directory: copies of the code, the archive it
  # was carried in, and backups copied out to be fetched. A folder named FamilyDB or scripts
  # counts only when it has no .git of its own: an unpacked archive, not somebody's working clone.
  for home in /root /home/*; do
    as_root test -d "$home" || continue
    for file in familydb-scripts familydb-code FamilyDB scripts; do
      as_root test -d "${home}/${file}" && _is_familydb_copy "${home}/${file}" || continue
      case "$file" in
        FamilyDB|scripts) as_root test -e "${home}/${file}/.git" && continue ;;
      esac
      _add_path "${home}/${file}"
    done
    for file in familydb.tar.gz familydb-backups.tar.gz; do _add_path "${home}/${file}"; done
    while IFS= read -r file; do _add_path "$file"; done \
      < <(as_root find "$home" -maxdepth 1 -name 'familydb-*.sqlite3' 2>/dev/null)
  done
  # Backups an earlier --purge left, the logs, and anything an earlier run left in /tmp.
  _add_path /var/backups/familydb
  while IFS= read -r file; do _add_path "$file"; done \
    < <(as_root find /var/log -maxdepth 1 -name 'familydb-*' 2>/dev/null)
  while IFS= read -r file; do
    [ "$file" = "${FAMILYDB_UNINSTALL_COPY:-}" ] || _add_path "$file"
  done < <(as_root find /tmp -maxdepth 1 -name 'familydb-*' 2>/dev/null)
  # nginx, when the guide's nginx configuration was used instead of Caddy, and its certificate.
  for file in /etc/nginx/sites-enabled/familydb /etc/nginx/sites-available/familydb; do
    as_root test -e "$file" || as_root test -L "$file" || continue
    ZERO_NGINX+=("$file")
  done
  if [ -n "$WEB_DOMAIN_NOW" ] && ! printf '%s' "$WEB_DOMAIN_NOW" | grep -Eq '^[0-9.]+$' \
     && have certbot && as_root test -d "/etc/letsencrypt/live/${WEB_DOMAIN_NOW}"; then
    ZERO_CERT="$WEB_DOMAIN_NOW"
  fi

  # What only an install from before the ledger could have left without writing it down. With a
  # ledger begun by a fresh install, the ledger alone says what the install added, and anything
  # else here (a uv of your own, say) was here first and stays.
  # And never on a machine FamilyDB was not installed on: then a uv, say, is somebody else's.
  [ "$WHOLE_LEDGER" = 1 ] || ! familydb_was_here || older_leftovers

  # Caddy, when it is going: its package, folders, account and the package source it came from.
  if [ "$ZERO_CADDY" = remove ]; then
    _add_package caddy
    for file in /etc/caddy /var/lib/caddy /var/log/caddy /etc/apt/sources.list.d/caddy-stable.list \
                /usr/share/keyrings/caddy-stable-archive-keyring.gpg; do
      _add_path "$file"
    done
    as_root test -e /etc/apt/sources.list.d/caddy-stable.list && ZERO_APT_UPDATE=1
    id caddy >/dev/null 2>&1 && ZERO_USERS+=(caddy)
    getent group caddy >/dev/null 2>&1 && ZERO_GROUPS+=(caddy)
  elif have caddy && [ "$ZERO_CADDY" = none ]; then
    ZERO_CADDY="keep"
  fi
  # A rule the ledger recorded that is no longer there needs nothing done.
  if [ "$ZERO_UFW" = 1 ] && ! { have ufw && as_root ufw status 2>/dev/null | grep -qE '^80,443/tcp'; }; then
    ZERO_UFW=0
  fi

  _add_path "$LEDGER_DIR"
}

familydb_was_here() { # anything an install, of any version, always leaves until it is removed
  [ "$INSTALL_PRESENT" = 1 ] || [ "$HAS_LEDGER" = 1 ] && return 0
  id "$SERVICE_USER" >/dev/null 2>&1 && return 0
  as_root test -f /etc/systemd/system/familydb.service && return 0
  as_root test -e /var/backups/familydb && return 0
  _is_private_key /root/familydb_deploy && return 0
  # Not this run's own log, which exists because this is running.
  as_root find /var/log -maxdepth 1 -name 'familydb-*' ! -name 'familydb-uninstall.log' 2>/dev/null \
    | grep -q .
}

older_leftovers() {
  local file rc
  # uv, when an older installer, run with sudo, put it in root's home: the binaries, the receipt,
  # its caches, and the line it added to each of root's shell profiles. Nobody else's home: there,
  # uv is that person's own.
  if as_root test -f /root/.local/bin/uv; then
    for file in uv uvx env env.fish; do _add_path "/root/.local/bin/${file}"; done
    _add_path /root/.config/fish/conf.d/uv.env.fish
    for rc in .profile .bashrc .bash_profile .bash_login .zshrc .zshenv; do
      as_root grep -qF '. "$HOME/.local/bin/env"' "/root/${rc}" 2>/dev/null && ZERO_PROFILES+=("/root/${rc}")
    done
    _add_path /root/.cache/uv
    _add_path /root/.local/share/uv
  fi
  _add_path /root/.config/uv/uv-receipt.json
  # uv in /usr/local/bin, which only the installer puts there on a FamilyDB server.
  _add_path /usr/local/bin/uv
  _add_path /usr/local/bin/uvx
  # Caddy, when it serves nothing but FamilyDB: an older installer, or the guide's steps by hand.
  if [ "$ZERO_CADDY" = none ] && { have caddy || as_root test -d /etc/caddy; }; then
    if caddy_serves_only_familydb; then ZERO_CADDY="remove"; else ZERO_CADDY="keep"; fi
  fi
  # The firewall rule: the only reason for it on this server was FamilyDB's page.
  have ufw && as_root ufw status 2>/dev/null | grep -qE '^80,443/tcp' && ZERO_UFW=1
  # GitHub's host key in root's known_hosts, which installs from before the ledger put there.
  as_root grep -q '^github\.com[ ,]' /root/.ssh/known_hosts 2>/dev/null && ZERO_KNOWN_HOSTS=1
  return 0
}

plan_from_zero() {
  local item
  [ "$ZERO_CADDY" = remove ] && plan_item "Remove Caddy, its configuration, certificates and account" \
    "it was there for FamilyDB's page, and serves nothing else here"
  [ ${#ZERO_PACKAGES[@]} -gt 0 ] && plan_item "Remove the packages the install added: ${ZERO_PACKAGES[*]}" \
    "they were not on this server before FamilyDB; packages that were are left alone"
  for item in "${ZERO_RESTORE[@]}"; do
    plan_item "Put ${item} back as it was" "the install replaced it, and kept the original"
  done
  for item in "${ZERO_PATHS[@]}"; do
    plan_item "Delete ${item}" "$(_why "$item")"
  done
  for item in "${ZERO_EMPTY[@]}"; do
    plan_item "Remove ${item} if nothing else is in it" "the install made it"
  done
  [ ${#ZERO_USERS[@]} -gt 0 ] && plan_item "Remove the accounts ${ZERO_USERS[*]}" "they were made for this"
  [ "$ZERO_UFW" = 1 ] && plan_item "Close ports 80 and 443 in ufw" "they were opened for the page"
  [ "$ZERO_CRONTAB" = 1 ] && plan_item "Remove root's crontab once the backup line is gone" \
    "root had none before FamilyDB"
  for item in "${ZERO_PROFILES[@]}"; do
    plan_item "Take the line uv added out of ${item}" "an older installer put uv there"
  done
  for item in "${ZERO_NGINX[@]}"; do plan_item "Delete ${item}" "FamilyDB's site in nginx"; done
  [ -n "$ZERO_CERT" ] && plan_item "Delete the certificate for ${ZERO_CERT}" "certbot got it for the page"
  [ "$ZERO_KNOWN_HOSTS" = 1 ] && plan_item "Take GitHub out of root's known_hosts" \
    "the install put it there when it fetched the code"
  return 0
}

_why() {
  case "$1" in
    *familydb_deploy*) echo "the key that let this server read the code; remove it on GitHub too" ;;
    */.local/bin/*|*/uv*|*uvx*) echo "uv, which the installer put there for FamilyDB" ;;
    */var/backups/familydb*|*.sqlite3|*backups.tar.gz) echo "a backup of FamilyDB's database" ;;
    /var/log/*) echo "a log of installing or looking after FamilyDB" ;;
    /tmp/*) echo "left over from an earlier run" ;;
    *caddy*) echo "Caddy's, which goes with it" ;;
    /etc/systemd/*) echo "how systemd started FamilyDB" ;;
    /etc/apt/*|/usr/share/keyrings/*) echo "a package source the install added" ;;
    "$LEDGER_DIR") echo "the install's record of what it changed, which goes last" ;;
    *) echo "left by the install" ;;
  esac
}

remove_what_was_around_it() {
  head2 "Removing what the install set up around it"
  local item home
  if [ "$ZERO_CADDY" = remove ] && have systemctl; then
    try_step "Stopping Caddy" as_root systemctl disable --now caddy
  fi
  if [ ${#ZERO_PACKAGES[@]} -gt 0 ]; then
    step "Removing ${ZERO_PACKAGES[*]}" as_root env DEBIAN_FRONTEND=noninteractive \
      apt-get purge -y -qq "${ZERO_PACKAGES[@]}"
  fi
  for item in "${ZERO_NGINX[@]}"; do step "Deleting ${item}" as_root rm -f "$item"; done
  if [ ${#ZERO_NGINX[@]} -gt 0 ] && have nginx; then
    try_step "Reloading nginx" sh -c "$(declare -f as_root); as_root nginx -t && as_root systemctl reload nginx"
  fi
  if [ -n "$ZERO_CERT" ]; then
    try_step "Deleting the certificate for ${ZERO_CERT}" \
      as_root certbot delete --non-interactive --cert-name "$ZERO_CERT"
  fi
  if [ "$ZERO_UFW" = 1 ]; then
    try_step "Closing ports 80 and 443 in ufw" as_root ufw delete allow 80,443/tcp
  fi
  for item in "${ZERO_PROFILES[@]}"; do
    step "Taking uv's line out of ${item}" as_root sed -i '/^\. "\$HOME\/\.local\/bin\/env"$/d' "$item"
  done
  if [ "$ZERO_KNOWN_HOSTS" = 1 ]; then
    try_step "Taking GitHub out of root's known_hosts" \
      as_root sed -i -e '/^github\.com[ ,]/d' /root/.ssh/known_hosts
    if [ "$DRY_RUN" = 0 ] && ! as_root test -s /root/.ssh/known_hosts; then
      as_root rm -f /root/.ssh/known_hosts
    fi
  fi
  # Restore before deleting, since the originals are kept in the ledger's folder.
  for item in "${ZERO_RESTORE[@]}"; do
    if as_root test -d "$(dirname "$item")"; then
      step "Putting ${item} back" as_root cp -a "${LEDGER_DIR}/saved${item}" "$item"
    fi
  done
  if [ "$ZERO_CADDY" = keep ] && printf '%s\n' "${ZERO_RESTORE[@]}" | grep -qx /etc/caddy/Caddyfile; then
    try_step "Reloading Caddy with its own configuration" as_root systemctl reload caddy
  fi
  for item in "${ZERO_PATHS[@]}"; do
    [ "$item" = "$LEDGER_DIR" ] && continue  # last of all
    case "$item" in
      /|/etc|/usr|/var|/home|/root|/opt|/tmp|/bin|/sbin|/lib|/boot|/usr/local/bin|/var/lib|/var/log)
        warn "Not deleting ${item}: that is a system directory." ; continue ;;
    esac
    step "Deleting ${item}" as_root rm -rf "${item:?}"
  done
  for item in "${ZERO_EMPTY[@]}"; do
    if [ "$DRY_RUN" = 1 ]; then
      note "[dry run] Removing ${item} if it is left empty"
    elif as_root rmdir "$item" 2>/dev/null; then
      ok "Removed ${item}, which was left empty"
    fi
  done
  for item in "${ZERO_USERS[@]}"; do
    id "$item" >/dev/null 2>&1 && try_step "Removing the ${item} account" as_root userdel "$item"
  done
  for item in "${ZERO_GROUPS[@]}"; do
    getent group "$item" >/dev/null 2>&1 && try_step "Removing the ${item} group" as_root groupdel "$item"
  done
  # Folders that only held what was just deleted. rmdir takes a folder only when it is empty,
  # and root's .ssh is never on this list, whatever is left in it.
  if [ "$DRY_RUN" = 0 ]; then
    for item in /root/.config/uv /root/.config/fish/conf.d /root/.config/fish /root/.config \
                /root/.local/bin /root/.local/share /root/.local; do
      as_root rmdir "$item" 2>/dev/null || true
    done
  fi
  if [ "$ZERO_APT_UPDATE" = 1 ]; then
    try_step "Refreshing the package lists" as_root env DEBIAN_FRONTEND=noninteractive apt-get update -qq
  fi
  if [ "$DRY_RUN" = 0 ] && { [ "$ZERO_CRONTAB" = 1 ] || [ "$WHOLE_LEDGER" = 0 ]; }; then
    # Only ever when nothing but FamilyDB's line was in it.
    if have crontab && ! as_root crontab -u root -l 2>/dev/null | grep -q '[^[:space:]]'; then
      as_root crontab -r -u root >/dev/null 2>&1 || true
    fi
  fi
  if [ "$DRY_RUN" = 0 ] && have systemctl; then
    as_root systemctl reset-failed familydb >/dev/null 2>&1 || true
  fi
  step "Deleting the install's record of what it changed" as_root rm -rf "${LEDGER_DIR:?}"
  local log="$LOG_FILE"
  LOG_FILE=""
  [ "$DRY_RUN" = 0 ] && [ -n "$log" ] && as_root rm -f "$log"
  return 0
}

# --------------------------------------------------------------- safety ----
INSTALL_PRESENT=1
if [ -z "$TARGET" ]; then
  TARGET="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
  # Run from somewhere else with nothing said: the install is where the installer puts it.
  [ -f "${TARGET}/pyproject.toml" ] || TARGET=/opt/familydb
fi
if [ ! -d "$TARGET" ] && [ "$FROM_ZERO" = 1 ]; then
  # Already gone, perhaps by hand: what was around it can still be cleaned up.
  INSTALL_PRESENT=0
else
  [ -d "$TARGET" ] || die "no such directory: ${TARGET}"
  TARGET="$(cd -- "$TARGET" && pwd -P)"
  # Deleting the wrong directory is the one mistake this script must not be able to make.
  case "$TARGET" in
    /|/usr|/usr/*|/etc|/etc/*|/var|/var/*|/home|/root|/bin|/sbin|/lib|/lib64|/boot|/opt|/srv|/tmp)
      die "refusing to touch ${TARGET}: that is a system directory, not a FamilyDB install"
      ;;
  esac
  if [ ! -f "${TARGET}/pyproject.toml" ] || ! grep -q 'name = "familydb"' "${TARGET}/pyproject.toml"; then
    die "${TARGET} does not look like a FamilyDB install (no familydb pyproject.toml). Use --target."
  fi
fi

# What the installer set up around the install, read now, while the checkout still says where.
DEPLOY_KEY_FILE=""
KEYS_PAGE=""
WEB_DOMAIN_NOW=""
if [ "$FROM_ZERO" = 1 ]; then
  if [ "$INSTALL_PRESENT" = 1 ]; then
    DEPLOY_KEY_FILE="$(as_root git -C "$TARGET" config --get core.sshCommand 2>/dev/null \
      | sed -n 's/.*-i \([^ ]*\).*/\1/p' || true)"
    # Where the key was given, so the end can link straight to the page it is deleted from.
    KEYS_PAGE="$(as_root git -C "$TARGET" remote get-url origin 2>/dev/null \
      | sed -n 's#^\(git@github.com:\|https://github.com/\)\([^/]*/[^/.]*\).*#https://github.com/\2/settings/keys#p' || true)"
    WEB_DOMAIN_NOW="$(as_root grep -E '^WEB_DOMAIN=' "${TARGET}/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "'\"" || true)"
  fi
  take_inventory
fi

if [ "$INSTALL_PRESENT" = 1 ]; then
  head2 "Removing FamilyDB from ${TARGET}"
else
  head2 "There is no install at ${TARGET}; removing what is left around it"
fi
[ "$DRY_RUN" = 1 ] && note "Dry run: nothing will actually be removed."

if [ "$PURGE" = 1 ]; then
  plan_item "Stop the bot, and remove the systemd unit or the containers" \
    "so nothing starts it again at boot"
  if [ "$INSTALL_PRESENT" = 1 ]; then
    plan_item "Delete ${TARGET}/data" \
      "the database with every idea, plan and message, the Google token, and the web login key"
    plan_item "Delete ${TARGET}/.env" \
      "the API keys, the page password and the rest of the configuration"
    plan_item "Delete ${TARGET} itself, and any backups inside it" \
      "nothing of the install is left behind"
  fi
  [ "$REMOVE_USER" = 1 ] && id "$SERVICE_USER" >/dev/null 2>&1 \
    && plan_item "Remove the '${SERVICE_USER}' system user" "it exists only to run this"
  if [ "$BACKUP" = 1 ]; then
    plan_item "Take one last backup of the database first" \
      "so a change of mind is still possible; it is written outside ${TARGET} and left there"
  elif [ "$FROM_ZERO" = 1 ] && [ "$INSTALL_PRESENT" = 1 ]; then
    plan_item "Keep no backup of the database" \
      "nothing is left behind; to keep one, stop here and add --backup-to DIR"
  fi
  [ "$FROM_ZERO" = 1 ] && plan_from_zero
else
  plan_item "Stop the bot, and remove the systemd unit or the containers" \
    "so nothing starts it again at boot"
  plan_item "Delete the virtualenv and the caches inside ${TARGET}" \
    "these are rebuilt by an install, and nothing in them is yours"
  plan_untouched "${TARGET}/data — the database, the Google token and the login key"
  plan_untouched "${TARGET}/.env — your keys and configuration"
  plan_untouched "any backups, inside ${TARGET} or outside it"
fi
if [ "$FROM_ZERO" = 1 ]; then
  plan_untouched "git, curl and the other system packages, which the system itself uses"
  plan_untouched "Docker, the accounts people log in with, and how you log in to this server"
  [ "$ZERO_CADDY" = keep ] && plan_untouched "Caddy, which serves other sites here too; only FamilyDB's part of it goes"
else
  plan_untouched "Docker and uv, which other things may be using"
fi
plan_untouched "your Telegram bot, your Google project, and your API keys at each provider"
show_plan "What this will remove"

if [ "$PURGE" = 0 ] && [ "$DRY_RUN" = 0 ] && ! approve "Remove the service and the installed files?"; then
  say "Nothing was removed."
  exit 0
fi

# Removing the data asks twice: once here, having shown the whole list, with no as the answer if
# Enter is pressed; and once more, after the backup, by having the words typed out in full.
if [ "$PURGE" = 1 ] && [ "$FORCE" = 0 ] && [ "$DRY_RUN" = 0 ]; then
  [ -t 0 ] || die "not a terminal, so there is nobody to ask. Re-run with --force if you mean it."
  say ""
  if [ "$FROM_ZERO" = 1 ]; then
    warn "This removes FamilyDB, everything the family has told it, and everything the installer"
    warn "set up for it. The server goes back to how it was before FamilyDB."
  else
    warn "This removes FamilyDB and everything the family has told it."
  fi
  if ! confirm "Are you sure? (1 of 2)" no; then
    say "Nothing was removed."
    exit 0
  fi
fi

# ------------------------------------------------------------- the service ----
head2 "Stopping it"
UNIT=/etc/systemd/system/familydb.service
if have systemctl && [ -f "$UNIT" ]; then
  system_change "Stop familydb, remove its unit, and tell systemd to forget it" \
    "otherwise it would start again at the next boot"
  try_step "Stopping and disabling the service" as_root systemctl disable --now familydb
  step "Removing ${UNIT}" as_root rm -f "$UNIT"
  try_step "Reloading systemd" as_root systemctl daemon-reload
elif have systemctl && systemctl list-unit-files 2>/dev/null | grep -q '^familydb.service'; then
  try_step "Stopping and disabling the service" as_root systemctl disable --now familydb
else
  note "No systemd unit here."
fi

if have docker && [ -f "${TARGET}/docker-compose.yml" ]; then
  if docker compose --project-directory "$TARGET" ps >/dev/null 2>&1; then
    system_change "Stop and remove the containers" "so nothing restarts them"
    step "Stopping the containers" as_root docker compose --project-directory "$TARGET" down --remove-orphans
    if [ "$PURGE" = 1 ]; then
      try_step "Removing the familydb:local image" as_root docker image rm familydb:local
    fi
  fi
fi

# Anything still running from this checkout would rewrite files after they are removed.
if pgrep -af "${TARGET}/.venv/bin/familydb" >/dev/null 2>&1; then
  warn "Something is still running from ${TARGET}:"
  pgrep -af "${TARGET}/.venv/bin/familydb" >&2 || true
  [ "$FORCE" = 1 ] || die "stop it first, or re-run with --force"
fi

# ---------------------------------------------------------------- backup ----
DB="${TARGET}/data/familydb.sqlite3"
if [ "$PURGE" = 1 ] && [ "$BACKUP" = 1 ] && [ -f "$DB" ]; then
  head2 "Backing the database up first"
  BACKUP_DIR="${BACKUP_DIR:-/var/backups/familydb}"
  stamp="$(date +%Y%m%d%H%M%S)"
  dest="${BACKUP_DIR}/familydb-${stamp}.sqlite3"
  if [ "$DRY_RUN" = 1 ]; then
    note "would back the database up to ${dest}"
  else
    as_root mkdir -p "$BACKUP_DIR"
    # Never copy a main SQLite file alone: committed data may still be in its WAL.
    if [ -x "${TARGET}/.venv/bin/familydb" ] \
       && as_root env FAMILYDB_PATH="$DB" "${TARGET}/.venv/bin/familydb" db backup "$dest" >/dev/null 2>&1; then
      ok "Backup written with SQLite's backup API."
    else
      have python3 || die "Python 3 is needed for a safe backup; purge stopped"
      as_root python3 - "$DB" "$dest" <<'PY'
import sqlite3, sys
from contextlib import closing
from pathlib import Path
with closing(sqlite3.connect(Path(sys.argv[1]).as_uri() + '?mode=ro', uri=True)) as source:
    with closing(sqlite3.connect(sys.argv[2])) as target:
        source.backup(target)
        if target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup validation failed; purge stopped')
PY
      ok "Backup written with SQLite's backup API."
    fi
    as_root chmod 600 "$dest"
    say "  ${B}${dest}${OFF}"
    say "  That file is the only copy of everything the family said. Keep it somewhere safe."
  fi
fi

# ----------------------------------------------------------- confirmation ----
if [ "$PURGE" = 1 ] && [ "$FORCE" = 0 ] && [ "$DRY_RUN" = 0 ]; then
  head2 "This cannot be undone"
  say "About to remove:"
  if [ "$INSTALL_PRESENT" = 1 ]; then
    say "  ${TARGET}/data          the database, the Google token and the login key"
    say "  ${TARGET}/.env          the keys and the configuration"
    say "  ${TARGET}               the code itself"
  fi
  [ "$REMOVE_USER" = 1 ] && say "  the ${SERVICE_USER} system user"
  if [ "$FROM_ZERO" = 1 ]; then
    say "  and everything else in the list above, so the server is as it was before FamilyDB"
  fi
  say ""
  if [ ! -t 0 ]; then
    die "not a terminal, so there is nobody to ask. Re-run with --force if you mean it."
  fi
  printf 'To go ahead (2 of 2), type %sremove everything%s: ' "$B" "$OFF"
  read -r answer || answer=""
  [ "$answer" = "remove everything" ] || die "stopped. Nothing was removed."
fi

# ---------------------------------------------------------------- removal ----
head2 "Removing"

# Remove only the schedule installed by maintain.sh; leave unrelated root jobs alone.
if [ "$DRY_RUN" = 0 ] && have crontab; then
  current_cron="$(as_root crontab -u root -l 2>/dev/null || true)"
  if printf '%s\n' "$current_cron" | grep -q 'familydb-maintain-backup'; then
    printf '%s\n' "$current_cron" | sed '/familydb-maintain-backup/d' | as_root crontab -u root -
  fi
fi

if [ "$INSTALL_PRESENT" = 1 ]; then
# What an install puts there, and nothing else: a reinstall rebuilds every one of these.
# `.cache` is uv's, which lands here because the service user's home is the install itself.
for path in .venv .cache .ruff_cache .pytest_cache; do
  if [ -e "${TARGET}/${path}" ]; then
    step "Removing ${path}" as_root rm -rf "${TARGET:?}/${path}"
  fi
done
# Compiled Python left behind by an install. Quiet: there can be hundreds.
if [ "$DRY_RUN" = 0 ]; then
  as_root find "$TARGET" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  ok "Removed the compiled Python caches"
else
  note "[dry run] Removing the compiled Python caches"
fi

fi

if [ "$PURGE" = 0 ]; then
  head2 "Done"
  say "The service is gone and the installed files are removed."
  say "Kept: ${TARGET}/.env, ${TARGET}/data, and any backups beside them."
  say ""
  say "To put it back:  cd ${TARGET} && scripts/install.sh"
  say "To remove the rest as well:  scripts/uninstall.sh --purge"
  exit 0
fi

if [ "$INSTALL_PRESENT" = 1 ]; then
for path in data caddy .env; do
  if [ -e "${TARGET}/${path}" ]; then
    step "Removing ${path}" as_root rm -rf "${TARGET:?}/${path}"
  fi
done
# .env backups the installer wrote when it was re-run.
try_step "Removing old .env backups" as_root find "$TARGET" -maxdepth 1 -name '.env.*.bak' -delete

if [ -d "${TARGET}/backups" ]; then
  step "Removing backups/ from inside the install" as_root rm -rf "${TARGET:?}/backups"
  note "Any backup kept outside ${TARGET} is untouched."
fi

# The checkout itself, but only when this script is not inside the thing it is deleting.
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "$HERE" in
  "${TARGET}"/*|"$TARGET")
    warn "Not removing ${TARGET} itself: this script is inside it."
    note "Finish with:  cd / && sudo rm -rf ${TARGET}"
    ;;
  *)
    step "Removing ${TARGET}" as_root rm -rf "${TARGET:?}"
    ;;
esac
fi

if [ "$REMOVE_USER" = 1 ] && id "$SERVICE_USER" >/dev/null 2>&1; then
  if [ "$SERVICE_USER" = root ] || [ "$(id -u "$SERVICE_USER")" -lt 100 ]; then
    warn "Refusing to remove ${SERVICE_USER}: that is not a service account this created."
  else
    have crontab && as_root crontab -r -u "$SERVICE_USER" >/dev/null 2>&1 || true
    try_step "Removing the ${SERVICE_USER} user" as_root userdel "$SERVICE_USER"
    if [ "$LAST_STEP_STATUS" != 0 ]; then
      note "Something else may still be running as it, or own files it owns. Find them with:"
      note "  sudo find / -xdev -user ${SERVICE_USER} 2>/dev/null | head"
    fi
  fi
fi

if [ "$FROM_ZERO" = 1 ]; then
  remove_what_was_around_it
fi

head2 "Done"
if [ "$FROM_ZERO" = 1 ]; then
  say "FamilyDB is off this machine, and so is everything the installer set up for it."
  if [ "$BACKUP" = 1 ] && [ -n "${dest:-}" ]; then
    say "One thing is kept on purpose: the backup at ${B}${dest}${OFF}."
    say "Delete it when you are sure:  sudo rm -rf ${BACKUP_DIR:-/var/backups/familydb}"
  fi
  say ""
  say "Left for you, because the server cannot do it:"
  say "  · delete the old deploy key on GitHub${KEYS_PAGE:+: ${KEYS_PAGE}}"
  say "  · the Telegram bot, the Google project and the API keys still work, and a new install"
  say "    can use the same ones; revoke them only if you are done with FamilyDB"
  say ""
  say "To install again: docs/INSTALL.md, step 1. Paste the block there into this terminal."
  # The copy this ran from; the shell has already read what it needs from it.
  [ -n "${FAMILYDB_UNINSTALL_COPY:-}" ] && rm -rf "$FAMILYDB_UNINSTALL_COPY"
  exit 0
fi
say "FamilyDB is off this machine."
if [ "$BACKUP" = 1 ] && [ -n "${dest:-}" ]; then
  say "The backup is still at ${B}${dest}${OFF}. Delete it too when you are sure."
fi
say ""
say "Things this did not touch, because they are not ours to remove:"
say "  · Docker itself, and uv"
say "  · the Telegram bot (delete it with /deletebot in @BotFather)"
say "  · the Google Cloud project and its OAuth client"
say "  · the API keys at each provider, which are still live until you revoke them"
[ -n "${FAMILYDB_UNINSTALL_COPY:-}" ] && rm -rf "$FAMILYDB_UNINSTALL_COPY"
exit 0
