"""Keep what the bot writes readable by the bot alone.

The database holds every message the family has sent and any key typed into the settings page;
the Google token and the web session key are credentials. On a shared server none of that
should be readable by another account, and on a single-user one it costs nothing to be sure.

`private_by_default` sets the process umask, so every file the bot creates from then on (the
database and its journal, backups, the Google token) is owner-only. `tighten` fixes the files an
older version already created with the usual 0644.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from familydb.config import Settings

log = logging.getLogger(__name__)

OWNER_ONLY = 0o077
JOURNALS = ("-wal", "-shm", "-journal")


def private_by_default() -> None:
    os.umask(OWNER_ONLY)


def sensitive_files(settings: Settings) -> list[Path]:
    """The database with its journal files, the Google token, and the web session key."""
    database = Path(settings.familydb_path).expanduser()
    return [
        database,
        *(database.with_name(database.name + suffix) for suffix in JOURNALS),
        Path(settings.google_token_path).expanduser(),
        database.parent / "web_secret",
    ]


def tighten(settings: Settings) -> list[Path]:
    """Take group and other access off each sensitive file this process owns. Returns them."""
    # Windows uses ACLs, not POSIX owner/group bits. Keep the user's inherited ACLs;
    # chmod there cannot provide the owner-only guarantee this routine implements.
    if os.name != "posix":
        return []
    changed: list[Path] = []
    for path in sensitive_files(settings):
        try:
            info = path.stat()
        except OSError:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            continue
        if info.st_mode & OWNER_ONLY:
            os.chmod(path, stat.S_IMODE(info.st_mode) & ~OWNER_ONLY)
            changed.append(path)
    if changed:
        log.info("made owner-only: %s", ", ".join(str(path) for path in changed))
    return changed
