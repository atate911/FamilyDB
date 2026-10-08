"""One choice for each thing the family has Vera do (agent/uses.py): the page's choices laid over
the older settings, which still say the answer for any use nobody chose."""

import pytest

from familydb.agent import gateway, uses
from familydb.agent.providers import catalog
from familydb.config import USE_KEYS


def keyed(settings, **more):
    """Claude's key (the fixture's), OpenAI's and Google's, so any company can be chosen."""
    return settings.model_copy(
        update={"openai_api_key": "sk-o", "gemini_api_key": "g-1", "provider": "openai", **more}
    )


def answered(settings, kind):
    provider, model = gateway.answering(settings, kind)
    return provider.name, model


# -- reading a choice -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, form",
    [
        ("", "default"),
        (None, "default"),
        ("off", "off"),
        ("same:chat", "same"),
        ("same:nonsense", "default"),
        ("openai:gpt-6-sol", "model"),
        ("openrouter:vendor/model:free", "model"),  # a model name may hold a colon
        ("nocolon", "default"),
        (":model", "default"),
    ],
)
def test_a_stored_choice_is_read_and_anything_else_is_the_default(text, form):
    assert uses.parse(text).form == form
    assert uses.parse("openrouter:vendor/model:free").model == "vendor/model:free"
    assert str(uses.parse("openai:gpt-6-sol")) == "openai:gpt-6-sol"


def test_every_kind_belongs_to_exactly_one_use():
    covered = [kind for use in uses.USES for kind in use.kinds]
    assert len(covered) == len(set(covered))
    assert set(gateway.KINDS) <= set(covered)
    assert {gateway.LISTEN, gateway.LOOK} <= set(covered)
    assert tuple(use.key for use in uses.USES) == USE_KEYS


def test_the_page_names_the_use_that_is_spelled_once_and_the_rest_have_labels():
    from familydb import happening

    assert uses.BY_KEY["onnear"].label == happening.NAME
    assert all(use.label and use.line for use in uses.USES)


def test_a_value_stored_by_another_version_never_stops_the_settings(settings):
    odd = settings.model_copy(update={})
    from familydb.config import Settings

    loaded = Settings(
        _env_file=None, model_choices={"chat": "openai:x", "future": "x", "digest": 5, "look": " "}
    )
    assert loaded.model_choices == {"chat": "openai:x"}
    assert odd.model_choices == {}


# -- with nothing chosen, nothing changes ----------------------------------------------------


def test_with_nothing_chosen_each_use_is_answered_as_the_older_settings_say(settings):
    live = keyed(settings, chat_level="everyday", lookup_level="better")
    assert uses.resolve(live, "chat").source == "default"
    assert answered(live, "chat") == ("openai", "gpt-6-luna")
    assert answered(live, "digest") == ("openai", "gpt-6-luna")
    assert answered(live, "choose") == ("openai", "gpt-6-astra")  # best, as choose_level says
    assert answered(live, "enrich") == ("openai", "gpt-6-sol")  # lookup_level better
    assert answered(live, "scout") == answered(live, "enrich")
    assert uses.resolve(live, "judge").off  # judgements are off until the family turns them on


def test_a_use_that_is_switched_off_by_an_older_toggle_defaults_to_off(settings):
    live = keyed(settings, choosing=False, voice_notes=False, photos=False, judgements=True)
    assert [use for use in ("choose", "hear", "look") if not uses.on(live, use)] == [
        "choose",
        "hear",
        "look",
    ]
    assert uses.on(live, "judge")
    assert not gateway.can_ask(live, "choose")


def test_the_overlay_hands_the_settings_back_untouched_when_nothing_was_said(settings):
    live = keyed(settings)
    for kind in (*gateway.KINDS, gateway.LISTEN, gateway.LOOK):
        assert uses.overlay(live, kind).settings is live, kind


# -- choosing --------------------------------------------------------------------------------


def test_a_chosen_model_answers_its_use_and_the_digest_follows_it(settings):
    live = keyed(settings, model_choices={"chat": "anthropic:claude-sonnet-5"})
    assert answered(live, "chat") == ("anthropic", "claude-sonnet-5")
    assert answered(live, "retry") == ("anthropic", "claude-sonnet-5")  # the same use
    assert answered(live, "digest") == ("anthropic", "claude-sonnet-5")  # same strength: same model
    chosen = uses.resolve(live, "chat")
    assert (chosen.source, chosen.level, chosen.explicit) == ("chosen", "better", True)
    assert uses.resolve(live, "digest").followed == "chat"


def test_choosing_suggestions_goes_to_the_chat_company_at_its_own_strength(settings):
    live = keyed(settings, choosing=True, model_choices={"chat": "anthropic:claude-haiku-4-5"})
    # Best, as before, but on the company the chat was chosen to.
    assert answered(live, "choose") == ("anthropic", "claude-opus-5")


def test_a_model_nobody_listed_can_be_chosen_and_stands_in_at_everyday(settings):
    live = keyed(settings, model_choices={"chat": "openai:gpt-9-secret"})
    assert answered(live, "chat") == ("openai", "gpt-9-secret")
    assert uses.resolve(live, "chat").level == catalog.EVERYDAY


def test_a_use_can_follow_another_and_a_loop_of_them_is_the_default(settings):
    live = keyed(
        settings,
        model_choices={"chat": "anthropic:claude-opus-5", "lookup": "same:chat"},
    )
    assert answered(live, "enrich") == ("anthropic", "claude-opus-5")
    loop = keyed(settings, model_choices={"chat": "same:digest", "digest": "same:chat"})
    assert uses.resolve(loop, "chat").source == "default"
    assert answered(loop, "chat") == ("openai", "gpt-6-luna")


def test_the_lookups_follow_what_they_were_chosen_to_and_so_do_photos(settings):
    live = keyed(settings, model_choices={"lookup": "gemini:gemini-3.8-flash"})
    assert answered(live, "enrich") == ("gemini", "gemini-3.8-flash")
    assert answered(live, "find_feeds") == ("gemini", "gemini-3.8-flash")  # What's going down?
    assert uses.resolve(live, "look").followed == "lookup"
    assert uses.overlay(live, gateway.LOOK).settings.worker_provider == "gemini"


def test_off_stops_a_use_that_can_be_off_and_is_ignored_for_one_that_cannot(settings):
    live = keyed(settings, model_choices={"choose": "off", "chat": "off", "hear": "off"})
    assert not uses.on(live, "choose") and not gateway.can_ask(live, "choose")
    assert uses.on(live, "chat")  # answering the family cannot be turned off
    assert not uses.on(live, "hear")
    on_again = keyed(settings, choosing=False, model_choices={"choose": "openai:gpt-6-sol"})
    assert uses.on(on_again, "choose")  # a choice made on the page beats the older switch
    assert answered(on_again, "choose") == ("openai", "gpt-6-sol")


def test_a_company_that_is_not_there_is_the_default(settings):
    live = keyed(settings, model_choices={"chat": "nobody:anything"})
    assert uses.resolve(live, "chat").source == "default"
    assert answered(live, "chat") == ("openai", "gpt-6-luna")


def test_a_chosen_voice_model_is_what_hears(settings):
    live = keyed(settings, model_choices={"hear": "openai:whisper-1"})
    overlaid = uses.overlay(live, gateway.LISTEN).settings
    assert (
        overlaid.transcribe_provider == "openai" and overlaid.openai_transcribe_model == "whisper-1"
    )
    assert gateway.can_listen(live)
    claude_only = keyed(settings, openai_api_key=None, gemini_api_key=None)
    assert not gateway.can_listen(claude_only)  # Claude hears nothing


def test_each_use_thinks_as_much_as_the_page_said(settings):
    live = keyed(settings, use_effort={"chat": "high", "lookup": "low"})
    assert uses.overlay(live, "chat").settings.effort == "high"
    assert uses.overlay(live, "enrich").settings.worker_effort == "low"
    assert uses.overlay(live, "digest").settings is live  # nothing said for it


# -- the stand-in --------------------------------------------------------------------------------


def test_a_stand_in_answers_at_the_level_of_the_model_chosen(settings, registry, ctx, monkeypatch):
    seen = {}
    monkeypatch.setattr(gateway, "run_turn", lambda **kwargs: seen.update(kwargs) or "done")
    live = keyed(settings, model_choices={"chat": "anthropic:claude-opus-5"})
    gateway.ask("chat", settings=live, registry=registry, ctx=ctx, current=["hi"])
    assert seen["provider"].name == "anthropic" and seen["model"] == "claude-opus-5"
    assert seen["level"] == "best"  # the level of Opus: what a stand-in company is asked at
    assert seen["fallback"] is not None and seen["fallback"].name != "anthropic"
    # Nothing chosen: the older setting's strength, as before.
    seen.clear()
    plain = keyed(settings, chat_level="better")
    gateway.ask("chat", settings=plain, registry=registry, ctx=ctx, current=["hi"])
    assert seen["level"] == "better" and seen["provider"].name == "openai"
