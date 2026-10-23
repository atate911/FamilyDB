#!/usr/bin/env bash
# Upgrade this install: the one command to remember, from the base directory.
#
#   sudo ./upgrade.sh              # or: sudo /opt/familydb/upgrade.sh
#   sudo ./upgrade.sh --dry-run    # say what would change, change nothing
#
# Everything is scripts/maintain.sh upgrade (RUNBOOK section 8): it fetches, says what this
# upgrade changes, asks (Enter is yes), stops the bot, takes a backup, prints the way back,
# moves to the newest commit on the default branch, reinstalls the dependencies, migrates and
# starts it again. This file only finds that script beside itself and runs it as root, so the
# options are maintain.sh's (--dry-run, --yes, --target DIR) and pass straight through. The
# process is replaced (exec), so the new code may replace this file mid-upgrade without harm.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ "${EUID:-$(id -u)}" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  # Upgrades run as root (the service, the backup, the packages). A token for a private
  # repository is carried along, as docs/INSTALL.md says (used for the fetch only).
  exec sudo --preserve-env=GITHUB_TOKEN -- "$HERE/scripts/maintain.sh" upgrade "$@"
fi
exec "$HERE/scripts/maintain.sh" upgrade "$@"
