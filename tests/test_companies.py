"""The registry of companies (agent/providers/companies.py): each fact about a company is written
once, and what it names exists."""

import importlib

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
