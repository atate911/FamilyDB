"""The Personality page: who she is and who the family are, as the chat model is told them."""

import html
import re
from dataclasses import replace

import pytest

from familydb import personas
from familydb.agent.prompt import build_system_blocks
from familydb.app import App
from familydb.config import PersonaRewrite
from familydb.store import settings as settings_store
from familydb.store.db import transaction
from familydb.web import create_app

PASSWORD = "a long family password"


def _signed_in(app):
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    client.app_state = app
    return client


@pytest.fixture
def page(settings, clock, conn, family):
    return _signed_in(App(settings.model_copy(update={"web_password": PASSWORD}), clock))


@pytest.fixture
def brief(monkeypatch):
    """A second persona beside Vera, as a folder of her own would give her."""
    stand_in = replace(personas.load(personas.DEFAULT), key="brief", character="You are {name}.")
    shipped = personas.load
    monkeypatch.setattr(personas, "available", lambda: (personas.DEFAULT, "brief"))
    monkeypatch.setattr(personas, "load", lambda key: stand_in if key == "brief" else shipped(key))
    return stand_in


def _form(page, **values):
    text = page.get("/settings/personality").text
    csrf = re.search(r'name="csrf" value="([^"]+)"', text).group(1)
    return {"csrf": csrf, **values}


def _drawn(page, **changes):
    """The form as the page draws it, sent with these changes, as a browser would send it."""
    text = page.get("/settings/personality").text
    form = {
        "csrf": re.search(r'name="csrf" value="([^"]+)"', text).group(1),
        "persona": re.search(r'<option value="([^"]+)" selected>', text).group(1),
    }
    for name in ("persona_text", "about_family"):
        if box := re.search(rf'name="{name}"[^>]*>(.*?)</textarea>', text, re.S):
            form[name] = html.unescape(box.group(1))
    if described := re.search(r'name="described" value="([^"]+)"', text):
        form["described"] = described.group(1)
    return {**form, **changes}


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
    # Kept as written, as hers, with her own character as it was when they rewrote it.
    written_of = personas.load(personas.DEFAULT).character
    assert settings_store.overrides(conn)["persona_text"] == {
        "default": {"text": rewrite, "of": written_of}
    }
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


def test_choosing_none_keeps_her_rewrite_for_when_she_is_chosen_again(page, conn) -> None:
    """Rewrite her, choose none and save, choose her again and save: her rewrite is in force."""
    rewrite = "You are {name}. Be very brief, and a little dry."
    page.post("/settings/personality", data=_drawn(page, persona_text=rewrite))
    assert page.post("/settings/personality", data=_drawn(page, persona="none")).status_code == 302
    # Under none nobody is described: no box to empty, and a line to say theirs is waiting.
    shown = page.get("/settings/personality").text
    assert 'name="persona_text"' not in shown and 'name="described"' not in shown
    assert "What you wrote for her description is kept for when she is chosen again." in shown
    assert settings_store.overrides(conn)["persona_text"]["default"]["text"] == rewrite
    # A form drawn under none before the box said whom it described sent an empty one.
    old_form = _form(page, persona="none", persona_text="", about_family="")
    assert page.post("/settings/personality", data=old_form).status_code == 302
    again = page.post("/settings/personality", data=_drawn(page, persona="default"))
    assert again.status_code == 302
    told = "# Who you are\n\nYou are Vera. Be very brief, and a little dry."
    assert _prefix(page, conn)[0].text.startswith(told)
    assert "This is your rewrite of the original." in page.get("/settings/personality").text


def test_under_none_nothing_is_said_to_be_kept_when_nothing_was_written(page) -> None:
    page.post("/settings/personality", data=_drawn(page, persona="none"))
    shown = page.get("/settings/personality").text
    assert 'name="persona_text"' not in shown and "kept for when she is chosen again" not in shown


def test_a_rewrite_belongs_to_the_persona_it_described(page, conn, brief) -> None:
    """The box describes the persona in force when the page was drawn, so choosing another in
    the same save leaves the new one as she is."""
    mine = "You are {name}. A little dry."
    form = _drawn(page, persona="brief", persona_text=mine)
    assert page.post("/settings/personality", data=form).status_code == 302
    page.app_state.refresh(conn)
    live = page.app_state.settings
    assert live.persona == "brief" and set(live.persona_text) == {personas.DEFAULT}
    assert personas.active(live).character == brief.character  # Vera's rewrite is not hers
    shown = page.get("/settings/personality").text
    assert 'name="described" value="brief"' in shown and "This is your rewrite" not in shown
    # Her own rewrite is hers, and restoring her drops hers alone.
    page.post("/settings/personality", data=_drawn(page, persona_text="You are {name}. Terse."))
    assert set(settings_store.overrides(conn)["persona_text"]) == {personas.DEFAULT, "brief"}
    assert _prefix(page, conn)[0].text.startswith("# Who you are\n\nYou are Vera. Terse.")
    restored = page.post("/settings/personality/restore", data=_form(page, described="brief"))
    assert restored.status_code == 302
    kept = settings_store.overrides(conn)["persona_text"]
    assert set(kept) == {personas.DEFAULT} and kept[personas.DEFAULT]["text"] == mine
    assert _prefix(page, conn)[0].text.startswith("# Who you are\n\nYou are Vera.\n")


def test_a_rewrite_says_which_of_her_it_was_written_from(page, conn) -> None:
    """So the page can tell later when her own character has changed since. Saving it unchanged
    keeps what it was written from; changing it writes it against her as she is now."""
    theirs = "You are {name}. Dry."
    with transaction(conn):
        settings_store.set_many(
            conn, {"persona_text": {"default": {"text": theirs, "of": "Her, once."}}}
        )
    assert page.post("/settings/personality", data=_drawn(page)).status_code == 302
    assert settings_store.overrides(conn)["persona_text"] == {
        "default": {"text": theirs, "of": "Her, once."}
    }
    page.post("/settings/personality", data=_drawn(page, persona_text="You are {name}. Drier."))
    now = personas.load(personas.DEFAULT).character
    assert settings_store.overrides(conn)["persona_text"] == {
        "default": {"text": "You are {name}. Drier.", "of": now}
    }


def test_a_rewrite_stored_as_it_used_to_be_is_still_hers(page, conn) -> None:
    """One string, from before rewrites were kept per persona: shown as hers, used as hers, and
    not written again by a save that changes nothing."""
    theirs = "You are {name}. Dry."
    with transaction(conn):
        settings_store.set_many(conn, {"persona_text": theirs})
    shown = page.get("/settings/personality").text
    assert f">{theirs}</textarea>" in shown and "This is your rewrite of the original." in shown
    assert _prefix(page, conn)[0].text.startswith("# Who you are\n\nYou are Vera. Dry.")
    page.post("/settings/personality", data=_drawn(page))
    assert settings_store.overrides(conn)["persona_text"] == theirs
    assert "Nothing was different" in page.get("/settings/personality").text


def test_a_rewrite_from_the_environment_can_be_restored_too(settings, clock, conn, family) -> None:
    """Restoring her stores that there is no rewrite, since dropping the page's value would only
    bring the environment's back."""
    rewrites = {personas.DEFAULT: PersonaRewrite(text="You are {name}. From a file.")}
    base = settings.model_copy(update={"web_password": PASSWORD, "persona_text": rewrites})
    page = _signed_in(App(base, clock))
    assert "This is your rewrite of the original." in page.get("/settings/personality").text
    assert page.post("/settings/personality/restore", data=_form(page)).status_code == 302
    assert settings_store.overrides(conn)["persona_text"] == {}
    assert personas.active(page.app_state.settings) == personas.load(personas.DEFAULT)


def test_a_rewrite_too_long_is_refused_and_kept(page, conn) -> None:
    assert 'maxlength="20000"' in page.get("/settings/personality").text
    long = "You are {name}. " + "x" * 20_000
    refused = page.post("/settings/personality", data=_drawn(page, persona_text=long))
    assert refused.status_code == 400 and "Nothing was saved" in refused.text
    assert long in refused.text and settings_store.overrides(conn) == {}


def test_a_box_said_to_describe_nobody_writes_nothing(page, conn) -> None:
    """A crafted form can only rewrite a persona there is a folder for: naming none, or one with
    no folder, leaves every rewrite as stored, and so does restoring either."""
    theirs = "You are {name}. Dry."
    page.post("/settings/personality", data=_drawn(page, persona_text=theirs))
    stored = settings_store.overrides(conn)["persona_text"]
    for nobody in ("none", "hal"):
        form = _drawn(page, described=nobody, persona_text="You are Zorblax.")
        assert page.post("/settings/personality", data=form).status_code == 302
        restored = page.post("/settings/personality/restore", data=_form(page, described=nobody))
        assert restored.status_code == 302
        assert settings_store.overrides(conn)["persona_text"] == stored
    assert "Zorblax" not in _prefix(page, conn)[0].text
