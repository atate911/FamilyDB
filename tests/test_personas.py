"""The persona layer: who the assistant is, as one object, and the one in force."""

import json
import re
from dataclasses import replace

import pytest

from familydb import personas
from familydb.agent import gateway, providers
from familydb.agent.history import HistoryTurn
from familydb.agent.prompt import JOB_HEADER, PERSONA_HEADER, load_system_prompt
from familydb.agent.render import render_user_turn
from familydb.config import PersonaRewrite, Settings


def test_every_persona_ships_whole() -> None:
    """A folder is a persona when it names her, and her name is written there and only there."""
    assert personas.DEFAULT in personas.available()
    for key in personas.available():
        persona = personas.load(key)
        assert persona.key == key and persona.name.strip(), key
        assert personas.NAME in persona.character, key  # she says {name}, not a name of her own
        assert not re.search(rf"\b{re.escape(persona.name)}\b", persona.character, re.I), key
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


def test_the_brief_persona_is_vera_in_fewer_words() -> None:
    """Fitted to a family's chat, at about a quarter of the first one's length. She never names
    herself outright, so a name the family give her is the only one she has."""
    brief = personas.load("brief")
    assert brief.name == "Vera" and brief.listed_as == "Vera, in brief"
    assert brief.character.startswith("You are {name}, an AI with a feminine identity (she/her).")
    assert len(brief.character) < 4_000
    assert not re.search(r"\bVera\b", brief.character, re.IGNORECASE)
    assert personas.DEFAULT == "default"  # the family still meet her as first written


def test_no_character_names_a_tool(registry) -> None:
    """A character is about how she talks. What can be done is the tools' and the job's, which
    hold whoever she is, and a family can rewrite her. A tool whose name is an everyday word
    ("now", "suggest") counts as named only when it is written as code."""
    for key in personas.available():
        character = personas.load(key).character
        for tool in registry.names():
            named = rf"\b{tool}\b" if "_" in tool else f"`{tool}`"
            assert not re.search(named, character), (key, tool)


@pytest.mark.parametrize("key", personas.available())
def test_she_changes_only_the_persona_part_of_the_request(
    key, conn, settings, family, registry, clock
) -> None:
    """Whoever she is, the model is given the same tools, the same job, the same family and
    ideas and the same conversation as with none: she changes how things are said, never what
    is done."""

    def request(persona: str):
        return gateway.build_request(
            "chat",
            conn=conn,
            settings=settings.model_copy(update={"persona": persona}),
            registry=registry,
            provider=providers.build("anthropic", settings, api=object()),
            current=render_user_turn("Sam", "what should we do?", clock),
            history=[HistoryTurn("user", "[Sam] hello"), HistoryTurn("assistant", "Hi.")],
        ).request

    hers, plain = request(key), request(personas.NONE)
    assert hers.tools == plain.tools
    assert hers.system[1] == plain.system[1]
    assert hers.messages == plain.messages
    told = PERSONA_HEADER + personas.load(key).prompt + JOB_HEADER + load_system_prompt()
    assert hers.system[0].text == told
    assert plain.system[0].text == load_system_prompt()
    # And nothing else: with her first block swapped for none's, it is none's request.
    assert replace(hers, system=[plain.system[0], *hers.system[1:]]) == plain


def test_a_new_name_reaches_all_of_her_character() -> None:
    juno = replace(personas.load(personas.DEFAULT), name="Juno")
    assert juno.prompt.startswith("You are Juno, an AI assistant") and "Vera" not in juno.prompt
    assert "Be recognizably Juno without making every response a demonstration of Juno." in (
        juno.prompt
    )


def test_a_label_says_which_of_her_this_is_with_her_name_in_it(settings) -> None:
    """Two personas may share a name, so the page lists each by her label."""
    vera = personas.load(personas.DEFAULT)
    assert vera.label == "{name}, as first written" and vera.listed_as == "Vera, as first written"
    assert replace(vera, name="Juno").listed_as == "Juno, as first written"
    called = settings.model_copy(update={"persona": "brief", "persona_name": "Juno"})
    assert personas.active(called).listed_as == "Juno, in brief"
    assert personas.PLAIN.label == personas.NAME and personas.PLAIN.listed_as == "FamilyDB"


def _loaded(tmp_path, monkeypatch, manifest: str, lines: str | None = None) -> personas.Persona:
    """A persona called "juno" with this manifest, and these lines if any, as the only folder
    there is, loaded past the cache so each is read as written."""
    folder = tmp_path / "juno"
    folder.mkdir(parents=True)
    (folder / personas.MANIFEST).write_text(manifest, "utf-8")
    (folder / personas.CHARACTER).write_text("You are {name}.", "utf-8")
    if lines is not None:
        (folder / personas.LINES).write_text(lines, "utf-8")
    monkeypatch.setattr(personas.resources, "files", lambda _package: tmp_path)
    return personas.load.__wrapped__("juno")


def test_a_folder_may_go_without_a_label_and_is_listed_by_her_name(tmp_path, monkeypatch) -> None:
    for number, manifest in enumerate(('name = "Juno"', 'name = "Juno"\nlabel = " "')):
        juno = _loaded(tmp_path / str(number), monkeypatch, manifest)
        assert juno.label == personas.NAME and juno.listed_as == "Juno", manifest
    labelled = 'name = "Juno"\nlabel = " {name}, the third "'
    assert _loaded(tmp_path / "labelled", monkeypatch, labelled).listed_as == "Juno, the third"


def test_a_label_with_any_brace_but_her_name_is_refused(tmp_path, monkeypatch) -> None:
    """Only {name} is filled in, so any other brace would be shown to the family as written."""
    labels = ("{title}, in brief", "{name, in brief", "{name}}", "{{name}}", "{}", "{name!r}", 3)
    refused = re.escape("her label is words, with no brace but {name}")
    for number, label in enumerate(labels):
        manifest = f'name = "Juno"\nlabel = {json.dumps(label)}'
        with pytest.raises(ValueError, match=refused):
            _loaded(tmp_path / str(number), monkeypatch, manifest)


def test_a_line_may_be_one_wording_or_a_list_of_them(tmp_path, monkeypatch) -> None:
    """A list is kept as a tuple, as the family's are kept as a list: a string is one wording."""
    lines = 'done = "Done."\nfollow_up = ["How was {plan}?", "{plan}: again?"]\n'
    juno = _loaded(tmp_path, monkeypatch, 'name = "Juno"', lines)
    assert juno.lines == {"done": "Done.", "follow_up": ("How was {plan}?", "{plan}: again?")}
    for number, wrong in enumerate(("done = 3", 'done = ["Done.", 3]', "done = {a = 1}")):
        with pytest.raises(ValueError, match="done is a wording, or a list of wordings"):
            _loaded(tmp_path / str(number), monkeypatch, 'name = "Juno"', wrong)


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


def test_the_family_s_notes_follow_her_character_whoever_she_is(settings, monkeypatch) -> None:
    """They are the family's words, not a copy of hers, so they go with any persona, after her
    character and under a header that says whose they are, with her name filled in."""
    noted = settings.model_copy(update={"persona_notes": "  No emoji. {name} calls Mia Captain.\n"})
    vera = personas.active(noted)
    assert vera.notes == "No emoji. {name} calls Mia Captain."
    assert vera.prompt == (
        personas.load(personas.DEFAULT).prompt
        + "\n\n## The family's own notes on how you talk\n\nNo emoji. Vera calls Mia Captain."
    )
    assert personas.active(settings).prompt == personas.load(personas.DEFAULT).prompt
    brief = replace(personas.load(personas.DEFAULT), key="brief", character="You are {name}.")
    shipped = personas.load
    monkeypatch.setattr(personas, "load", lambda key: brief if key == "brief" else shipped(key))
    as_brief = noted.model_copy(update={"persona": "brief", "persona_name": "Juno"})
    assert personas.active(as_brief).prompt == (
        "You are Juno.\n\n## The family's own notes on how you talk\n\n"
        "No emoji. Juno calls Mia Captain."
    )


def test_notes_are_at_most_a_thousand_characters() -> None:
    assert Settings(_env_file=None, persona_notes="x" * 1_000).persona_notes == "x" * 1_000
    with pytest.raises(ValueError):
        Settings(_env_file=None, persona_notes="x" * 1_001)


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
    with pytest.raises(ValueError, match="the choices are brief, default, none"):
        Settings(_env_file=None, persona="hal")


def test_none_is_plain_whatever_the_family_wrote(settings) -> None:
    plain = settings.model_copy(
        update={
            "persona": "none",
            "persona_text": {personas.DEFAULT: PersonaRewrite(text="You are Zorblax.")},
            "persona_notes": "No emoji, ever.",
            "voice_lines": {"reminder": "Psst: {title}."},
        }
    )
    assert personas.active(plain) is personas.PLAIN and not personas.PLAIN.notes
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
