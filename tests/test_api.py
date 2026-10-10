"""The API (web/api.py, web/answers.py; docs/INTERFACE.md section 11): every page of the family's
as the data it draws, the box's message and the page's forms from a script, behind the same
sign-in, permissions and CSRF token as the page. No model call for a read."""

from __future__ import annotations

import json
from typing import Any

import pytest

from familydb import family as rules
from familydb.app import App
from familydb.store import db, ideas, outcomes, plans, tasks, wishes
from familydb.web import answers, api, create_app, edits
from tests import fakes
from tests.conftest import NOW_ISO

SAM = ("Sam", "sam likes long sentences")
GIRLS = ("the girls", "a kid can choose one too")


@pytest.fixture
def app(settings, clock, conn, family):
    shared = {"web_password": "installer-made-password-1", "kid_daily_messages": 20}
    live = App(settings.model_copy(update=shared), clock)
    rules.choose_password(conn, family["sam"].id, SAM[1], now=NOW_ISO)
    rules.choose_password(conn, family["girls"].id, GIRLS[1], now=NOW_ISO)
    return live


@pytest.fixture
def household(conn, family) -> dict[str, Any]:
    """A little of everything a page draws: a place, an outing done and rated, a plan, a present
    kept from the kids, a to-do of the kids' and one of Sam's, and a wish."""
    with db.transaction(conn):
        ramen = ideas.insert(conn, title="Kenji's Ramen", kind="restaurant", now=NOW_ISO)
        hike = ideas.insert(conn, title="Silver Falls hike", kind="outing", now=NOW_ISO)
        bike = ideas.insert(conn, title="A red bike", kind="gift", now=NOW_ISO)
        plan = plans.insert(
            conn,
            title="Silver Falls hike",
            start="2026-09-17T10:00",
            end="2026-09-17T14:00",
            all_day=False,
            idea_id=hike.id,
        )
        went = outcomes.insert(
            conn,
            idea_id=hike.id,
            plan_id=plan.id,
            happened_on="2026-09-17",
            rating=9,
            would_repeat=True,
            notes=None,
            recorded_by=family["sam"].id,
            now=NOW_ISO,
        )
        fish, dentist = (
            tasks.insert(
                conn,
                title=title,
                notes="",
                owner_id=family[owner].id,
                due_at=None,
                preferred_window="",
                operation_key=f"test-{title}",
                channel="web",
                chat_id="web",
                now=NOW_ISO,
            )
            for title, owner in (("Feed the fish", "girls"), ("Call the dentist", "sam"))
        )
        wish = wishes.insert(
            conn,
            member_id=family["girls"].id,
            title="Roller skates",
            topic="roller skates",
            occasion=None,
            rank=1,
            now=NOW_ISO,
        )
    return {
        "ramen": ramen.id,
        "hike": hike.id,
        "bike": bike.id,
        "plan": plan.id,
        "went": went.id,
        "fish": fish,
        "dentist": dentist,
        "wish": wish.id,
    }


def _in_as(app: App, who: tuple[str, str], *, api_: Any = None):
    client = create_app(app, api=api_).test_client()
    assert client.post("/login", data={"name": who[0], "password": who[1]}).status_code == 302
    return client


def _token(client) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api").json["csrf"]}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


def _pages(household: dict[str, Any]) -> list[str]:
    return [
        "now",
        "about",
        "board",
        "chat",
        "eat",
        "do",
        f"place/{household['ramen']}",
        f"idea/{household['hike']}",
        "week",
        "week/2026-09-17",
        f"plan/{household['plan']}",
        f"reminder/{household['dentist']}",
        "tasks",
        "kids",
        "kids/the-girls",
        "soon",
        "lists",
        "did",
        f"did/{household['went']}",
        "plans",
        "plans/month",
        "memory",
        "status",
    ]


# -- reading


def test_signed_out_a_script_is_told_to_sign_in_never_sent_to_a_form(app) -> None:
    client = create_app(app).test_client()
    for asked in (client.get("/api"), client.get("/api/now"), client.get("/api/find?q=ra")):
        assert asked.status_code == 401 and asked.json == {"error": "sign in first"}
    for path in ("/api/say", "/api/act"):
        posted = client.post(path, json={"text": "hello"})
        assert posted.status_code == 401 and posted.json == {"error": "sign in first"}


def test_the_index_says_who_is_asking_what_they_may_read_and_the_token(app, household) -> None:
    told = _in_as(app, SAM).get("/api").json
    assert told["who"] == "Sam" and told["role"] == "admin"
    assert {page["endpoint"] for page in told["pages"]} == set(api.PAGES)
    assert told["say"] == "/api/say" and told["act"] == "/api/act" and told["find"] == "/api/find"
    assert told["csrf"] and told["csrf_header"] == "X-CSRF-Token"
    acts = {one["act"]: one["takes"] for one in told["acts"]}
    assert acts["finish_task"] == ["task_id"] and "change_list" in acts and "act" not in acts

    kid = _in_as(app, GIRLS).get("/api").json
    readable = {page["endpoint"] for page in kid["pages"]}
    assert "web.home" in readable and "go.week" in readable
    assert not readable & {"web.status", "web.happening_page", "web.memory", "web.find"}
    kid_acts = {one["act"] for one in kid["acts"]}
    assert {"finish_task", "add_wish", "undo"} <= kid_acts
    assert not kid_acts & {"answer_wish", "change_list", "add_idea", "set_status"}


def test_every_page_is_its_own_answer_with_the_box_and_the_row_and_asks_no_model(
    app, household
) -> None:
    model = fakes.FakeMessagesAPI()  # nothing to say: any call would fail the test
    client = _in_as(app, SAM, api_=model)
    for path in _pages(household):
        got = client.get(f"/api/{path}")
        assert got.status_code == 200, (path, got.json)
        assert got.mimetype == "application/json"
        assert set(got.json) == {"page", "answer", "box", "row"}, path
        assert not _keys(got.json) & answers.NEVER, (path, _keys(got.json) & answers.NEVER)
        text = json.dumps(got.json)
        assert "sam likes long sentences" not in text and "scrypt" not in text, path
    assert model.requests == []
    now = client.get("/api/now").json
    assert now["page"] == "now" and isinstance(now["row"], list) and now["row"]
    place = client.get(f"/api/place/{household['ramen']}").json
    assert "Kenji's Ramen" in json.dumps(place["answer"])


def test_a_kid_reads_her_own_pages_and_is_refused_the_rest_in_json(app, household) -> None:
    kid = _in_as(app, GIRLS)
    for path in ("now", "week", "do", "kids", "board"):
        got = kid.get(f"/api/{path}")
        assert got.status_code == 200, (path, got.json)
        text = json.dumps(got.json)
        assert "A red bike" not in text, path  # a present is kept from every kid
        assert "Call the dentist" not in text, path  # only her own to-dos
    assert "Feed the fish" in json.dumps(kid.get("/api/now").json)
    for path in ("soon", "status", "memory", f"reminder/{household['fish']}"):
        refused = kid.get(f"/api/{path}")
        assert refused.status_code == 403 and "error" in refused.json, path


def test_what_is_not_a_page_of_the_familys_is_not_an_answer(app, household) -> None:
    client = _in_as(app, SAM)
    for path in ("nowhere", "settings", "family", "wiki", "more", "export/ideas.csv", "say"):
        missing = client.get(f"/api/{path}")
        assert missing.status_code == 404 and missing.json == {"error": api.NOT_A_PAGE}, path


# -- saying something


def test_a_message_from_a_script_is_answered_on_the_page_it_names(app, household) -> None:
    model = fakes.FakeMessagesAPI(fakes.message([fakes.text("Kenji's is open till nine.")]))
    client = _in_as(app, SAM, api_=model)
    web = client.application
    sent = client.post(
        "/api/say",
        json={"text": "is it open tonight?", "page": "/eat", "scope": "About Kenji's Ramen:"},
        headers=_token(client),
    )
    assert sent.status_code == 202
    asked = sent.json["asked"]
    assert sent.json["check"] == f"/api/eat?asked={asked}"
    assert web.config["FAMILYDB_CHAT"].wait(10)
    box = client.get(sent.json["check"]).json["box"]
    said = box["said"]
    assert said["text"] == "Kenji's is open till nine." and "is it open tonight?" in said["asked"]
    # The page's scope went ahead of what was typed, as the box sends it.
    assert len(model.requests) == 1
    assert "About Kenji's Ramen: is it open tonight?" in json.dumps(model.requests[0])


def test_saying_needs_the_token_and_this_pages_origin(app, household) -> None:
    client = _in_as(app, SAM)
    bare = client.post("/api/say", json={"text": "hello"})
    assert bare.status_code == 400 and "error" in bare.json
    elsewhere = client.post(
        "/api/say",
        json={"text": "hello"},
        headers={**_token(client), "Origin": "https://example.com"},
    )
    assert elsewhere.status_code == 400
    empty = client.post("/api/say", json={"text": "  "}, headers=_token(client))
    assert empty.status_code == 400 and empty.json["error"] == "There was nothing to send."


# -- the page's forms


def test_a_tap_is_the_forms_own_tool_call_and_can_be_taken_back(app, conn, household) -> None:
    client = _in_as(app, SAM)
    token = _token(client)
    task = tasks.get(conn, household["dentist"])
    done = client.post(
        "/api/act",
        json={"act": "finish_task", "task_id": task.id, "revision": task.revision},
        headers=token,
    )
    assert done.status_code == 200, done.json
    assert done.json["changed"] is True and done.json["said"] == "Done: Call the dentist."
    assert tasks.get(conn, task.id).status == "done" and done.json["undo"]
    back = client.post("/api/act", json={"act": "undo", "target": done.json["undo"]}, headers=token)
    assert back.status_code == 200 and back.json["changed"] is True
    assert tasks.get(conn, task.id).status == "open"
    # Its notice is the answer's, never left in the session for the next page.
    assert "Done: Call the dentist." not in client.get("/").text


def test_a_tap_carries_the_forms_checks(app, conn, household) -> None:
    client = _in_as(app, SAM)
    token = _token(client)
    stale = client.post(
        "/api/act", json={"act": "finish_task", "task_id": household["dentist"]}, headers=token
    )
    assert stale.status_code == 400 and stale.json["changed"] is False
    assert stale.json["said"] == "Reload this task before ticking it off."
    assert tasks.get(conn, household["dentist"]).status == "open"
    for wrong in ({"act": "nothing"}, {"act": "act"}, {"act": "finish_task", "task_id": "x"}):
        missing = client.post("/api/act", json=wrong, headers=token)
        assert missing.status_code == 404 and missing.json["error"] == edits.NOT_AN_ACT, wrong
    no_token = client.post("/api/act", json={"act": "look_up_waiting"})
    assert no_token.status_code == 400


def test_a_list_is_changed_and_a_kid_may_do_only_what_her_buttons_do(
    app, conn, family, household
) -> None:
    client = _in_as(app, SAM)
    added = client.post(
        "/api/act",
        json={"act": "change_list", "action": "add", "items": "milk\neggs", "name": "shopping"},
        headers=_token(client),
    )
    assert added.status_code == 200 and added.json["changed"] is True, added.json
    shopping = json.dumps(client.get("/api/lists/shopping").json["answer"])
    assert "milk" in shopping and "eggs" in shopping

    kid = _in_as(app, GIRLS)
    token = _token(kid)
    refused = kid.post(
        "/api/act",
        json={"act": "answer_wish", "wish_id": household["wish"], "status": "granted"},
        headers=token,
    )
    assert refused.status_code == 403 and wishes.get(conn, household["wish"]).status != "granted"
    not_hers = kid.post(
        "/api/act",
        json={"act": "change_list", "action": "add", "items": "candy", "name": "shopping"},
        headers=token,
    )
    assert not_hers.status_code == 403
    fish = tasks.get(conn, household["fish"])
    ticked = kid.post(
        "/api/act",
        json={"act": "finish_task", "task_id": fish.id, "revision": fish.revision},
        headers=token,
    )
    assert ticked.status_code == 200 and ticked.json["said"] == "Done: Feed the fish!"
    dentist = tasks.get(conn, household["dentist"])
    someone_elses = kid.post(
        "/api/act",
        json={"act": "finish_task", "task_id": dentist.id, "revision": dentist.revision},
        headers=token,
    )
    assert someone_elses.status_code == 400 and someone_elses.json["changed"] is False
    assert tasks.get(conn, dentist.id).status == "open"
