"""Turn pydantic input models into JSON schemas the API accepts under strict tool mode.

Strict mode wants `additionalProperties: false` on every object and rejects numeric and length
constraints, so those are stripped here and re-checked inside the handlers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

STRIP_KEYS = frozenset(
    {
        "title",
        "default",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)
_NAME_MAPS = ("properties", "$defs")


def _walk(node: Any, *, name_map: bool = False) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if not name_map and key in STRIP_KEYS:
                continue
            child_is_map = not name_map and key in _NAME_MAPS
            out[key] = _walk(value, name_map=child_is_map)
        if not name_map and (out.get("type") == "object" or "properties" in out):
            out.setdefault("properties", {})
            out["additionalProperties"] = False
        return out
    if isinstance(node, list):
        return [_walk(item) for item in node]
    return node


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    return _walk(model.model_json_schema())
