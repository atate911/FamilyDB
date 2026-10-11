"""Troubleshooting: the models' words kept for an admin, the problem log, the log-level controls."""

from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime, timedelta

import pytest

from familydb import logs
from familydb.agent.loop import run_turn
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers import build
from familydb.agent.render import render_user_turn
from familydb.app import App
from familydb.base.errors import AgentError
from familydb.channels.base import IncomingMessage
from familydb.jobs.tidy import run_tidy
from familydb.pipeline import handle_incoming
from familydb.store import ai_texts, db, members, problems
from tests import fakes
from tests import test_web_logins as logins

app = logins.app
sam = logins.sam
alex = logins.alex


def _turn(api, settings, registry, ctx, text="we should try the ramen place"):
    return run_turn(
        provider=build("anthropic", settings, api=api),
        settings=settings,
        registry=registry,
        ctx=ctx,
        system=build_system_blocks(ctx.conn, settings),
        messages=build_messages([], render_user_turn("Sam", text, ctx.clock)),
        kind="chat",
    )


# -- what the models were sent and said


def test_a_call_is_kept_in_words_with_the_prompt_stored_once(settings, registry, ctx) -> None:
    for _ in range(2):
        api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi Sam!")]))
        _turn(api, settings, registry, ctx)
    rows = ai_texts.recent(ctx.conn)
    assert [row["outcome"] for row in rows] == ["answered", "answered"]
    one = ai_texts.get(ctx.conn, rows[0]["id"])
    assert "we should try the ramen place" in one["request"]
    assert one["reply"].startswith("Hi Sam!") and "[ended: end]" in one["reply"]
    assert one["system"] and one["tools"] and "add_idea" in one["tools"]
    # The same instructions and tools are one blob, not one per call.
    assert ctx.conn.execute("SELECT count(*) FROM ai_blobs").fetchone()[0] == 2
    assert ai_texts.for_call(ctx.conn, one["call_id"]) == one["id"]


def test_a_tool_step_is_in_the_next_calls_words(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [fakes.tool_use("tu_1", "add_idea", {"title": "Ramen place", "kind": "restaurant"})],
            stop_reason="tool_use",
        ),
        fakes.message([fakes.text("Saved #1.")]),
    )
    _turn(api, settings, registry, ctx)
    first, second = reversed(ai_texts.recent(ctx.conn))
    assert "[asks for add_idea]" in ai_texts.get(ctx.conn, first["id"])["reply"]
    request = ai_texts.get(ctx.conn, second["id"])["request"]
    assert "[asks for add_idea]" in request and "[result of add_idea]" in request


def test_a_failed_call_keeps_what_it_was_sent_and_why(settings, registry, ctx) -> None:
    api = fakes.FakeMessagesAPI(fakes.rate_limit_error())
    with pytest.raises(AgentError):
        _turn(api, settings, registry, ctx)
    (row,) = ai_texts.recent(ctx.conn, failed_only=True)
    one = ai_texts.get(ctx.conn, row["id"])
    assert one["outcome"] == "failed" and one["call_id"] is None
    assert "ramen" in one["request"] and "worth trying again: True" in one["reply"]
    (logged,) = problems.recent(ctx.conn, source="model")
    assert logged["level"] == "ERROR" and "did not answer" in logged["message"]


def test_nothing_is_kept_when_the_family_keeps_no_words(settings, registry, ctx) -> None:
    quiet = settings.model_copy(update={"keep_ai_text_days": 0})
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi!")]), fakes.rate_limit_error())
    _turn(api, quiet, registry, ctx)
    with pytest.raises(AgentError):
        _turn(api, quiet, registry, ctx)
    assert ai_texts.sizes(ctx.conn)["calls"] == 0
    # The failure is still in the problem log, which holds no prompt.
    assert len(problems.recent(ctx.conn, source="model")) == 1


def test_the_tidy_job_lets_go_of_old_words_and_their_blobs(settings, clock, conn) -> None:
    old = clock.now() - timedelta(days=20)
    with db.transaction(conn):
        ai_texts.record(
            conn, call_id=None, message_id=None, turn=None, iteration=1, kind="chat", about=None,
            provider="anthropic", model="m", error=None, system="old prompt", tools="old tools",
            request="r", reply="a", now=old,
        )  # fmt: skip
        ai_texts.record(
            conn, call_id=None, message_id=None, turn=None, iteration=1, kind="chat", about=None,
            provider="anthropic", model="m", error=None, system="new prompt", tools="t",
            request="r", reply="a", now=clock.now(),
        )  # fmt: skip
    run_tidy(App(settings, clock))  # fourteen days is the default
    assert [row["id"] for row in ai_texts.recent(conn)] == [2]
    assert {row["text"] for row in conn.execute("SELECT text FROM ai_blobs")} == {"new prompt", "t"}
    run_tidy(App(settings.model_copy(update={"keep_ai_text_days": 0}), clock))
    assert ai_texts.sizes(conn)["calls"] == 0


def test_taking_somebody_off_for_good_takes_the_words_of_their_messages(
    settings, registry, ctx, family
) -> None:
    api = fakes.FakeMessagesAPI(fakes.message([fakes.text("Hi!")]))
    reply = handle_incoming(
        App(settings, ctx.clock),
        IncomingMessage("telegram", "9", "chat-1", "1001", "hello there"),
        api=api,
        conn=ctx.conn,
    )
    assert reply is not None and ai_texts.sizes(ctx.conn)["calls"] == 1
    with db.transaction(ctx.conn):
        members.erase(ctx.conn, family["sam"].id)
    assert ai_texts.sizes(ctx.conn)["calls"] == 0


# -- the problem log


def test_the_same_trouble_is_one_row_with_a_count(conn) -> None:
    now = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    for minute in range(3):
        problems.record(
            conn,
            level="ERROR",
            source="familydb.jobs.reminders",
            message=f"reminder {minute} failed",
            detail="Traceback ...\nKeyError: 'x'",
            now=now + timedelta(minutes=minute),
        )
    (row,) = problems.recent(conn)
    assert row["count"] == 3 and row["last_at"] > row["first_at"]
    problems.record(conn, level="ERROR", source="other", message="different", now=now)
    assert len(problems.recent(conn)) == 2
    # A day later it is news again.
    problems.record(
        conn, level="ERROR", source="familydb.jobs.reminders", message="reminder 9 failed",
        detail="Traceback ...\nKeyError: 'x'", now=now + timedelta(days=2),
    )  # fmt: skip
    assert len(problems.recent(conn)) == 3


def test_the_problem_log_is_trimmed_by_age_and_count(conn) -> None:
    now = datetime(2026, 10, 8, tzinfo=UTC)
    problems.record(conn, level="ERROR", source="a", message="old", now=now - timedelta(days=40))
    problems.record(conn, level="ERROR", source="b", message="new", now=now)
    assert problems.trim(conn, now=now) == 1
    assert [row["message"] for row in problems.recent(conn)] == ["new"]


def test_a_logged_line_reaches_the_database_without_its_secrets(settings, conn) -> None:
    handler = logs.ProblemLog(settings.familydb_path, logging.WARNING)
    logger = logging.getLogger("familydb.test_problem_log")
    logger.addHandler(handler)
    try:
        logger.info("too quiet to keep")
        try:
            raise RuntimeError("https://api.telegram.org/bot123456:ABCDEFGHIJKLMNOPQRSTUVWX/send")
        except RuntimeError:
            logger.exception("sending failed, key=sk-abcdefghijklmnopqrstuvwxyz")
    finally:
        handler.flush_and_stop()
        logger.removeHandler(handler)
    (row,) = problems.recent(conn)
    assert row["level"] == "ERROR" and row["source"] == "familydb.test_problem_log"
    assert "sk-abcdef" not in row["message"] and "ABCDEFGHIJKLMNOP" not in row["detail"]
    assert "RuntimeError" in row["detail"] and "bot<token>" in row["detail"]


def test_logging_never_waits_for_the_database(settings) -> None:
    handler = logs.ProblemLog(settings.familydb_path.parent / "nowhere" / "x.sqlite3")
    logger = logging.getLogger("familydb.test_nowhere")
    logger.addHandler(handler)
    try:
        started = time.monotonic()
        for number in range(2000):  # more than the queue holds: the rest are dropped
            logger.warning("line %d", number)
        assert time.monotonic() - started < 2
    finally:
        logger.removeHandler(handler)
        handler.flush_and_stop(0.2)


# -- the log-level controls


def test_areas_are_lines_of_a_name_and_a_level() -> None:
    assert logs.parse_areas("models=debug\n\n telegram = WARNING \nfamilydb.x.y=INFO") == {
        "models": "DEBUG",
        "telegram": "WARNING",
        "familydb.x.y": "INFO",
    }
    for bad in ("models", "models=LOUD", "the moon=DEBUG"):
        with pytest.raises(ValueError):
            logs.parse_areas(bad)


def test_an_area_turns_up_its_loggers_and_back_down_when_removed() -> None:
    models = logging.getLogger("familydb.agent")
    before = models.level
    try:
        logs.apply_areas("models=DEBUG")
        assert models.level == logging.DEBUG
        logs.apply_areas("")
        assert models.level == logging.NOTSET
    finally:
        models.setLevel(before)
        logs.apply_areas("")


def test_what_a_line_is_called_is_the_familys_word_for_its_part() -> None:
    assert logs.area_of("familydb.agent.loop") == "Asking the models"
    assert logs.area_of("somebody.else") == "somebody.else"


# -- the pages


def test_an_admin_reads_the_log_and_the_words_and_nobody_else_does(app, sam, alex, conn) -> None:
    api = fakes.FakeMessagesAPI(
        fakes.message([fakes.text("Saved <b>it</b>.")]), fakes.rate_limit_error()
    )
    handle_incoming(
        app,
        IncomingMessage("telegram", "9", "chat-1", "1001", "we should try the ramen place"),
        api=api,
        conn=conn,
    )
    with db.transaction(conn):
        problems.record(
            conn,
            level="ERROR",
            source="familydb.jobs.reminders",
            message="Job crashed <i>hard</i>",
            detail="Traceback (most recent call last):\nKeyError: 'x'",
            now=app.clock.now(),
        )

    page = sam.get("/settings/troubleshooting")
    assert page.status_code == 200
    assert "Job crashed &lt;i&gt;hard&lt;/i&gt;" in page.text and "<i>hard</i>" not in page.text
    assert "KeyError" in page.text and "Background jobs" in page.text
    assert "Logging" in sam.get("/settings").text

    listing = sam.get("/settings/troubleshooting/ai")
    assert listing.status_code == 200 and "answering the family" in listing.text
    first = re.search(r'href="(/settings/troubleshooting/ai/\d+)"', listing.text).group(1)
    words = sam.get(first).text
    assert "we should try the ramen place" in words
    assert "Saved &lt;b&gt;it&lt;/b&gt;." in words and "<b>it</b>" not in words
    assert sam.get("/settings/troubleshooting/ai?show=failed").status_code == 200
    assert sam.get("/settings/troubleshooting/ai/9999").status_code == 404

    # The message's own history links to its words.
    history = sam.get(
        re.search(r'href="(/status/activity/m\d+)"', sam.get("/status").text).group(1)
    )
    assert "/settings/troubleshooting/ai/" in history.text

    for path in ("/settings/troubleshooting", "/settings/troubleshooting/ai", first):
        assert alex.get(path).status_code == 403


def test_the_log_levels_are_set_from_the_page_and_a_bad_line_is_refused(app, sam, conn) -> None:
    def post(**values):
        form = {**logins._tokens(sam, "/settings/troubleshooting"), "section": "troubleshooting"}
        return sam.post("/settings", data={**form, **values})

    refused = post(log_areas="models=LOUD")
    assert refused.status_code == 400 and "models=LOUD" in refused.text
    root = logging.getLogger().level
    saved = post(
        log_level="WARNING",
        problem_log_level="ERROR",
        log_areas="models=DEBUG",
        keep_ai_text_days="3",
    )
    assert saved.status_code == 302
    live = app.settings
    assert (live.log_level, live.problem_log_level, live.log_areas) == (
        "WARNING",
        "ERROR",
        "models=DEBUG",
    )
    assert live.keep_ai_text_days == 3
    assert logging.getLogger("familydb.agent").level == logging.DEBUG
    # The process is left as it was.
    logs.apply_areas("")
    logging.getLogger().setLevel(root)
