"""What code checks of a choice before it leads a suggestion (tools/suggest.py `give_picks`)."""

from __future__ import annotations

from datetime import date

import pytest

from familydb.suggest.dossier import Option
from familydb.tools import ToolContext

OPTIONS = {
    "idea:1": Option("idea:1", "idea", "Ramen at Menya", idea_id=1, done_before=True),
    "idea:2": Option("idea:2", "idea", "Lantern walk", idea_id=2, days=("2026-09-26",)),
    "find:1": Option("find:1", "find", "Harvest fair", url="https://example.org/fair"),
}
CITES = frozenset({"m1", "o3", "idea:1", "idea:2", "find:1"})


def _ctx(conn, settings, clock) -> ToolContext:
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=None)
    ctx.scratch.update(
        {"options": OPTIONS, "cites": CITES, "window": (date(2026, 9, 26), date(2026, 9, 27))}
    )
    return ctx


def _pick(ref="idea:1", slot="favorite", reason="They loved it last time.", **more):
    return {"ref": ref, "slot": slot, "reason": reason, **more}


def _give(registry, ctx, *picks, framing=None):
    return registry.dispatch("give_picks", {"picks": list(picks), "framing": framing}, ctx)


def test_a_sound_choice_is_kept(registry, conn, settings, clock) -> None:
    ctx = _ctx(conn, settings, clock)
    result = _give(
        registry,
        ctx,
        _pick(cites=["o3"]),
        _pick("idea:2", "new", "Never tried, and dry on Saturday.", day="2026-09-26"),
        _pick("find:1", "wildcard", "Only this weekend."),
        framing="A slow weekend.",
    )
    assert not result.is_error
    chosen = ctx.scratch["chosen"]
    assert [p["ref"] for p in chosen["picks"]] == ["idea:1", "idea:2", "find:1"]
    assert chosen["picks"][1]["day"] == "2026-09-26" and chosen["framing"] == "A slow weekend."


@pytest.mark.parametrize(
    "picks, said",
    [
        ([_pick("idea:9")], "not one of the options"),
        ([_pick(), _pick()], "picked twice"),
        ([_pick("idea:2", "favorite")], "not a favorite"),
        ([_pick("idea:1", "new")], "not new"),
        ([_pick("idea:2", "new", day="2026-09-27")], "fits 2026-09-26"),
        ([_pick(day="2026-10-03")], "outside the days asked about"),
        ([_pick(day="Saturday")], "YYYY-MM-DD"),
        ([_pick(reason="x" * 201)], "1 to 200 characters"),
        ([_pick(cites=["m99"])], "not in the dossier"),
        ([_pick(f"idea:{n}") for n in range(6)], "1 to 5 picks"),
        ([], "1 to 5 picks"),
    ],
)
def test_a_pick_code_can_tell_is_wrong_is_refused(registry, conn, settings, clock, picks, said):
    ctx = _ctx(conn, settings, clock)
    result = _give(registry, ctx, *picks)
    assert result.is_error and said in result.content
    assert "chosen" not in ctx.scratch
