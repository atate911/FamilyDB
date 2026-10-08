"""The companies FamilyDB can ask, as data: what each is called, where its key and models live in
the settings, and which model names are its own. SDK-free.

A company is one `Company`. The three that ship with a module of their own are `BUILT_IN`; any
other (OpenRouter, a company the family has an account with) is defined in the settings and spoken
to by the generic adapter (`chat.py`). Everything that used to keep its own table of
the three (a label on a page, a line in a notice, the setting a key is stored under) asks here, so
a fourth company is one definition and not a change in a dozen files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    slug: str
    label: str  # in a picker: "Google"
    named: str  # in a sentence or a notice: "Google Gemini"
    status: str  # on the Status page: "Claude (Anthropic)"
    line: str  # what to say of it where it is offered
    key_start: str  # what its keys begin with, to catch a pasted word
    key_setting: str  # the setting its key is stored under
    env_name: str  # the environment variable the same key may come from
    chat_setting: str  # the setting naming its everyday chat model
    worker_setting: str  # and its everyday lookup model
    better_setting: str  # and the family's own better and best models, empty for the lineup's
    best_setting: str
    owns: tuple[str, ...]  # prefixes of the model names that are its own
    litellm: str  # LiteLLM's name for the company
    openrouter: str  # the maker's name in OpenRouter's model ids

    def level_setting(self, level: str) -> str | None:
        return {"better": self.better_setting, "best": self.best_setting}.get(level)


OPENAI = Company(
    slug="openai",
    label="OpenAI",
    named="OpenAI",
    status="OpenAI",
    line="The least expensive by far for what FamilyDB does, so it is the one it starts with.",
    key_start="sk-",
    key_setting="openai_api_key",
    env_name="OPENAI_API_KEY",
    chat_setting="openai_model",
    worker_setting="openai_worker_model",
    better_setting="openai_better_model",
    best_setting="openai_best_model",
    owns=("gpt", "o1", "o3", "o4", "chatgpt"),
    litellm="openai",
    openrouter="openai",
)
ANTHROPIC = Company(
    slug="anthropic",
    label="Anthropic",
    named="Anthropic",
    status="Claude (Anthropic)",
    line="Claude. Several times dearer a message with the model it starts on.",
    key_start="sk-ant-",
    key_setting="anthropic_api_key",
    env_name="ANTHROPIC_API_KEY",
    chat_setting="anthropic_model",
    worker_setting="worker_model",  # the first, so unprefixed
    better_setting="anthropic_better_model",
    best_setting="anthropic_best_model",
    owns=("claude",),
    litellm="anthropic",
    openrouter="anthropic",
)
GEMINI = Company(
    slug="gemini",
    label="Google",
    named="Google Gemini",
    status="Google Gemini",
    line="Gemini, from Google. In between on price.",
    key_start="AIza",
    key_setting="gemini_api_key",
    env_name="GEMINI_API_KEY",
    chat_setting="gemini_model",
    worker_setting="gemini_worker_model",
    better_setting="gemini_better_model",
    best_setting="gemini_best_model",
    owns=("gemini",),
    litellm="gemini",
    openrouter="google",
)

# In the order a page lists them.
BUILT_IN: tuple[Company, ...] = (OPENAI, ANTHROPIC, GEMINI)
# In the order a spare is looked for, so the same one is chosen every time.
SPARE_ORDER: tuple[str, ...] = ("anthropic", "openai", "gemini")


# The same, as companies.
SPARE_COMPANIES: tuple[Company, ...] = tuple(
    company for slug in SPARE_ORDER for company in BUILT_IN if company.slug == slug
)


def built_in(slug: str | None) -> Company | None:
    return next((company for company in BUILT_IN if company.slug == slug), None)


def get(slug: str | None) -> Company | None:
    return built_in(slug)


def slugs() -> tuple[str, ...]:
    """Every company, in the order a spare is looked for."""
    return SPARE_ORDER


def label(slug: str | None) -> str:
    company = get(slug)
    return company.label if company else str(slug or "")


def named(slug: str | None) -> str:
    """The company as a sentence says it; an unfamiliar slug is said as it is."""
    company = get(slug)
    return company.named if company else str(slug or "")


def owner(model: str | None) -> str | None:
    """Whose model this name is, or None; only to say who answered a logged call."""
    lowered = (model or "").lower()
    for company in BUILT_IN:
        if any(lowered.startswith(prefix) for prefix in company.owns):
            return company.slug
    return None
