import json

from pydantic import BaseModel, Field

from familydb.config import Settings
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


def test_every_registered_tool_has_a_strict_schema(
    registry: ToolRegistry, settings: Settings
) -> None:
    tools = registry.api_tools(settings)
    names = [t["name"] for t in tools]
    assert names == sorted(names)
    assert len(names) == len(set(names))
    assert "web_search" not in names  # off by default
    for tool in tools:
        assert tool["strict"] is True
        assert tool["description"]
        assert all(
            obj.get("additionalProperties") is False for obj in _objects(tool["input_schema"])
        )
        assert not (set(_keys(tool["input_schema"])) & STRIP_KEYS)
        json.dumps(tool)  # serialisable


def test_server_tools_are_appended_when_enabled(settings: Settings, registry: ToolRegistry) -> None:
    enabled = settings.model_copy(update={"web_tools_enabled": True})
    tools = registry.api_tools(enabled)
    assert [t["name"] for t in tools[-2:]] == ["web_search", "web_fetch"]
    assert tools[-2]["type"] == "web_search_20260209"
    assert tools[:-2] == registry.api_tools(settings)


def test_now_tool_takes_no_input(registry: ToolRegistry) -> None:
    schema = registry.get("now").api_definition()["input_schema"]
    assert schema == {"type": "object", "properties": {}, "additionalProperties": False}


def test_api_tools_subset_and_forced_web(registry: ToolRegistry, settings: Settings) -> None:
    subset = registry.api_tools(settings, names=["now", "add_idea"], force_web=True, max_uses=2)
    assert [t["name"] for t in subset] == ["add_idea", "now", "web_search", "web_fetch"]
    assert subset[2]["max_uses"] == 2
    located = registry.api_tools(
        settings,
        names=["now"],
        force_web=True,
        user_location={"type": "approximate", "city": "Portland"},
    )
    assert located[1]["user_location"] == {"type": "approximate", "city": "Portland"}
    assert "user_location" not in registry.api_tools(settings, names=["now"], force_web=True)[1]
    import pytest

    with pytest.raises(ValueError):
        registry.api_tools(settings, names=["teleport"])
