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
from familydb.web import create_app, views

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
    for name in ("persona_text", "persona_notes", "about_family"):
        if box := re.search(rf'name="{name}"[^>]*>(.*?)</textarea>', text, re.S):
            form[name] = html.unescape(box.group(1))
    if called := re.search(r'name="persona_name" value="([^"]*)"', text):
        form["persona_name"] = html.unescape(called.group(1))
    if described := re.search(r'name="described" value="([^"]+)"', text):
        form["described"] = described.group(1)
    return {**form, **changes}


def _prefix(page, conn):
    page.app_state.refresh(conn)
    return build_system_blocks(conn, page.app_state.settings)


def _tokens(page) -> int:
    """What the page says she and the family add to every message."""
    shown = page.get("/settings/personality").text
    return int(re.search(r"about ([\d,]+) tokens now", shown).group(1).replace(",", ""))


def test_the_page_shows_her_and_links_from_settings(page) -> None:
    assert "Personality and family" in page.get("/settings").text
    shown = page.get("/settings/personality").text
    # Her description as written, with {name} where her name goes, and the name it stands for.
    assert "You are {name}, an AI assistant" in shown
    assert "{name} is what she is called, Vera, wherever it is written." in shown
    assert 'value="default" selected>Vera</option>' in shown
    # What the family call her: nothing of theirs yet, so her own name is the placeholder.
    assert "What she is called" in shown
    assert re.search(r'<input id="p-name"[^>]*value=""[^>]*placeholder="Vera"', shown, re.S)
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


def test_a_name_of_their_own_is_hers_wherever_she_is_named(page, conn) -> None:
    """Everything that asks who she is follows it: the chat model, her lines and the page."""
    from familydb import voice

    saved = page.post("/settings/personality", data=_drawn(page, persona_name=" Juno "))
    assert saved.status_code == 302
    assert settings_store.overrides(conn) == {"persona_name": "Juno"}
    shown = page.get("/settings/personality").text
    assert "Saved. Changed: her name." in shown
    assert re.search(r'<input id="p-name"[^>]*value="Juno"[^>]*placeholder="Vera"', shown, re.S)
    assert "{name} is what she is called, Juno, wherever it is written." in shown
    assert _prefix(page, conn)[0].text.startswith("# Who you are\n\nYou are Juno, an AI assistant")
    assert voice.say(page.app_state.settings, "start").startswith("Hi, I'm Juno.")
    chat = page.get("/chat").text
    assert "<title>Juno · " in chat and '<span class="label">Juno</span>' in chat
    assert "Vera" not in chat
    history = page.get("/settings").text
    assert re.search(r"<strong>persona_name</strong>\s*from the environment → Juno", history)


def test_under_none_the_bot_is_familydb_and_their_name_for_her_is_kept(page, conn) -> None:
    """A name belongs to a persona: with none the bot is itself, and the family's name for her
    comes back with her."""
    from familydb import voice

    page.post("/settings/personality", data=_drawn(page, persona_name="Juno"))
    assert page.post("/settings/personality", data=_drawn(page, persona="none")).status_code == 302
    assert settings_store.overrides(conn) == {"persona": "none", "persona_name": "Juno"}
    assert all("Juno" not in block.text for block in _prefix(page, conn))
    assert voice.say(page.app_state.settings, "start").startswith("Hi! I'm FamilyDB,")
    chat = page.get("/chat").text
    assert "<title>Chat · " in chat and "Juno" not in chat
    shown = page.get("/settings/personality").text
    assert 'name="persona_name"' not in shown
    assert "The name you gave her, Juno, is kept for when she is chosen again." in shown
    # Saved under none, with no box for her name, and then with her chosen again.
    assert page.post("/settings/personality", data=_drawn(page)).status_code == 302
    again = page.post("/settings/personality", data=_drawn(page, persona="default"))
    assert again.status_code == 302
    assert settings_store.overrides(conn) == {"persona_name": "Juno"}
    assert _prefix(page, conn)[0].text.startswith("# Who you are\n\nYou are Juno, an AI assistant")


def test_her_own_name_or_an_empty_box_is_no_name_of_theirs(page, conn) -> None:
    """Neither is stored; a form drawn before there was a box for her name leaves theirs alone."""
    for own in ("Vera", " Vera ", ""):
        saved = page.post("/settings/personality", data=_drawn(page, persona_name=own))
        assert saved.status_code == 302 and settings_store.overrides(conn) == {}, own
    page.post("/settings/personality", data=_drawn(page, persona_name="Juno"))
    old_form = _form(page, persona="default", persona_text="", about_family="")
    assert page.post("/settings/personality", data=old_form).status_code == 302
    assert settings_store.overrides(conn) == {"persona_name": "Juno"}
    page.post("/settings/personality", data=_drawn(page, persona_name="Vera"))
    assert settings_store.overrides(conn) == {}
    assert personas.active(page.app_state.settings) == personas.load(personas.DEFAULT)


def test_a_name_that_will_not_do_is_refused_and_nothing_is_saved(page, conn) -> None:
    """A brace would be filled in again wherever {name} is, and a name goes on one line."""
    assert 'maxlength="40"' in page.get("/settings/personality").text
    refusals = {
        "{name}": "cannot have a brace in it",
        "Ju}no": "cannot have a brace in it",
        "Ju\nno": "goes on one line",
        "Ju\x07no": "goes on one line",
        "J" * 41: "at most 40 characters",
    }
    for bad, why in refusals.items():
        form = _drawn(page, persona_name=bad, about_family="The girls are 7 and 10.")
        refused = page.post("/settings/personality", data=form)
        assert refused.status_code == 400 and "Nothing was saved" in refused.text, repr(bad)
        assert why in refused.text, repr(bad)
        assert settings_store.overrides(conn) == {}, repr(bad)


def test_her_own_name_takes_back_one_the_environment_gave_her(settings, clock, conn, family):
    """An empty box says she is herself, so it is stored over a name from the environment,
    which would otherwise stay; the environment's own name is not stored over it."""
    named = settings.model_copy(update={"web_password": PASSWORD, "persona_name": "Juno"})
    page = _signed_in(App(named, clock))
    assert 'value="Juno"' in page.get("/settings/personality").text
    for own in ("", "Vera"):
        page.post("/settings/personality", data=_drawn(page, persona_name="Ada"))
        saved = page.post("/settings/personality", data=_drawn(page, persona_name=own))
        assert saved.status_code == 302 and settings_store.overrides(conn) == {"persona_name": ""}
        assert personas.active(page.app_state.settings).name == "Vera", own
        assert re.search(r'<input id="p-name"[^>]*value=""', page.get("/settings/personality").text)
    page.post("/settings/personality", data=_drawn(page, persona_name="Juno"))
    assert settings_store.overrides(conn) == {}
    assert personas.active(page.app_state.settings).name == "Juno"


NOTES = "No emoji. Call Mia Captain. Less chat in the mornings."


def test_the_family_s_notes_reach_the_prefix_after_her_character_and_before_the_job(
    page, conn
) -> None:
    shown = page.get("/settings/personality").text
    assert "Anything to add" in shown
    box = r'<textarea id="p-notes" name="persona_notes" rows="4"\s+maxlength="1000">'
    assert re.search(box, shown)
    before = _tokens(page)
    saved = page.post("/settings/personality", data=_drawn(page, persona_notes=f" {NOTES}\r\n"))
    assert saved.status_code == 302
    assert settings_store.overrides(conn) == {"persona_notes": NOTES}
    told = (
        "# Who you are\n\n"
        + personas.load(personas.DEFAULT).prompt
        + "\n\n## The family's own notes on how you talk\n\n"
        + NOTES
        + "\n\n# The job\n\nYou are the private planning assistant"
    )
    assert _prefix(page, conn)[0].text.startswith(told)
    shown = page.get("/settings/personality").text
    assert "Saved. Changed: notes on how she talks." in shown
    assert f'maxlength="1000">{NOTES}</textarea>' in shown
    assert _tokens(page) > before  # what they add to every message is counted
    history = page.get("/settings").text
    assert "persona_notes" in history and "Captain" not in history  # not echoed in the log


def test_notes_are_kept_under_none_and_unused_and_come_back_with_her(page, conn) -> None:
    page.post("/settings/personality", data=_drawn(page, persona_notes=NOTES))
    assert page.post("/settings/personality", data=_drawn(page, persona="none")).status_code == 302
    assert all("Captain" not in block.text for block in _prefix(page, conn))
    shown = page.get("/settings/personality").text
    assert 'name="persona_notes"' not in shown
    assert "What you added on how she talks is kept for when she is chosen again." in shown
    # Saved under none, with no box for them, and then with her chosen again.
    assert page.post("/settings/personality", data=_drawn(page)).status_code == 302
    again = page.post("/settings/personality", data=_drawn(page, persona="default"))
    assert again.status_code == 302
    assert settings_store.overrides(conn) == {"persona_notes": NOTES}
    assert NOTES in _prefix(page, conn)[0].text


def test_a_box_not_sent_leaves_the_notes_and_an_empty_one_drops_them(page, conn) -> None:
    """A form drawn before there was a box for them leaves them as they are."""
    page.post("/settings/personality", data=_drawn(page, persona_notes=NOTES))
    old_form = _form(page, persona="default", persona_text="", about_family="")
    assert page.post("/settings/personality", data=old_form).status_code == 302
    assert settings_store.overrides(conn) == {"persona_notes": NOTES}
    emptied = page.post("/settings/personality", data=_drawn(page, persona_notes=" "))
    assert emptied.status_code == 302
    assert settings_store.overrides(conn) == {}
    assert personas.active(page.app_state.settings) == personas.load(personas.DEFAULT)


def test_notes_too_long_are_refused_and_kept(page, conn) -> None:
    long = "x" * 1_001
    refused = page.post("/settings/personality", data=_drawn(page, persona_notes=long))
    assert refused.status_code == 400 and "Nothing was saved" in refused.text
    assert f">{long}</textarea>" in refused.text and settings_store.overrides(conn) == {}


def test_notes_outlast_her_rewrite_being_restored(page, conn) -> None:
    """They are not a copy of her description, so restoring hers leaves them in force."""
    rewrite = "You are {name}. Be very brief."
    page.post("/settings/personality", data=_drawn(page, persona_text=rewrite, persona_notes=NOTES))
    assert _prefix(page, conn)[0].text.startswith(
        "# Who you are\n\nYou are Vera. Be very brief.\n\n## The family's own notes"
    )
    assert page.post("/settings/personality/restore", data=_form(page)).status_code == 302
    assert settings_store.overrides(conn) == {"persona_notes": NOTES}
    first = _prefix(page, conn)[0].text
    assert first.startswith("# Who you are\n\n" + personas.load(personas.DEFAULT).prompt)
    assert f"{NOTES}\n\n# The job" in first
    assert f">{NOTES}</textarea>" in page.get("/settings/personality").text


def _rewritten_from(conn, of: str) -> None:
    """A rewrite of her, written when her own description was `of`."""
    with transaction(conn):
        settings_store.set_many(
            conn, {"persona_text": {"default": {"text": "You are {name}. Dry.", "of": of}}}
        )


def test_the_page_says_when_her_own_description_has_changed_since_she_was_rewritten(
    page, conn
) -> None:
    """Her own, as it was when they rewrote her, with one of its lines worded otherwise then:
    the page says so above their rewrite, and shows the line as it was and as it is."""
    hers = personas.load(personas.DEFAULT).character
    line = "Be recognizably {name} without making every response a demonstration of {name}."
    assert line in hers
    _rewritten_from(conn, hers.replace(line, "Be {name}, and do not overdo it."))
    shown = page.get("/settings/personality").text
    notice = "Vera's own description has changed since you rewrote her."
    assert notice in shown and "Your rewrite is as you left it." in shown
    assert shown.index(notice) < shown.index('name="persona_text"')  # above her description
    changes = re.search(r'<pre class="changes">(.*?)</pre>', shown, re.S).group(1)
    assert '<span class="removed">-Be {name}, and do not overdo it.' in changes
    assert '<span class="added">+Be recognizably {name} without making every response' in changes
    assert '<span class="same"> ' in changes  # a line either side, as it was
    assert "@@" not in changes and "---" not in changes  # no headers a family cannot read
    # With the name they call her, the notice says it.
    page.post("/settings/personality", data=_drawn(page, persona_name="Juno"))
    assert "Juno's own description has changed" in page.get("/settings/personality").text


def test_changes_far_apart_are_shown_apart_with_what_is_between_left_out() -> None:
    """Two lines of context either side of each change, and an ellipsis where the rest was."""
    before = "\n\n".join(f"Paragraph {n}." for n in range(1, 11))
    now = before.replace("Paragraph 2.", "Paragraph two.")
    now = now.replace("Paragraph 9.", "Paragraph nine.")
    assert views.line_changes(before, now) == [
        {"kind": "same", "text": " Paragraph 1."},
        {"kind": "same", "text": " "},
        {"kind": "removed", "text": "-Paragraph 2."},
        {"kind": "added", "text": "+Paragraph two."},
        {"kind": "same", "text": " "},
        {"kind": "same", "text": " Paragraph 3."},
        {"kind": "same", "text": "…"},
        {"kind": "same", "text": " Paragraph 8."},
        {"kind": "same", "text": " "},
        {"kind": "removed", "text": "-Paragraph 9."},
        {"kind": "added", "text": "+Paragraph nine."},
        {"kind": "same", "text": " "},
        {"kind": "same", "text": " Paragraph 10."},
    ]
    assert views.line_changes(before, before) == []


def test_no_notice_while_her_own_description_is_as_it_was(page, conn) -> None:
    """Written from hers as she is now, or before what it was written from was remembered, or not
    rewritten at all: nothing to say."""
    assert "own description has changed" not in page.get("/settings/personality").text
    for of in (personas.load(personas.DEFAULT).character, ""):
        _rewritten_from(conn, of)
        shown = page.get("/settings/personality").text
        assert "This is your rewrite of the original." in shown, repr(of[:20])
        assert "own description has changed" not in shown and 'class="changes"' not in shown


def test_saving_a_changed_rewrite_ends_the_notice(page, conn) -> None:
    """Saving it unchanged keeps it as it was written; changing it writes it against her now."""
    _rewritten_from(conn, "You are {name}, as she once was.")
    assert "own description has changed" in page.get("/settings/personality").text
    assert page.post("/settings/personality", data=_drawn(page)).status_code == 302
    assert "own description has changed" in page.get("/settings/personality").text
    changed = _drawn(page, persona_text="You are {name}. Drier.")
    assert page.post("/settings/personality", data=changed).status_code == 302
    rewrite = settings_store.overrides(conn)["persona_text"]["default"]
    assert rewrite["of"] == personas.load(personas.DEFAULT).character
    shown = page.get("/settings/personality").text
    assert "own description has changed" not in shown and 'class="changes"' not in shown
    assert "This is your rewrite of the original." in shown


def test_under_none_nothing_is_said_of_her_own_description_changing(page, conn) -> None:
    _rewritten_from(conn, "You are {name}, as she once was.")
    page.post("/settings/personality", data=_drawn(page, persona="none"))
    shown = page.get("/settings/personality").text
    assert "own description has changed" not in shown and 'class="changes"' not in shown
