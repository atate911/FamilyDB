"""The modules stand in an order, and each imports only from its own level or below.

The order is the design (CLAUDE.md, Layout): the kernel in `base` under everything; the personas,
the service clients and the data under the domain; the domain modules (what the family's things
are and how they change) under the tools, the agent and the engine; the orchestration modules
(the pipeline, the App, what wires a message, a tap or a job to the rest) over those; the
channels, the jobs and the page on top. The domain and the orchestration both live directly in
the package, told apart by `ORCHESTRATION`.

Every import that crosses the order upward is named in `EXCEPTIONS` with its reason, so the list
can only shrink: one no longer needed fails the test until it is taken out.
"""

from __future__ import annotations

import ast
from pathlib import Path

import familydb

PACKAGE = Path(familydb.__file__).parent

# Bottom to top.
ORDER = [
    "base",
    "personas",
    "integrations",
    "store",
    "domain",
    "tools",
    "agent",
    "suggest",
    "orchestration",
    "channels",
    "jobs",
    "web",
]
LEVEL = {name: index for index, name in enumerate(ORDER)}
PACKAGES = {name for name in ORDER if name not in {"domain", "orchestration"}} | {"wiki"}

# The modules directly in the package that wire the rest together; every other one there is
# domain. Entry points (`cli`, `doctor`, `__main__`) may import anything.
ORCHESTRATION = {
    "__main__",
    "app",
    "buttons",
    "cli",
    "commands",
    "doctor",
    "judgement",
    "model_watch",
    "picks",
    "pipeline",
    "undo",
    "usage_watch",
}
TOP = {"cli.py", "doctor.py", "__main__.py"}

# (module, level it reaches up to): why. Each must still be needed.
EXCEPTIONS: dict[tuple[str, str], str] = {
    ("base/config.py", "personas"): "the persona settings are validated against the folders",
    ("base/config.py", "domain"): "`log_areas` is validated by logs.parse_areas",
    ("integrations/price_lists.py", "agent"): "each list is read by the company it names",
    ("alerts.py", "agent"): "a notice names the company by its label and the parts it refused",
    ("alerts.py", "orchestration"): "a refusal nobody can read is filed as a question (judgement)",
    ("whereabouts.py", "channels"): "channels.base holds the message dataclasses",
    (
        "wish_service.py",
        "orchestration",
    ): "the buttons under a wish message are declared in buttons.py",
    ("tools/registry.py", "agent"): "ToolDef, the provider-neutral declaration a tool becomes",
    ("tools/ideas.py", "agent"): "an idea is echoed as the line the prompt renders it as",
    ("tools/memory.py", "suggest"): "CostLevel, the type a memory's rule is read as",
    ("tools/suggest.py", "suggest"): "the tool that runs the engine",
    ("tools/undo.py", "orchestration"): "the tool that takes a change back (undo.take_back)",
    ("pipeline.py", "channels"): "channels.base holds the message dataclasses",
    ("commands.py", "channels"): "channels.base holds the message dataclasses",
}


def _level_of_module(module: str) -> str:
    """`familydb.x.y` to its level: the package, or domain/orchestration for a top-level module."""
    parts = module.split(".")
    if len(parts) >= 2 and parts[1] in PACKAGES:
        return parts[1]
    name = parts[1] if len(parts) >= 2 else ""
    return "orchestration" if name in ORCHESTRATION else "domain"


def _level_of_file(where: str) -> str:
    if "/" in where:
        return where.split("/")[0]
    return "orchestration" if where[:-3] in ORCHESTRATION else "domain"


def _imports(tree: ast.AST) -> set[str]:
    """Every familydb module imported at run time (a `TYPE_CHECKING` block is for the reader)."""
    for_types: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
        ):
            for_types |= {id(inner) for inner in ast.walk(node)}
    found = set()
    for node in ast.walk(tree):
        if id(node) in for_types:
            continue
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "familydb":
                found |= {f"familydb.{alias.name}" for alias in node.names}
            elif node.module.startswith("familydb."):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names if alias.name.startswith("familydb")}
    return found


def _modules() -> dict[str, ast.AST]:
    return {
        path.relative_to(PACKAGE).as_posix(): ast.parse(path.read_text("utf-8"))
        for path in sorted(PACKAGE.rglob("*.py"))
    }


def test_every_import_stays_at_its_level_or_below() -> None:
    crossings = []
    used = set()
    for where, tree in _modules().items():
        if where in TOP:
            continue
        own = _level_of_file(where)
        for module in _imports(tree):
            target = _level_of_module(module)
            if target == "wiki" or LEVEL[target] <= LEVEL[own]:
                continue
            if (where, target) in EXCEPTIONS:
                used.add((where, target))
                continue
            crossings.append(f"{where} imports {module} ({own} is below {target})")
    assert crossings == [], "\n".join(crossings)
    stale = sorted(set(EXCEPTIONS) - used)
    assert stale == [], f"no longer needed, take them out of EXCEPTIONS: {stale}"


def test_the_kernel_imports_only_itself() -> None:
    """`base` is what everything stands on: nothing in it reaches up, bar what is named."""
    for where, tree in _modules().items():
        if not where.startswith("base/"):
            continue
        outside = {
            module
            for module in _imports(tree)
            if not module.startswith("familydb.base")
            and (where, _level_of_module(module)) not in EXCEPTIONS
        }
        assert outside == set(), f"{where} imports {sorted(outside)}"


def test_the_orchestration_list_names_only_modules_that_exist() -> None:
    names = {path.stem for path in PACKAGE.glob("*.py")}
    assert names >= ORCHESTRATION, ORCHESTRATION - names
