"""The family's data to take away (familydb/export.py): plans as a calendar file, ideas and things
to do as spreadsheets, everything as JSON for an admin, never a secret or a way in."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from familydb import export, presents, task_service
from familydb.store import db, ideas, plans
from tests.conftest import NOW_ISO
from tests.test_web_logins import KIDS, SAMS, _as, _start, _tokens, alex, app, sam  # noqa: F401


def _plan(conn, title, start, end=None, *, all_day=False, status="confirmed", **fields):
    with db.transaction(conn):
        made = plans.insert(
            conn, title=title, start=start, end=end, all_day=all_day, now=NOW_ISO, **fields
        )
        if status != "confirmed":
            conn.execute("UPDATE plans SET status = ? WHERE id = ?", (status, made.id))
    return made


def test_the_plans_open_in_any_calendar(settings, clock, conn) -> None:
    beck = _plan(conn, "Beck; at the Moda, with friends", "2026-11-18T19:30", "2026-11-18T22:00")
    _plan(conn, "Camping", "2026-10-03", "2026-10-04", all_day=True, location="Cape Disappointment")
    _plan(conn, "Called off", "2026-10-10", all_day=True, status="cancelled")
    text = export.plans_ics(conn, settings, clock.now())
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n") and text.endswith(
        "END:VCALENDAR\r\n"
    )
    assert f"UID:plan-{beck.id}@familydb" in text
    # In UTC, whatever the family's clock does in November.
    start = datetime(2026, 11, 18, 19, 30, tzinfo=settings.tzinfo).astimezone(UTC)
    end = start + timedelta(hours=2, minutes=30)
    assert f"DTSTART:{start:%Y%m%dT%H%M%SZ}\r\nDTEND:{end:%Y%m%dT%H%M%SZ}" in text
    assert "SUMMARY:Beck\\; at the Moda\\, with friends" in text
    # All day, the last day inclusive here and exclusive in the file.
    assert "DTSTART;VALUE=DATE:20261003\r\nDTEND;VALUE=DATE:20261005" in text
    assert "LOCATION:Cape Disappointment" in text and "Called off" not in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))


def test_the_spreadsheets_leave_out_what_is_kept_from_whoever_asks(conn, family) -> None:
    with db.transaction(conn):
        ramen = ideas.insert(conn, title="Ramen place", kind="restaurant", now=NOW_ISO)
        lego = ideas.insert(
            conn, title="Lego castle", kind="gift", participants=["the girls"], now=NOW_ISO
        )
        ideas.insert(conn, title="Old idea", kind="outing", status="dropped", now=NOW_ISO)
        pass
    task_service.create(
        conn,
        {"title": "Bins out", "owner_id": family["sam"].id},
        reminder=None,
        operation_key="bins",
        channel="web",
        chat_id="web",
        now=NOW_ISO,
    )
    kept = presents.kept_ids(conn, family["girls"])
    rows = list(csv.DictReader(io.StringIO(export.ideas_csv(conn, kept))))
    assert [row["title"] for row in rows] == ["Ramen place"] and lego.id in kept
    rows = list(csv.DictReader(io.StringIO(export.ideas_csv(conn))))
    assert [row["id"] for row in rows] == [str(ramen.id), str(lego.id)]
    todo = list(csv.DictReader(io.StringIO(export.tasks_csv(conn))))
    assert [(row["title"], row["for"], row["status"]) for row in todo] == [
        ("Bins out", "Sam", "open")
    ]


def test_everything_is_the_familys_records_and_never_a_way_in(settings, clock, conn, family):
    from familydb import family as rules

    rules.choose_password(conn, family["sam"].id, SAMS, now=NOW_ISO)
    dump = json.loads(export.everything_json(conn, clock.now()))
    assert set(dump) >= {"members", "ideas", "plans", "tasks", "memories", "messages", "lists"}
    assert set(dump["members"][0]) == set(export.TABLES["members"])
    text = json.dumps(dump)
    assert "1001" not in text  # a Telegram id is how she knows somebody: not taken away
    assert "scrypt$" not in text and "member_logins" not in dump and "push_key" not in dump


def test_familydb_export_writes_the_four(settings, clock, conn, tmp_path: Path, monkeypatch):
    from typer.testing import CliRunner

    from familydb.cli import app as cli

    monkeypatch.setenv("FAMILYDB_PATH", str(settings.familydb_path))
    answered = CliRunner().invoke(cli, ["export", str(tmp_path / "out")])
    assert answered.exit_code == 0, answered.output
    written = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert written == ["everything.json", "ideas.csv", "plans.ics", "tasks.csv"]


def test_a_grown_up_downloads_and_only_an_admin_takes_everything(
    app,  # noqa: F811
    sam,  # noqa: F811
    alex,  # noqa: F811
    family,
) -> None:
    ics = alex.get("/export/plans.ics")
    assert ics.status_code == 200 and ics.mimetype == "text/calendar"
    assert ics.headers["Content-Disposition"] == 'attachment; filename="familydb-plans.ics"'
    assert alex.get("/export/ideas.csv").mimetype == "text/csv"
    assert 'href="/export/plans.ics"' in alex.get("/plans/month").text
    kid = _as(app, "the girls", _start(sam, family["girls"].id))
    kid.post("/you", data={**_tokens(kid, "/you"), "new": KIDS, "again": KIDS})
    assert kid.get("/export/tasks.csv").status_code == 403
    assert 'href="/export/plans.ics"' not in kid.get("/plans").text
    # Everything: an admin's, with the password typed again.
    form = _tokens(sam, "/settings/security")
    wrong = sam.post("/settings/export", data={**form, "password": "not it"})
    assert wrong.status_code == 401
    taken = sam.post("/settings/export", data={**form, "password": SAMS})
    assert taken.status_code == 200 and taken.mimetype == "application/json"
    assert json.loads(taken.text)["members"][0]["display_name"] == "Sam"
    assert alex.post("/settings/export", data={**form, "password": "x"}).status_code == 403


@pytest.mark.parametrize("value", ["a\nb", "x;y", "c,d", "back\\slash"])
def test_calendar_text_is_escaped(value: str) -> None:
    assert "\n" not in export._text(value)
    assert export._text(value).count("\\") >= 1
