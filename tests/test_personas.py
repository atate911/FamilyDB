"""The persona layer: who the assistant is, as one object, and the one in force."""

import pytest

from familydb import personas


def test_every_persona_ships_whole() -> None:
    """A folder is a persona when it names her; her character says who she is."""
    assert "vera" in personas.available()
    for key in personas.available():
        persona = personas.load(key)
        assert persona.key == key and persona.name.strip(), key
        assert persona.character and persona.name in persona.character, key


def test_vera_is_who_the_family_meets(settings) -> None:
    vera = personas.load("vera")
    assert vera.name == "Vera" and vera.character.startswith("You are Vera")
    assert vera.lines["reminder"].startswith("Reminder: {title}")
    # The default, with nothing of the family's laid over her, is her as she ships.
    assert personas.active(settings) == vera


def test_the_family_s_words_are_laid_over_hers(settings) -> None:
    vera = personas.load("vera")
    theirs = settings.model_copy(
        update={
            "persona_text": "  You are Vera. Be very brief.\n",
            "voice_lines": {"reminder": "Psst: {title}.", "follow_up": ""},
        }
    )
    speaking = personas.active(theirs)
    assert speaking.character == "You are Vera. Be very brief."
    assert speaking.lines["reminder"] == "Psst: {title}."
    assert speaking.lines["follow_up"] == vera.lines["follow_up"]  # an empty box is still hers
    assert speaking.name == "Vera" and speaking.key == "vera"
    # What ships is untouched: restoring her original brings her back as she was.
    assert personas.load("vera") == vera and vera.lines["reminder"] != "Psst: {title}."


def test_none_is_plain_whatever_the_family_wrote(settings) -> None:
    plain = settings.model_copy(
        update={
            "persona": "none",
            "persona_text": "You are Zorblax.",
            "voice_lines": {"reminder": "Psst: {title}."},
        }
    )
    assert personas.active(plain) is personas.PLAIN
    assert personas.load(personas.NONE) is personas.PLAIN
    assert personas.PLAIN.character == "" and not personas.PLAIN.lines
    assert personas.PLAIN.name == "FamilyDB"


def test_only_a_persona_there_is_a_folder_for_is_loaded() -> None:
    for key in ("hal", "Vera", "", "..", "../agent/prompts", "__pycache__", "vera/character.md"):
        with pytest.raises(LookupError):
            personas.load(key)


def test_nobody_can_change_her_by_reading_her() -> None:
    """She is loaded once and shared, so she cannot be changed in place by whoever reads her."""
    vera = personas.load("vera")
    with pytest.raises(TypeError):
        vera.lines["reminder"] = "Changed."  # type: ignore[index]
    with pytest.raises(AttributeError):
        vera.name = "Hal"  # type: ignore[misc]
    assert personas.load("vera").lines["reminder"].startswith("Reminder: {title}")
