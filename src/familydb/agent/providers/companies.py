"""The companies FamilyDB can ask, as data: what each is called, where its key and models live, and
which model names are its own. SDK-free.

A company is one `Company`. The three that ship with a module of their own are `BUILT_IN`; any
other (OpenRouter, a service the family has an account with) is defined in the settings as a
`CompanyDef` and spoken to by the generic adapter (`chat.py`). Everything that used to keep its own
table of the three (a label on a page, a line in a notice, the setting a key is stored under) asks
here, so a fourth company is one definition and not a change in a dozen files.

The added ones are read from the settings given, or, where a caller has none to hand (a notice's
wording), from those `use` last put in force: `App` does it whenever the settings are reloaded.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from familydb.agent.providers import prices
from familydb.base.config import BUILT_IN_COMPANIES, MODEL_FIELDS, CompanyDef, CompanyModels


@dataclass(frozen=True)
class Company:
    slug: str
    label: str  # in a picker: "Google"
    named: str  # in a sentence or a notice: "Google Gemini"
    status: str  # on the Status page: "Claude (Anthropic)"
    line: str = ""  # what to say of it where it is offered
    key_start: str = ""  # what its keys begin with, to catch a pasted word
    key_setting: str = ""  # the setting its key is stored under (built in)
    env_name: str = ""  # the environment variable the same key may come from
    owns: tuple[str, ...] = ()  # prefixes of the model names that are its own
    litellm: str = ""  # LiteLLM's name for the company
    openrouter: str = ""  # the maker's name in OpenRouter's model ids
    defined: CompanyDef | None = None  # set for a company the settings define

    @property
    def built_in(self) -> bool:
        return self.defined is None

    def key(self, settings: Any) -> str | None:
        """Its API key, wherever it is kept."""
        if self.defined is None:
            return getattr(settings, self.key_setting, None) or None
        return (getattr(settings, "company_keys", None) or {}).get(self.slug) or None

    def under(self, settings: Any) -> CompanyModels:
        """Its models as the environment says (built in) or its definition (added): what the
        page's own are laid over."""
        if self.defined is not None:
            return self.defined.own_models
        env = getattr(settings, "env_company_models", None) or {}
        return env.get(self.slug) or CompanyModels()

    def models(self, settings: Any) -> CompanyModels:
        """Its models in force: the page's (`Settings.company_models`) over `under`."""
        page = (getattr(settings, "company_models", None) or {}).get(self.slug)
        return page.laid_over(self.under(settings)) if page else self.under(settings)

    def chat_model(self, settings: Any) -> str:
        return self.models(settings).model

    def worker_model(self, settings: Any) -> str:
        found = self.models(settings)
        return found.worker_model or found.model

    def level_model(self, settings: Any, level: str) -> str:
        """The model the family named for this company at a level above everyday, or ""."""
        found = self.models(settings)
        return {"better": found.better_model, "best": found.best_model}.get(level, "")

    def box(self, field: str) -> str:
        """The form box for one of its models (`MODEL_FIELDS`): `openai_model`,
        `anthropic_worker_model`, the one name a page, a judgement and the Status page agree on."""
        return f"{self.slug}_{field}"

    def boxes_naming(self, settings: Any, name: str) -> list[str]:
        """The boxes whose model in force is this one."""
        found = self.models(settings)
        return [
            self.box(field)
            for field in MODEL_FIELDS
            if getattr(found, field, "").lower() == name.lower()
        ]

    def known_models(self) -> tuple[str, ...]:
        """The model names its definition knows; a built-in company is known by prefix instead."""
        return self.defined.models if self.defined else ()


OPENAI = Company(
    slug="openai",
    label="OpenAI",
    named="OpenAI",
    status="OpenAI",
    line="The least expensive by far for what FamilyDB does, so it is the one it starts with.",
    key_start="sk-",
    key_setting="openai_api_key",
    env_name="OPENAI_API_KEY",
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
    owns=("gemini",),
    litellm="gemini",
    openrouter="google",
)

# In the order a page lists them.
BUILT_IN: tuple[Company, ...] = (OPENAI, ANTHROPIC, GEMINI)
# In the order a spare is looked for, so the same one is chosen every time. Added companies follow,
# in the order they were added.
SPARE_ORDER: tuple[str, ...] = BUILT_IN_COMPANIES
# The same, as companies.
SPARE_COMPANIES: tuple[Company, ...] = tuple(
    company for slug in SPARE_ORDER for company in BUILT_IN if company.slug == slug
)

# The company asked when the settings name one that is not defined.
DEFAULT = "openai"

_ADDED: tuple[CompanyDef, ...] = ()


def use(defined: Iterable[CompanyDef]) -> None:
    """Put the companies the settings define in force, with the prices their admin typed
    (`App` at start and whenever the settings are reloaded; a test to reset)."""
    global _ADDED
    _ADDED = tuple(defined)
    prices.own(
        {
            company.slug: {
                price.name.lower(): prices.Price(
                    input=price.input,
                    output=price.output,
                    cached=price.input if price.cached is None else price.cached,
                    search=0.0,
                )
                for price in company.prices
            }
            for company in _ADDED
        }
    )


def added(settings: Any = None) -> tuple[Company, ...]:
    """The companies the settings define (those in force when none are given), in the order they
    were added."""
    defined = _ADDED if settings is None else tuple(getattr(settings, "companies", ()) or ())
    return tuple(_from_definition(one) for one in defined)


def _from_definition(one: CompanyDef) -> Company:
    return Company(slug=one.slug, label=one.label, named=one.label, status=one.label, defined=one)


def built_in(slug: str | None) -> Company | None:
    return next((company for company in BUILT_IN if company.slug == slug), None)


def get(slug: str | None, settings: Any = None) -> Company | None:
    return built_in(slug) or next(
        (company for company in added(settings) if company.slug == slug), None
    )


def every(settings: Any = None) -> tuple[Company, ...]:
    """Every company in the order a page lists them: the built-in ones, then the added."""
    return (*BUILT_IN, *added(settings))


def slugs(settings: Any = None) -> tuple[str, ...]:
    """Every company, in the order a spare is looked for."""
    return (*SPARE_ORDER, *(company.slug for company in added(settings)))


def label(slug: str | None, settings: Any = None) -> str:
    company = get(slug, settings)
    return company.label if company else str(slug or "")


def named(slug: str | None, settings: Any = None) -> str:
    """The company as a sentence says it; an unfamiliar slug is said as it is."""
    company = get(slug, settings)
    return company.named if company else str(slug or "")


def status_name(slug: str | None, settings: Any = None) -> str:
    """The company as the Status page says it."""
    company = get(slug, settings)
    return company.status if company else str(slug or "")


def box_of(name: str, settings: Any = None) -> tuple[Company, str] | None:
    """The company and model field a form box names, or None for a box that is not one."""
    for company in every(settings):
        for field in MODEL_FIELDS:
            if company.box(field) == name:
                return company, field
    return None


def box_value(name: str, settings: Any) -> str:
    """The model in force in this box, or "" for a box that is not one."""
    found = box_of(name, settings)
    return getattr(found[0].models(settings), found[1], "") if found else ""


def models_with(
    settings: Any, stored: Mapping[str, Any] | None, boxes: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    """The page's `company_models` (as stored) with these boxes set. A name that is what the
    environment or the definition already says is kept as "", and a company with nothing said is
    left out, so what is stored is only what the family changed."""
    kept = {
        slug: {str(key): str(value) for key, value in entry.items()}
        for slug, entry in (stored or {}).items()
        if isinstance(entry, Mapping)
    }
    for box, value in boxes.items():
        found = box_of(box, settings)
        if found is None:
            continue
        company, field = found
        name = value.strip()
        entry = kept.setdefault(company.slug, {})
        entry[field] = "" if name == getattr(company.under(settings), field) else name
    return {slug: entry for slug, entry in kept.items() if any(entry.values())}


def owner(model: str | None, settings: Any = None) -> str | None:
    """Whose model this name is, or None; only to say who answered a logged call. An added
    company owns the names its definition knows."""
    lowered = (model or "").lower()
    for company in BUILT_IN:
        if any(lowered.startswith(prefix) for prefix in company.owns):
            return company.slug
    for company in added(settings):
        if lowered and lowered in (name.lower() for name in company.known_models()):
            return company.slug
    return None


@dataclass(frozen=True)
class Template:
    """A starting point for adding a company: the values that are the same for everyone who uses
    that service, so adding it needs only a key and a model."""

    key: str
    label: str
    line: str  # what to say of it, including where the family's words go
    base_url: str
    key_start: str
    reasoning_fields: tuple[str, ...]
    extra_body: dict[str, Any]
    # Where a person finds the service's models and its keys (names in web/links.py).
    models_link: str
    keys_link: str
    # A path that answers only to a key that is good, when the list of models is public and so
    # proves nothing about the key (OpenRouter's `/key`).
    key_path: str = ""


OPENROUTER = Template(
    key="openrouter",
    label="OpenRouter",
    line=(
        "One key, hundreds of models from many companies (DeepSeek, Kimi, GLM, Qwen, MiniMax and "
        "more), paid for at OpenRouter. Your messages pass through OpenRouter as well as the "
        "company that answers; it is asked to use only companies that keep and train on nothing."
    ),
    base_url="https://openrouter.ai/api/v1",
    key_start="sk-or-",
    reasoning_fields=("reasoning_details", "reasoning"),
    # Only providers that do not collect what they are sent, and only ones that take every
    # parameter we send (a model that cannot use tools is refused, not quietly run without).
    extra_body={"provider": {"data_collection": "deny", "require_parameters": True}},
    models_link="openrouter_models",
    keys_link="openrouter_keys",
    key_path="/key",
)
TEMPLATES: dict[str, Template] = {OPENROUTER.key: OPENROUTER}


def options(slug: str | None, settings: Any = None) -> Any:
    """What the family said of this company on the models page (`config.CompanyOptions`)."""
    from familydb.base.config import CompanyOptions

    given = getattr(settings, "company_options", None) or {}
    return given.get(slug or "", CompanyOptions())


def allowed(slug: str | None, settings: Any = None) -> bool:
    """Whether the company may be asked at all."""
    return bool(options(slug, settings).allowed)


def may_stand_in(slug: str | None, settings: Any = None) -> bool:
    """Whether it may answer when the company chosen cannot. The family's word on the page; else,
    for the three built in, the one switch that used to say it for them all; for one added, its own
    definition, still behind that switch."""
    said = options(slug, settings).stand_in
    if said is not None:
        return bool(said)
    company = get(slug, settings)
    if company is None:
        return False
    fallback = bool(getattr(settings, "env_stand_in", True))
    return fallback if company.defined is None else bool(company.defined.stand_in and fallback)


def monthly_limit(slug: str | None, settings: Any = None) -> float | None:
    """The most the family has said to spend on the company in a month, or None."""
    return options(slug, settings).monthly_limit
