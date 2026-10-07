"""Taking back the last change: one tool with no input (familydb/undo.py says what it can undo)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from familydb import undo as taking_back
from familydb.tools.registry import ToolContext, tool


class UndoInput(BaseModel):
    pass


@tool(
    name="undo",
    description=(
        "Take back the sender's last change in this chat within a day (added, changed, moved, "
        "done or remembered). Returns what was undone, or why not."
    ),
    writes=True,
)
def undo(ctx: ToolContext, args: UndoInput) -> dict[str, Any]:
    return taking_back.take_back(ctx)
