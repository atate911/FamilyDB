"""The Personality page: who she is and who the family are, as the chat model is told them."""

import re

import pytest

from familydb import personas
from familydb.agent.prompt import build_system_blocks
from familydb.app import App
from familydb.store import settings as settings_store
from familydb.web import create_app

PASSWORD = "a long family password"


@pytest.fixture
def page(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.app_state = app
    return client


def _form(page, **values):
    text = page.get("/settings/personality").text
    csrf = re.search(r'name="csrf" value="([^"]+)"', text).group(1)
    return {"csrf": csrf, **values}


def _prefix(page, conn):
    page.app_state.refresh(conn)
    return build_system_blocks(conn, page.app_state.settings)


def test_the_page_shows_her_and_links_from_settings(page) -> None:
    assert "Personality and family" in page.get("/settings").text
    shown = page.get("/settings/personality").text
    # Her description as written, with {name} where her name goes, and the name it stands for.
    assert "You are {name}, an AI assistant" in shown and "{name} is her name, Vera" in shown
    assert 'value="default" selected>Vera</option>' in shown
    assert "About the family" in shown and "tokens now" in shown


def test_about_the_family_reaches_every_chat(page, conn) -> None:
    about = "The girls are 7 and 10 and love animals. Alex is vegetarian."
    form = _form(
        page,
        persona="default",
        persona_text=personas.load(personas.DEFAULT).character,
        about_family=about,
    )
    assert page.post("/settings/personality", data=form).status_code == 302
    family_block = _prefix(page, conn)[1].text
    assert "About the family, in their words:\n" + about in family_block
    # The same text as hers is no rewrite, and she is already the default: only the family's
    # words are stored.
    assert settings_store.overrides(conn) == {"about_family": about}


def test_a_rewrite_is_used_and_can_be_restored(page, conn) -> None:
    rewrite = "You are {name}. Be very brief, and a little dry."
    page.post(
        "/settings/personality",
        data=_form(page, persona="default", persona_text=rewrite, about_family=""),
    )
    told = "# Who you are\n\nYou are Vera. Be very brief, and a little dry."
    assert _prefix(page, conn)[0].text.startswith(told)
    assert settings_store.overrides(conn)["persona_text"] == rewrite  # kept as written
    history = page.get("/settings").text
    assert "rewritten" in history and "a little dry" not in history  # not echoed in the log
    assert page.post("/settings/personality/restore", data=_form(page)).status_code == 302
    assert _prefix(page, conn)[0].text.startswith(
        "# Who you are\n\n" + personas.load(personas.DEFAULT).prompt
    )


def test_her_own_text_with_her_name_filled_in_is_no_rewrite(page, conn) -> None:
    """A form drawn before her name was written once showed her name, and the old key."""
    form = _form(
        page,
        persona="vera",
        persona_text=personas.load(personas.DEFAULT).prompt,
        about_family="",
    )
    assert page.post("/settings/personality", data=form).status_code == 302
    assert settings_store.overrides(conn) == {}


def test_none_means_none_whatever_was_written(page, conn) -> None:
    page.post(
        "/settings/personality",
        data=_form(page, persona="none", persona_text="You are Zorblax.", about_family=""),
    )
    first = _prefix(page, conn)[0].text
    assert first.startswith("You are the private planning assistant") and "Zorblax" not in first


def test_too_long_or_unknown_is_refused_and_kept(page, conn) -> None:
    long = "x" * 4_001
    refused = page.post(
        "/settings/personality",
        data=_form(page, persona="default", persona_text="", about_family=long),
    )
    assert refused.status_code == 400 and "Nothing was saved" in refused.text
    assert long in refused.text  # what was typed is not lost
    unknown = page.post(
        "/settings/personality",
        data=_form(page, persona="hal", persona_text="", about_family=""),
    )
    assert unknown.status_code == 400 and "no persona called" in unknown.text
    assert settings_store.overrides(conn) == {}


def test_a_form_from_elsewhere_is_refused(page, conn) -> None:
    forged = page.post(
        "/settings/personality", data={"persona": "", "persona_text": "", "about_family": "x"}
    )
    assert forged.status_code == 400 and settings_store.overrides(conn) == {}


def test_her_lines_can_be_rewritten_and_a_bad_one_is_refused(page, conn) -> None:
    from familydb import voice

    shown = page.get("/settings/personality").text
    assert "What she says unasked" in shown
    assert "Can use {name}, {title}, {who}, {task}." in shown
    mine = "{name} here: {title}, that's #{task}."
    saved = page.post(
        "/settings/personality",
        data=_form(page, persona="default", persona_text="", about_family="", line_reminder=mine),
    )
    assert saved.status_code == 302
    assert settings_store.overrides(conn)["voice_lines"] == {"reminder": mine}
    page.app_state.refresh(conn)
    said = voice.say(page.app_state.settings, "reminder", title="Bins out", who="", task=3)
    assert said == "Vera here: Bins out, that's #3."
    refused = page.post(
        "/settings/personality",
        data=_form(page, persona="default", persona_text="", about_family="", line_follow_up="{x}"),
    )
    assert refused.status_code == 400
    assert "Asking how a plan went: {x} is not something it knows" in refused.text
    assert settings_store.overrides(conn)["voice_lines"] == {"reminder": mine}  # unchanged


def test_an_unknown_persona_is_refused_even_when_none_is_chosen(page, conn) -> None:
    page.post(
        "/settings/personality",
        data=_form(page, persona="none", persona_text="", about_family=""),
    )
    assert settings_store.overrides(conn)["persona"] == "none"
    unknown = page.post(
        "/settings/personality",
        data=_form(page, persona="hal", persona_text="", about_family=""),
    )
    assert unknown.status_code == 400 and "no persona called" in unknown.text
    assert settings_store.overrides(conn)["persona"] == "none"
