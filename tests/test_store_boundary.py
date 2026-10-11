"""One repository per table (CLAUDE.md): a statement is run only in `familydb/store/`.

Anything else asks a store module, so a table's shape is known in one place and a change to it
is one change. The database file's own checks (a write probe, `quick_check`) are the store's
`db.py` too.
"""

from __future__ import annotations

import ast
from pathlib import Path

import familydb

PACKAGE = Path(familydb.__file__).parent
RUNS = {"execute", "executemany", "executescript"}


def _statement_calls(tree: ast.AST) -> list[int]:
    """Lines where a statement is run: `.execute(...)` and kin with a string as the statement
    (a Google request's `.execute()` takes nothing)."""
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in RUNS or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.JoinedStr) or (
            isinstance(first, ast.Constant) and isinstance(first.value, str)
        ):
            found.append(node.lineno)
    return found


def test_a_statement_is_run_only_in_the_store() -> None:
    outside = []
    for path in sorted(PACKAGE.rglob("*.py")):
        where = path.relative_to(PACKAGE).as_posix()
        if where.startswith("store/"):
            continue
        tree = ast.parse(path.read_text("utf-8"))
        outside += [f"{where}:{line}" for line in _statement_calls(tree)]
    assert outside == [], outside
