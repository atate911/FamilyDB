import json

import pytest
from pydantic import BaseModel, Field

from familydb.tools import ToolRegistry
from familydb.tools.schema import STRIP_KEYS, strict_schema


def _objects(node):
    """Yield every schema object node (skipping the name maps)."""
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            yield node
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for child in value.values():
                    yield from _objects(child)
            else:
                yield from _objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from _objects(item)


def _keys(node, *, in_map=False):
    if isinstance(node, dict):
        for key, value in node.items():
            if not in_map:
                yield key
            yield from _keys(value, in_map=(key in ("properties", "$defs")) and not in_map)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


class Nested(BaseModel):
    day: str
    open: str = Field(description="HH:MM")


class Sample(BaseModel):
    title: str = Field(description="A property literally named title must survive.")
    default: int = 3
    count: int = Field(default=1, ge=0, le=10)
    tags: list[str] = Field(default_factory=list, max_length=5)
    hours: list[Nested] = Field(default_factory=list)
    note: str | None = None


def test_strict_schema_strips_constraints_and_closes_objects() -> None:
    schema = strict_schema(Sample)
    assert set(schema["properties"]) == {"title", "default", "count", "tags", "hours", "note"}
    assert schema["required"] == ["title"]
    assert schema["properties"]["title"]["description"].startswith("A property")
    assert all(obj.get("additionalProperties") is False for obj in _objects(schema))
    assert not (set(_keys(schema)) & STRIP_KEYS)
    assert "anyOf" in schema["properties"]["note"]


def test_every_registered_tool_has_a_usable_schema(registry: ToolRegistry) -> None:
    tools = registry.tool_defs()
    names = [t.name for t in tools]
    assert names == sorted(names)
    assert len(names) == len(set(names))
    assert "web_search" not in names  # hosted tools belong to the provider, not the registry
    for tool in tools:
        assert tool.description
        assert all(obj.get("additionalProperties") is False for obj in _objects(tool.schema))
        assert not (set(_keys(tool.schema)) & STRIP_KEYS)
        json.dumps(tool.schema)  # serialisable


def test_the_registry_knows_nothing_about_hosted_tools(registry: ToolRegistry) -> None:
    """Whether a surface may search is the provider's decision, from the request it is handed."""
    from familydb.agent.providers.base import ToolDef

    assert all(isinstance(tool, ToolDef) for tool in registry.tool_defs())
    hand_back = {"save_place", "skip_place", "report_finds"}
    assert hand_back.isdisjoint(t.name for t in registry.tool_defs())
    assert hand_back <= {t.name for t in registry.tool_defs(registry.names())}


def test_now_tool_takes_no_input(registry: ToolRegistry) -> None:
    schema = registry.get("now").api_definition()["input_schema"]
    assert schema == {"type": "object", "properties": {}, "additionalProperties": False}


def test_tool_defs_take_a_subset_and_refuse_an_unknown_name(registry: ToolRegistry) -> None:
    subset = registry.tool_defs(["now", "add_idea"])
    assert [t.name for t in subset] == ["add_idea", "now"]
    with pytest.raises(ValueError, match="teleport"):
        registry.tool_defs(["teleport"])
