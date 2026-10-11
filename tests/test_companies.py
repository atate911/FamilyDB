"""The registry of companies (agent/providers/companies.py): each fact about a company is written
once, and what it names exists."""

import importlib
import re
import tokenize
from pathlib import Path

import pytest

from familydb.agent.providers import catalog, companies, prices
from familydb.base.config import Settings


@pytest.mark.parametrize("company", companies.BUILT_IN, ids=lambda company: company.slug)
def test_a_built_in_company_has_a_module_and_the_settings_it_names(company):
    importlib.import_module(f"familydb.agent.providers.{company.slug}")
    fields = Settings.model_fields
    for name in (company.key_setting, company.chat_setting, company.worker_setting):
        assert name in fields, f"{company.slug}: {name} is not a setting"
    for name in (company.better_setting, company.best_setting):
        assert name in fields


def test_every_company_is_looked_for_as_a_spare_once():
    assert sorted(companies.SPARE_ORDER) == sorted(company.slug for company in companies.BUILT_IN)
    assert [company.slug for company in companies.SPARE_COMPANIES] == list(companies.SPARE_ORDER)


def test_the_lineup_and_the_prices_name_only_companies_that_exist():
    known = {company.slug for company in companies.BUILT_IN}
    assert set(catalog.LINEUP) == known
    assert set(prices.PRICES) <= known


def test_a_model_is_traced_back_to_its_company():
    for model in (m for slug in catalog.LINEUP for m in catalog.lineup(slug)):
        assert companies.owner(model.name) == model.provider
    assert companies.owner("some-unknown-model") is None
    assert companies.owner(None) is None


def test_a_company_is_named_as_each_place_says_it():
    assert companies.named("gemini") == "Google Gemini"
    assert companies.label("gemini") == "Google"
    assert companies.get("gemini").status == "Google Gemini"
    assert companies.get("anthropic").status == "Claude (Anthropic)"
    # An unfamiliar one is said as it is rather than lost.
    assert companies.named("someone") == "someone"


# A company is named by its slug and asked of `companies`, never written into the file that
# needs a label, a key's setting or a model's owner (CLAUDE.md). The files that still name one
# are listed with why, so the list can only shrink: one that stops fails the test until it is
# taken out.
NAMED_OUTSIDE = {
    "base/config.py": "the built-in companies' key, model and cache settings are Settings fields",
    "store/settings.py": "the whitelist of those settings",
    "web/fields.py": "the boxes for those settings, with help written for the family",
    "web/links.py": "where each company's console and keys are",
    "web/models_page.py": "which companies can hear a recording, and the example choice",
    "voice.py": "the example facts under her lines",
    "integrations/price_lists.py": "the two public lists' own naming of the three",
}
COMPANY_WORD = re.compile(
    # The word, a model name's start, or a setting's start (`openai_api_key`); not CLAUDE.md.
    r"(?<![\w/])(anthropic|openai|gemini|claude(?!\.md)|gpt)(\b|_[a-z])",
    re.I,
)


def _code_without_comments(path: Path) -> str:
    with tokenize.open(path) as handle:
        return "".join(
            tok.string
            for tok in tokenize.generate_tokens(handle.readline)
            if tok.type != tokenize.COMMENT
        )


def test_only_the_providers_name_a_company():
    import familydb

    package = Path(familydb.__file__).parent
    naming = set()
    for path in sorted(package.rglob("*.py")):
        where = path.relative_to(package).as_posix()
        if where.startswith("agent/providers/"):
            continue
        if COMPANY_WORD.search(_code_without_comments(path)):
            naming.add(where)
    assert naming <= set(NAMED_OUTSIDE), sorted(naming - set(NAMED_OUTSIDE))
    assert naming == set(NAMED_OUTSIDE), (
        f"take out of NAMED_OUTSIDE: {sorted(set(NAMED_OUTSIDE) - naming)}"
    )
