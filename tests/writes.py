"""Which functions in the package write to the database, worked out from the source.

A function writes when it opens a transaction, runs a statement that changes a table, dispatches
a tool, or calls a function that does (followed through the package until nothing new is found).
`tests/test_web.py` holds the page to the few it may call; a store module's own name for a
writer, or a service's, is never listed by hand, so a new one is refused the day it is written.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from functools import cache
from pathlib import Path

import familydb

PACKAGE = Path(familydb.__file__).parent
CHANGES = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER)\b", re.I)
# Methods that change a table or run a tool, whatever they are called on.
METHODS = {"executescript", "executemany", "dispatch"}


def module_name(path: Path) -> str:
    rel = path.relative_to(PACKAGE).with_suffix("").as_posix().replace("/", ".")
    name = f"familydb.{rel}"
    return name.removesuffix(".__init__")


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Local name to the fully qualified module or `module.function` it stands for."""
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "familydb" or node.module.startswith("familydb."):
                for alias in node.names:
                    found[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("familydb"):
                    found[alias.asname or alias.name] = alias.name
    return found


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _dotted(node.value)
        return f"{inner}.{node.attr}" if inner else None
    return None


def calls_in(func: ast.AST, aliases: dict[str, str]) -> set[str]:
    """What a function calls, as `familydb.module.function` where the name resolves."""
    out = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted(node.func)
        if dotted is None:
            continue
        head, _, rest = dotted.partition(".")
        if head in aliases:
            out.add(f"{aliases[head]}.{rest}" if rest else aliases[head])
        elif dotted.startswith("familydb."):
            out.add(dotted)
    return out


def _writes_itself(func: ast.AST) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else getattr(node.func, "id", None)
        )
        if name == "transaction" or name in METHODS:
            return True
        if name == "execute" and node.args:
            first = node.args[0]
            text = first.value if isinstance(first, ast.Constant) else None
            if isinstance(first, ast.JoinedStr):
                text = "".join(v.value for v in first.values if isinstance(v, ast.Constant))
            if isinstance(text, str) and CHANGES.search(text):
                return True
    return False


@cache
def writers() -> dict[str, frozenset[str]]:
    """Module name to the functions in it that write, directly or through what they call."""
    functions: dict[str, ast.AST] = {}
    calls: dict[str, set[str]] = {}
    direct: set[str] = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text("utf-8"))
        module = module_name(path)
        aliases = _aliases(tree)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{module}.{node.name}"
                functions[name] = node
                calls[name] = calls_in(node, aliases)
                if _writes_itself(node):
                    direct.add(name)
            elif isinstance(node, ast.ClassDef):
                for inner in node.body:
                    if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        name = f"{module}.{node.name}.{inner.name}"
                        functions[name] = inner
                        calls[name] = calls_in(inner, aliases)
                        if _writes_itself(inner):
                            direct.add(name)
    writing = set(direct)
    while True:
        more = {name for name, called in calls.items() if name not in writing and called & writing}
        if not more:
            return _by_module(writing)
        writing |= more


def _by_module(names: set[str]) -> dict[str, frozenset[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for name in names:
        module, _, function = name.rpartition(".")
        if "." in function:  # never: a method is module.Class.method
            pass
        grouped[module].add(function)
    return {module: frozenset(found) for module, found in grouped.items()}


def writes_called(path: Path) -> set[str]:
    """Every call in the module to a function that writes, as `familydb.module.function`, and
    every statement or dispatch run on something ("dispatch()", "execute()")."""
    tree = ast.parse(path.read_text("utf-8"))
    aliases = _aliases(tree)
    known = writers()
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", None)
            )
            if name == "transaction" or name in METHODS or name == "execute":
                found.add(f"{name}()")
    for name in calls_in(tree, aliases):
        module, _, function = name.rpartition(".")
        if function in known.get(module, ()):
            found.add(name)
        # A method on a class: familydb.module.Class.method
        head, _, method = module.rpartition(".")
        if method and f"{method}.{function}" in known.get(head, ()):
            found.add(name)
    return found
