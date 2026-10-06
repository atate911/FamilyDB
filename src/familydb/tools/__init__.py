"""Tools the model can call. Importing the modules registers them."""

from __future__ import annotations

from familydb.tools.registry import REGISTRY, ToolContext, ToolRegistry, ToolResult


def build_registry() -> ToolRegistry:
    from familydb.tools import (  # noqa: F401
        gcal,
        ideas,
        judgement,
        lists,
        memory,
        now,
        outcomes,
        places,
        suggest,
        tasks,
        undo,
        weather,
        wishes,
    )

    return REGISTRY


__all__ = ["REGISTRY", "ToolContext", "ToolRegistry", "ToolResult", "build_registry"]
