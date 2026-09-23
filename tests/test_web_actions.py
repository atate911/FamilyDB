"""Browser workflows, with real persistence and fake external services."""

from html.parser import HTMLParser

import pytest

from familydb.app import App
from familydb.pipeline import retry_message
from familydb.store import db, ideas, members, messages, plans
from familydb.web import actions, create_app
from tests.fakes import FakeCalendar, FakeMessagesAPI, message, text


class Fields(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.values = {}
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") and attrs.get("type") == "hidden":
            self.values.setdefault(attrs["name"], attrs.get("value", ""))


def form(client, path, **values):
    page = client.get(path)
    assert page.status_code == 200, page.text
    return {**Fields(page.text).values, **values}


def idea_form(client, path="/ideas/new", **values):
    return form(
        client,
        path,
        title="A picnic",
        kind="activity",
        setting="either",
        weather="any",
        status="idea",
        **values,
    )


def test_create_edit_clear_archive_and_replay(settings, clock, conn):
    client = create_app(App(settings, clock)).test_client()
    data = idea_form(client, description="By the lake", cost_level="2", tags="outside, weekend")
    result = client.post("/ideas/new", data=data)
    assert result.status_code == 303
    assert client.post("/ideas/new", data=data).headers["Location"] == result.headers["Location"]
    stored = ideas.list_all(conn)
    assert len(stored) == 1 and stored[0].tags == ["outside", "weekend"]
    path = f"/idea/{stored[0].id}/edit"
    changed = idea_form(client, path, description="", cost_level="")
    changed["status"] = "dropped"
    assert client.post(path, data=changed).status_code == 303
    saved = ideas.get(conn, stored[0].id)
    assert saved.status == "dropped" and saved.cost_level is None and not saved.description
    assert client.get(f"/idea/{saved.id}").status_code == 200


@pytest.mark.parametrize(
    "values",
    [
        {"title": " "},
        {"duration_min": "90", "duration_max": "20"},
        {"cost_level": "5"},
        {"url": "javascript:alert(1)"},
        {"status": "bogus"},
        {"duration_min": "-2"},
        {"seasons": "fall"},
    ],
)
def test_validation_keeps_draft_and_does_not_write(settings, clock, conn, values):
    client = create_app(App(settings, clock)).test_client()
    data = idea_form(client, description="Keep my draft")
    data.update(values)
    response = client.post("/ideas/new", data=data)
    assert response.status_code == 422 and "Keep my draft" in response.text
    assert not ideas.list_all(conn)


def test_stale_edit_does_not_overwrite_another_member(settings, clock, conn):
    client = create_app(App(settings, clock)).test_client()
    saved = ideas.insert(conn, title="Original", kind="activity")
    path = f"/idea/{saved.id}/edit"
    data = idea_form(client, path)
    with db.transaction(conn):
        ideas.update(conn, saved.id, {"title": "Someone else's change"})
    result = client.post(path, data=data)
    assert result.status_code == 422 and "Someone changed" in result.text
    assert ideas.get(conn, saved.id).title == "Someone else's change"


@pytest.mark.parametrize(
    "path",
    [
        "/ideas/new",
        "/idea/1/edit",
        "/plans/new",
        "/plan/1/edit",
        "/plan/1/cancel",
        "/assistant",
        "/assistant/1/retry",
        "/family",
        "/family/1/edit",
    ],
)
def test_every_write_requires_auth_csrf_and_same_origin(settings, clock, path):
    client = create_app(
        App(settings.model_copy(update={"web_password": "family secret pass"}), clock)
    ).test_client()
    assert client.post(path).status_code == 401
    client.post("/login", data={"password": "family secret pass"})
    assert client.post(path).status_code == 403
    data = form(client, "/ideas/new")
    assert (
        client.post(path, data=data, headers={"Origin": "https://evil.example"}).status_code == 403
    )


def test_form_token_cannot_be_forged_or_moved_between_actions(settings, clock, conn):
    client = create_app(App(settings, clock)).test_client()
    data = idea_form(client)
    assert client.post("/plans/new", data=data).status_code == 400
    data["operation"] = "forged"
    assert client.post("/ideas/new", data=data).status_code == 400
    assert not ideas.list_all(conn)


def test_calendar_create_replay_edit_cancel(calendar_settings, clock, conn):
    calendar = FakeCalendar(clock.tz)
    client = create_app(App(calendar_settings, clock, calendar=calendar)).test_client()
    data = form(
        client, "/plans/new", title="Lunch", start="2026-09-25T12:00", end="2026-09-25T13:00"
    )
    assert client.post("/plans/new", data=data).status_code == 303
    assert client.post("/plans/new", data=data).status_code == 303
    assert len(calendar.events) == 1
    saved = conn.execute("SELECT id FROM plans").fetchone()["id"]
    data = form(
        client,
        f"/plan/{saved}/edit",
        title="Dinner",
        start="2026-09-25T18:00",
        end="2026-09-25T19:00",
    )
    assert client.post(f"/plan/{saved}/edit", data=data).status_code == 303
    assert plans.get(conn, saved).title == "Dinner"
    page = client.get(f"/plan/{saved}/edit").text
    # The cancellation form has its own purpose-bound token.
    cancel = Fields(page[page.index('action="/plan/') :]).values
    assert client.post(f"/plan/{saved}/cancel", data=cancel).status_code == 400
    cancel["confirm"] = "yes"
    assert client.post(f"/plan/{saved}/cancel", data=cancel).status_code == 303
    assert plans.get(conn, saved).status == "cancelled"
    assert not calendar.events


def test_disconnected_calendar_keeps_form(settings, clock, conn):
    client = create_app(App(settings, clock)).test_client()
    data = form(client, "/plans/new", title="Our lunch", start="2026-09-25T12:00")
    response = client.post("/plans/new", data=data)
    assert response.status_code == 422 and "Our lunch" in response.text
    assert "not connected" in response.text
    assert conn.execute("SELECT count(*) FROM plans").fetchone()[0] == 0


def test_assistant_persists_reply_and_deduplicates(settings, clock, conn, family, monkeypatch):
    app = App(settings, clock)
    client = create_app(app).test_client()
    api = FakeMessagesAPI(message([text("Let's visit the lake.")]))

    monkeypatch.setattr(actions, "_start_process", actions._process)
    monkeypatch.setattr(actions, "retry_message", lambda app, mid: retry_message(app, mid, api=api))
    data = form(client, "/assistant", message="What can we do?", member_id=str(family["sam"].id))
    assert client.post("/assistant", data=data).status_code == 303
    assert client.post("/assistant", data=data).status_code == 303
    page = client.get("/assistant")
    assert "Let's visit the lake." in page.text.replace("&#39;", "'")
    assert conn.execute("SELECT count(*) FROM messages WHERE direction='in'").fetchone()[0] == 1
    assert len(api.requests) == 1


def test_assistant_preserves_draft_while_busy(settings, clock, family):
    web = create_app(App(settings, clock))
    client = web.test_client()
    data = form(client, "/assistant", message="Keep this draft", member_id=str(family["sam"].id))
    gate = web.config["FAMILYDB_WEB_CHAT_GATE"]
    gate.acquire()
    try:
        response = client.post("/assistant", data=data)
        assert response.status_code == 409 and "Keep this draft" in response.text
    finally:
        gate.release()


def test_pages_render_and_escape_saved_content(settings, clock, conn):
    saved = ideas.insert(conn, title="<script>alert(1)</script>", kind="restaurant")
    client = create_app(App(settings, clock)).test_client()
    for path in (
        "/home",
        "/",
        "/restaurants",
        "/plans",
        "/calendar",
        "/assistant",
        "/plans/new",
        f"/idea/{saved.id}",
    ):
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert "<script>alert(1)</script>" not in response.text
        assert "script-src 'none'" in response.headers["Content-Security-Policy"]


def test_native_date_controls_and_all_day_calendar(calendar_settings, clock, conn):
    calendar = FakeCalendar(clock.tz)
    client = create_app(App(calendar_settings, clock, calendar=calendar)).test_client()
    data = form(
        client,
        "/plans/new",
        title="Camping",
        start_date="2026-09-25",
        end_date="2026-09-27",
        start_time="",
        end_time="",
        all_day="on",
    )
    assert client.post("/plans/new", data=data).status_code == 303
    response = client.get("/calendar?month=2026-09")
    assert response.status_code == 200
    assert response.text.count(">Camping</a>") == 2
    assert "Live Google Calendar" in response.text
    for month in ("garbage", "0001-01", "9999-12"):
        assert client.get("/calendar?month=" + month).status_code == 400


def test_native_timed_form_requires_time(calendar_settings, clock, conn):
    calendar = FakeCalendar(clock.tz)
    client = create_app(App(calendar_settings, clock, calendar=calendar)).test_client()
    data = form(client, "/plans/new", title="Lunch", start_date="2026-09-25", start_time="")
    assert client.post("/plans/new", data=data).status_code == 422
    assert not calendar.events
    data["start_time"] = "12:00"
    assert client.post("/plans/new", data=data).status_code == 303
    event = next(iter(calendar.events.values()))
    assert not event.all_day and event.start.hour == 12


def test_saved_browser_request_can_resume_after_restart(settings, clock, conn, family, monkeypatch):
    with db.transaction(conn):
        saved = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="interrupted",
            chat_id="web:family",
            member_id=family["sam"].id,
            text="Suggest a picnic",
        )
    app = App(settings, clock)
    client = create_app(app).test_client()
    api = FakeMessagesAPI(message([text("Try the lake.")]))
    monkeypatch.setattr(actions, "_start_process", actions._process)
    monkeypatch.setattr(actions, "retry_message", lambda app, mid: retry_message(app, mid, api=api))
    data = form(client, "/assistant")
    assert client.post(f"/assistant/{saved.id}/retry", data=data).status_code == 303
    assert messages.get(conn, saved.id).status == "processed"
    assert "Try the lake." in client.get("/assistant").text
    assert len(api.requests) == 1


def test_family_setup_enables_assistant_and_prevents_duplicates(settings, clock, conn):
    client = create_app(App(settings, clock)).test_client()
    assert "Add a family member" in client.get("/assistant").text
    data = form(client, "/family", display_name="  Sam   Smith  ", role="admin")
    assert client.post("/family", data=data).status_code == 303
    assert members.list_all(conn)[0].display_name == "Sam Smith"
    assert "Sam Smith" in client.get("/assistant").text
    assert client.post("/family", data=data).status_code == 409
    data["display_name"] = "SAM SMITH"
    assert client.post("/family", data=data).status_code == 409
    assert len(members.list_all(conn)) == 1


@pytest.mark.parametrize("name,role", [(" ", "admin"), ("x" * 81, "kid"), ("Sam", "owner")])
def test_invalid_family_member_does_not_write(settings, clock, conn, name, role):
    client = create_app(App(settings, clock)).test_client()
    data = form(client, "/family", display_name=name, role=role)
    assert client.post("/family", data=data).status_code == 422
    assert not members.list_all(conn)


def test_calendar_midnight_end_and_utc_start_use_local_days(settings, clock, conn):
    # September 26, 00:00 UTC is September 25 at 17:00 for this family.
    with db.transaction(conn):
        plans.insert(
            conn,
            title="Evening concert",
            start="2026-09-26T00:00:00Z",
            end="2026-09-26T07:00:00Z",
            all_day=False,
        )
    client = create_app(App(settings, clock)).test_client()
    page = client.get("/calendar?month=2026-09").text
    assert page.count(">Evening concert</a>") == 1
    assert "<small>17:00</small>" in page
    agenda = client.get("/plans").text
    assert "Friday 25 September, 17:00" in agenda


def test_ongoing_plans_are_upcoming_and_exclusive_ends_are_recent(settings, clock, conn):
    with db.transaction(conn):
        plans.insert(
            conn, title="Still camping", start="2026-09-19", end="2026-09-22", all_day=True
        )
        plans.insert(
            conn, title="Finished trip", start="2026-09-18", end="2026-09-20", all_day=True
        )
    client = create_app(App(settings, clock)).test_client()
    home = client.get("/home").text
    assert "Still camping" in home and "Finished trip" not in home
    agenda = client.get("/plans").text
    coming, recent = agenda.split("<h2>Recently</h2>")
    assert "Still camping" in coming and "Finished trip" not in coming
    assert "Finished trip" in recent and "Still camping" not in recent


def test_member_edit_preserves_identity_and_channel(settings, clock, conn, family):
    person = family["alex"]
    client = create_app(App(settings, clock)).test_client()
    path = f"/family/{person.id}/edit"
    data = form(client, path, display_name="Alexandra", role="admin", active="yes")
    assert client.post(path, data=data).status_code == 303
    changed = members.get(conn, person.id)
    assert changed.display_name == "Alexandra" and changed.role == "admin"
    assert changed.channel == person.channel and changed.channel_user_id == person.channel_user_id
    assert changed.created_at == person.created_at


def test_deactivate_and_restore_preserves_history_but_stops_requests(settings, clock, conn, family):
    person = family["alex"]
    with db.transaction(conn):
        pending = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="before-disable",
            chat_id="web:family",
            member_id=person.id,
            text="Find an activity",
        )
    app = App(settings, clock)
    client = create_app(app).test_client()
    path = f"/family/{person.id}/edit"
    data = form(client, path, display_name=person.display_name, role="member", active="no")
    assert client.post(path, data=data).status_code == 303
    assert not members.get(conn, person.id).active
    assert members.resolve(conn, "telegram", person.channel_user_id) is None
    stopped = messages.get(conn, pending.id)
    assert stopped.give_up and stopped.error == "member_inactive" and stopped.status == "failed"
    page = client.get("/assistant").text
    assert "This request was stopped" in page and "Resume saved request" not in page
    assert 'http-equiv="refresh"' not in page
    message_form = form(client, "/assistant", member_id=str(person.id), message="Another request")
    assert client.post("/assistant", data=message_form).status_code == 422
    data = form(client, path, display_name=person.display_name, role="member", active="yes")
    assert client.post(path, data=data).status_code == 303
    assert members.resolve(conn, "telegram", person.channel_user_id).id == person.id
    api = FakeMessagesAPI()
    assert retry_message(app, pending.id, api=api) is None
    assert not api.requests


@pytest.mark.parametrize("role,active", [("admin", "no"), ("member", "yes")])
def test_last_admin_cannot_be_removed(settings, clock, conn, family, role, active):
    person = family["sam"]
    client = create_app(App(settings, clock)).test_client()
    path = f"/family/{person.id}/edit"
    data = form(client, path, display_name=person.display_name, role=role, active=active)
    response = client.post(path, data=data)
    assert response.status_code == 422 and "active administrator" in response.text
    assert members.get(conn, person.id) == person


def test_member_edit_rejects_stale_duplicate_and_running_request(settings, clock, conn, family):
    person = family["alex"]
    client = create_app(App(settings, clock)).test_client()
    path = f"/family/{person.id}/edit"
    duplicate = form(client, path, display_name="SAM", role="member", active="yes")
    assert client.post(path, data=duplicate).status_code == 422
    stale = form(client, path, display_name="A new name", role="member", active="yes")
    with db.transaction(conn):
        members.set_active(conn, person.id, False)
    assert "This profile changed" in client.post(path, data=stale).text
    with db.transaction(conn):
        members.set_active(conn, person.id, True)
        running = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="running",
            chat_id="web:family",
            member_id=person.id,
            text="Plan something",
        )
        conn.execute(
            "UPDATE messages SET claim_until = ? WHERE id = ?", ("2099-01-01T00:00:00Z", running.id)
        )
    data = form(client, path, display_name=person.display_name, role="member", active="no")
    response = client.post(path, data=data)
    assert response.status_code == 422 and "request running" in response.text
    assert members.get(conn, person.id).active


def test_retry_worker_rechecks_membership_after_deactivation(settings, clock, conn, family):
    person = family["alex"]
    with db.transaction(conn):
        pending = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="cli-disabled",
            chat_id="web:family",
            member_id=person.id,
            text="Plan something",
        )
        members.set_active(conn, person.id, False)
    api = FakeMessagesAPI()
    assert retry_message(App(settings, clock), pending.id, api=api) is None
    assert not api.requests
    assert messages.get(conn, pending.id).give_up


@pytest.mark.parametrize("terminal", ["give_up", "retry_limit"])
def test_stopped_request_does_not_block_new_conversation(
    settings, clock, conn, family, monkeypatch, terminal
):
    with db.transaction(conn):
        stopped = messages.insert_in(
            conn,
            channel="web",
            channel_update_id="stopped",
            chat_id="web:family",
            member_id=family["sam"].id,
            text="An old request",
        )
        if terminal == "give_up":
            messages.give_up(conn, stopped.id)
        else:
            conn.execute(
                "UPDATE messages SET retries = ? WHERE id = ?",
                (settings.retry_max_attempts, stopped.id),
            )
    app = App(settings, clock)
    client = create_app(app).test_client()
    api = FakeMessagesAPI(message([text("A fresh reply.")]))
    monkeypatch.setattr(actions, "_start_process", actions._process)
    monkeypatch.setattr(actions, "retry_message", lambda app, mid: retry_message(app, mid, api=api))
    page = client.get("/assistant").text
    assert 'http-equiv="refresh"' not in page and "Resume saved request" not in page
    data = form(client, "/assistant", member_id=str(family["sam"].id), message="A new request")
    assert client.post("/assistant", data=data).status_code == 303
    assert "A fresh reply." in client.get("/assistant").text
