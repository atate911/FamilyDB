"""Keep what the bot writes readable by the bot alone: the database (every message, any key typed on
the settings page) and the Google and session keys.

`private_by_default` sets the process umask so every file the bot creates is owner-only;
`tighten` fixes existing ones an older version left 0644.
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
    database = Path(settings.familydb_path).expanduser()
    return [
        database,
        *(database.with_name(database.name + suffix) for suffix in JOURNALS),
        Path(settings.google_key_path).expanduser(),
        database.parent / "web_secret",
    ]


def tighten(settings: Settings) -> list[Path]:
    # Windows uses ACLs, not POSIX bits: keep the inherited ACLs, chmod cannot give owner-only
    # there.
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
