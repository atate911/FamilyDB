"""The persona layer: who the assistant is, as one object, and the one in force."""

from dataclasses import replace

import pytest

from familydb import personas
from familydb.config import PersonaRewrite, Settings


def test_every_persona_ships_whole() -> None:
    """A folder is a persona when it names her, and her name is written there and only there."""
    assert personas.DEFAULT in personas.available()
    for key in personas.available():
        persona = personas.load(key)
        assert persona.key == key and persona.name.strip(), key
        assert personas.NAME in persona.character, key  # she says {name}, not a name of her own
        assert persona.name in persona.prompt and personas.NAME not in persona.prompt, key


def test_the_default_is_vera_as_she_was_first_written(settings) -> None:
    vera = personas.load(personas.DEFAULT)
    assert vera.name == "Vera"
    assert vera.character.startswith("You are {name}, an AI assistant")
    assert vera.prompt.startswith("You are Vera, an AI assistant")
    assert "Be recognizably Vera without making every response a demonstration of Vera." in (
        vera.prompt
    )
    assert vera.lines["reminder"].startswith("Reminder: {title}")
    # With nothing of the family's laid over her, she is who the family meets.
    assert settings.persona == personas.DEFAULT and personas.active(settings) == vera


def test_a_new_name_reaches_all_of_her_character() -> None:
    juno = replace(personas.load(personas.DEFAULT), name="Juno")
    assert juno.prompt.startswith("You are Juno, an AI assistant") and "Vera" not in juno.prompt
    assert "Be recognizably Juno without making every response a demonstration of Juno." in (
        juno.prompt
    )


def test_the_family_s_name_for_her_is_her_name_but_never_the_plain_bot_s(settings) -> None:
    called = settings.model_copy(update={"persona_name": "Juno"})
    juno = personas.active(called)
    assert juno.name == "Juno" and juno.prompt.startswith("You are Juno, an AI assistant")
    assert juno.character == personas.load(personas.DEFAULT).character  # {name} is left in it
    assert personas.load(personas.DEFAULT).name == "Vera"  # what ships is untouched
    assert personas.active(called.model_copy(update={"persona": "none"})) is personas.PLAIN


def test_her_name_is_one_plain_line() -> None:
    """It goes wherever {name} is written, in her character and her lines, so a brace in it
    would be filled in again and a line break would break the line it is in."""
    assert Settings(_env_file=None, persona_name="  Captain Ada ").persona_name == "Captain Ada"
    assert Settings(_env_file=None, persona_name=f" {'J' * 40} ").persona_name == "J" * 40
    assert Settings(_env_file=None, persona_name="").persona_name == ""
    for bad in ("{name}", "Ju{no", "Ju}no", "Ju\nno", "Ju\rno", "Ju\tno", "Ju\u2028no", "J" * 41):
        with pytest.raises(ValueError):
            Settings(_env_file=None, persona_name=bad)


def test_the_family_s_words_are_laid_over_hers(settings) -> None:
    vera = personas.load(personas.DEFAULT)
    rewrite = PersonaRewrite(text="  You are {name}. Be very brief.\n")
    theirs = settings.model_copy(
        update={
            "persona_text": {personas.DEFAULT: rewrite},
            "voice_lines": {"reminder": "Psst: {title}.", "follow_up": ""},
        }
    )
    speaking = personas.active(theirs)
    assert speaking.character == "You are {name}. Be very brief."
    assert speaking.prompt == "You are Vera. Be very brief."  # their {name} is hers too
    assert speaking.lines["reminder"] == "Psst: {title}."
    assert speaking.lines["follow_up"] == vera.lines["follow_up"]  # an empty box is still hers
    assert speaking.name == "Vera" and speaking.key == personas.DEFAULT
    # What ships is untouched: restoring her original brings her back as she was.
    assert personas.load(personas.DEFAULT) == vera and vera.lines["reminder"] != "Psst: {title}."


def test_a_rewrite_is_laid_over_the_persona_it_rewrote_and_nobody_else(
    settings, monkeypatch
) -> None:
    """With a second persona beside her, the family's rewrite of Vera must not become hers."""
    brief = replace(personas.load(personas.DEFAULT), key="brief", character="You are {name}.")
    shipped = personas.load
    monkeypatch.setattr(personas, "load", lambda key: brief if key == "brief" else shipped(key))
    of_vera = {personas.DEFAULT: PersonaRewrite(text="You are {name}. Dry.")}
    as_brief = settings.model_copy(update={"persona": "brief", "persona_text": of_vera})
    assert personas.active(as_brief).character == "You are {name}."
    as_vera = settings.model_copy(update={"persona_text": of_vera})
    assert personas.active(as_vera).character == "You are {name}. Dry."
    both = {**of_vera, "brief": PersonaRewrite(text="You are {name}. Terse.")}
    assert personas.active(as_brief.model_copy(update={"persona_text": both})).character == (
        "You are {name}. Terse."
    )
    assert personas.active(as_vera.model_copy(update={"persona_text": both})).character == (
        "You are {name}. Dry."
    )


def test_a_rewrite_written_before_it_was_kept_per_persona_still_loads(monkeypatch) -> None:
    """It was one string, the rewrite of the only persona there was. A setting that fails to load
    takes every stored setting with it, so each shape it could have been saved in is still read,
    as hers."""
    hers = {personas.DEFAULT: PersonaRewrite(text="You are {name}. Dry.")}
    assert Settings(_env_file=None, persona_text="You are {name}. Dry.").persona_text == hers
    assert Settings(_env_file=None, persona_text={"vera": "You are {name}. Dry."}).persona_text == (
        hers
    )
    monkeypatch.setenv("PERSONA_TEXT", "You are {name}. Dry.")  # not JSON, and never was
    assert Settings(_env_file=None).persona_text == hers
    monkeypatch.setenv("PERSONA_TEXT", '{"Vera": {"text": "You are {name}. Dry."}}')
    assert Settings(_env_file=None).persona_text == hers
    monkeypatch.delenv("PERSONA_TEXT")
    blanks = ({"default": " "}, {"default": None}, {"default": {"text": ""}}, '{"default": null}')
    for nothing in (None, "", "  \n", {}, *blanks):
        assert Settings(_env_file=None, persona_text=nothing).persona_text == {}, nothing
    # A persona whose folder has gone is kept, unused, rather than breaking every setting.
    gone = Settings(_env_file=None, persona_text={"hal": {"text": "You are {name}.", "of": "x"}})
    assert gone.persona_text == {"hal": PersonaRewrite(text="You are {name}.", of="x")}
    assert personas.active(gone) == personas.load(personas.DEFAULT)


def test_a_setting_saved_before_she_had_a_folder_of_her_own_still_finds_her() -> None:
    """The default persona's folder was "vera". A setting that no longer loads would take every
    stored setting with it, the keys included, so the old value has to keep working."""
    for written in ("vera", " Vera ", "VERA", "default", "Default "):
        assert Settings(_env_file=None, persona=written).persona == personas.DEFAULT, written
    assert Settings(_env_file=None, persona=" None ").persona == personas.NONE
    with pytest.raises(ValueError, match="the choices are default, none"):
        Settings(_env_file=None, persona="hal")


def test_none_is_plain_whatever_the_family_wrote(settings) -> None:
    plain = settings.model_copy(
        update={
            "persona": "none",
            "persona_text": {personas.DEFAULT: PersonaRewrite(text="You are Zorblax.")},
            "voice_lines": {"reminder": "Psst: {title}."},
        }
    )
    assert personas.active(plain) is personas.PLAIN
    assert personas.load(personas.NONE) is personas.PLAIN
    assert personas.PLAIN.character == personas.PLAIN.prompt == "" and not personas.PLAIN.lines
    assert personas.PLAIN.name == "FamilyDB"


def test_only_a_persona_there_is_a_folder_for_is_loaded() -> None:
    """Loading is by exact key; an old or loosely written one is the setting's to tidy first."""
    for key in ("hal", "vera", "Default", "", "..", "../agent/prompts", "__pycache__"):
        with pytest.raises(LookupError):
            personas.load(key)
    with pytest.raises(LookupError):
        personas.load("default/character.md")


def test_nobody_can_change_her_by_reading_her() -> None:
    """She is loaded once and shared, so she cannot be changed in place by whoever reads her."""
    vera = personas.load(personas.DEFAULT)
    with pytest.raises(TypeError):
        vera.lines["reminder"] = "Changed."  # type: ignore[index]
    with pytest.raises(AttributeError):
        vera.name = "Hal"  # type: ignore[misc]
    assert personas.load(personas.DEFAULT).lines["reminder"].startswith("Reminder: {title}")
