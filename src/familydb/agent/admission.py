"""Serialize paid calls and their accounting for one database, across threads and processes.

No SQLite transaction is held over the network. The OS releases the file lock if a process
dies. Release before dispatching tools, which may themselves ask a worker model.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


@contextmanager
def locked(conn: sqlite3.Connection) -> Iterator[None]:
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    key = os.path.normcase(os.path.realpath(path)) if path else ":memory:"
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if not path:
            yield
            return
        with open(key + ".spending-lock", "a+b") as handle:
            if os.name == "nt":
                import msvcrt

                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                while True:
                    handle.seek(0)
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError as exc:
                        if exc.errno not in (13, 36):
                            raise
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle, fcntl.LOCK_UN)
