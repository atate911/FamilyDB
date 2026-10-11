"""What is said of a tool is said once per place, and every writing tool is said of: the line a
budget interruption reports it with (spending.DONE), the words the page uses for what a turn did
(views.DID_WORDS). A new writing tool without them fails here, not silently in a reply."""

from __future__ import annotations

import json

from familydb.agent import spending
from familydb.store import db
from familydb.tools import ToolContext, build_registry
from familydb.tools.registry import UNDO_VERSION
from familydb.web import views


def test_every_writing_tool_has_its_done_line_and_its_did_words() -> None:
    registry = build_registry()
    writing = {spec.name for spec in registry.specs() if spec.writes}
    from_chat = {spec.name for spec in registry.specs() if spec.writes and not spec.worker_only}
    assert set(spending.DONE) == writing
    assert set(views.DID_WORDS) == from_chat
    assert all(label and key for label, key in spending.DONE.values())


def test_an_inverse_kept_by_another_version_is_left_alone(settings, clock, conn, family) -> None:
    registry = build_registry()
    ctx = ToolContext(
        conn=conn, settings=settings, clock=clock, member=family["sam"], source="page"
    )
    made = json.loads(registry.dispatch("add_task", {"title": "Call the plumber"}, ctx).content)
    row = conn.execute("SELECT id, undo FROM tool_calls ORDER BY id DESC LIMIT 1").fetchone()
    kept = json.loads(row["undo"])
    assert kept["v"] == UNDO_VERSION
    with db.transaction(conn):
        conn.execute(
            "UPDATE tool_calls SET undo = ? WHERE id = ?",
            (json.dumps({**kept, "v": UNDO_VERSION + 1}), row["id"]),
        )
    ctx.undo_target = row["id"]
    answer = registry.dispatch("undo", {}, ctx)  # a tool's refusal is a result, not a raise
    assert answer.is_error and "another version" in answer.content
    assert (
        conn.execute("SELECT status FROM tasks WHERE id = ?", (made["task"]["id"],)).fetchone()[0]
        != "cancelled"
    )
