"""Reading the forms of the Other companies card on the AI model settings page, and what the card
draws for each company. Nothing here writes: `web/settings.py` takes what this returns, checks the
key with the company, and keeps it.

A company is defined by a `CompanyDef` (config.py); a person types a few of its parts and the rest
come from a template (agent/providers/companies.py) or a default. Every complaint is a sentence for
the person at the page."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from familydb.agent import uses
from familydb.agent.providers import companies
from familydb.config import CompanyDef, ModelPrice, Settings
from familydb.integrations import address

# Most companies a family would add; Settings holds twelve.
MOST = 12

OTHER = "other"
NO_NAME = "Give the company a name, so you can tell it from the others."
NO_ADDRESS = "Type the web address its chat service lives at, such as https://api.example.com/v1."
NOT_FOUND = (
    "This server could not find {host}. Check how it is spelled, and that this server is online."
)
LOCAL_BUT_PUBLIC = (
    "{host} is out on the internet, not on this machine or your own network, so “It runs on this "
    "machine or my own network” cannot be ticked for it: untick it, and use an https address."
)
NOT_PUBLIC = (
    "{host} is not out on the internet: it is this machine or your own network. If that is where "
    "it runs, tick “It runs on this machine or my own network”."
)
TOO_MANY = "That is as many companies as there is room for. Remove one first."
NO_MODEL = "Name the model to ask, as the company writes it."
BAD_PRICE_LINE = (
    "Line {number} of the prices is not “model, price in, price out” (dollars per million tokens, "
    "and optionally the price of a cached token read): {line}"
)
BAD_EXTRA = "The extra request fields are not a JSON object: {why}"
TAKEN = "There is already a company called {label}."
PROTECTION_LOST = (
    " It no longer asks {template} to use only companies that keep and train on nothing, so what "
    "you write may now go to ones that do."
)
KEY_AGAIN = (
    "You changed where {label} is, so type its key again: a saved key is not sent to a new "
    "address without you. (An address on your own network needs no key: tick that instead.)"
)


class FormError(Exception):
    """A form that cannot be taken as it was filled in; the message is for the person."""


def slug_for(label: str, taken: set[str]) -> str:
    """A short name for the company from what it is called, not one in use or a built-in one."""
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    base = re.sub(r"^[^a-z]+", "", base)[:20].strip("-") or "company"
    if len(base) < 2:
        base = f"{base}-ai"
    reserved = taken | set(companies.SPARE_ORDER)
    slug, number = base, 2
    while slug in reserved:
        slug = f"{base[: 23 - len(str(number))]}-{number}"
        number += 1
    return slug


def prices_from(text: str) -> tuple[ModelPrice, ...]:
    """Lines of `model price_in price_out [price_cached]`, in dollars per million tokens."""
    found: list[ModelPrice] = []
    for number, line in enumerate(text.splitlines(), start=1):
        words = line.replace(",", " ").split()
        if not words:
            continue
        try:
            if len(words) not in (3, 4):
                raise ValueError(line)
            amounts = [float(word.lstrip("$")) for word in words[1:]]
            found.append(
                ModelPrice(
                    name=words[0],
                    input=amounts[0],
                    output=amounts[1],
                    cached=amounts[2] if len(amounts) == 3 else None,
                )
            )
        except (ValueError, ValidationError):
            raise FormError(BAD_PRICE_LINE.format(number=number, line=line.strip()[:80])) from None
    return tuple(found)


def prices_text(prices: tuple[ModelPrice, ...]) -> str:
    lines = []
    for price in prices:
        cached = f" {price.cached:g}" if price.cached is not None else ""
        lines.append(f"{price.name} {price.input:g} {price.output:g}{cached}")
    return "\n".join(lines)


def extra_body_from(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise FormError(BAD_EXTRA.format(why=str(exc)[:80])) from None
    if not isinstance(parsed, dict):
        raise FormError(BAD_EXTRA.format(why="it should start with { and end with }"))
    return parsed


def extra_body_text(body: Mapping[str, Any]) -> str:
    return json.dumps(body, indent=2, sort_keys=True) if body else ""


def field_names_from(text: str) -> tuple[str, ...]:
    return tuple(word for word in re.split(r"[\s,]+", text.lower()) if word)


def check_address(base_url: str, *, local: bool, trusted: bool = False) -> None:
    """A service not on the family's own network must be out on the internet: a company's address
    is typed by a person, but this server is the one that goes there with a key. A template's
    address is ours (`trusted`), not typed, so it is not looked up."""
    host = urlsplit(base_url.strip()).hostname
    if not host or trusted:
        return
    reach = address.classify(host)
    if local:
        # A service on the family's network may speak http and need no key; one out on the
        # internet may not, whatever the box says.
        if reach == "public":
            raise FormError(LOCAL_BUT_PUBLIC.format(host=host))
        return
    if reach == "unresolved":
        raise FormError(NOT_FOUND.format(host=host))
    if reach == "private":
        raise FormError(NOT_PUBLIC.format(host=host))


def complaint(exc: ValidationError) -> str:
    """Pydantic's first complaint about a definition, as a sentence."""
    error = exc.errors(include_url=False)[0]
    message = str(error["msg"]).removeprefix("Value error, ")
    if not error["loc"]:  # about the definition as a whole, and already says what it is about
        return f"{message[:1].upper()}{message[1:]}."
    field = str(error["loc"][0])
    names = {
        "slug": "Its short name",
        "label": "Its name",
        "base_url": "Its address",
        "model": "Its model",
        "worker_model": "Its lookup model",
        "better_model": "Its better model",
        "best_model": "Its best model",
        "reasoning_fields": "The thinking fields",
        "extra_body": "The extra request fields",
    }
    return f"{names.get(field, field)}: {message}."


def from_template(
    template: companies.Template, *, model: str, taken: set[str], local: bool = False
) -> CompanyDef:
    """A new company from a template: only the model is the person's."""
    try:
        return CompanyDef(
            slug=slug_for(template.key, taken),
            label=template.label,
            base_url=template.base_url,
            template=template.key,
            model=model,
            reasoning_fields=template.reasoning_fields,
            extra_body=template.extra_body,
            local=local,
        )
    except ValidationError as exc:
        raise FormError(complaint(exc)) from exc


def from_form(
    form: Mapping[str, str], *, taken: set[str], existing: CompanyDef | None = None
) -> CompanyDef:
    """A company from what the add form (no `existing`) or an edit form held. A box an edit form
    does not carry at all keeps what the company had, so a short post cannot take away a field
    that protects the family; a box that is there and empty clears it."""

    def said(name: str, was: str = "") -> str:
        return form.get(name, was).strip()

    label = said("label", existing.label if existing else "")
    if not label:
        raise FormError(NO_NAME)
    base_url = said("base_url", existing.base_url if existing else "")
    if not base_url:
        raise FormError(NO_ADDRESS)
    whole = existing is None or "extra_body" in form  # an edit form that was drawn whole
    local = bool(form.get("local")) if whole else bool(existing and existing.local)
    model = said("model", existing.model if existing else "")
    if not model:
        raise FormError(NO_MODEL)
    try:
        fields: dict[str, Any] = {
            "slug": existing.slug if existing else slug_for(label, taken),
            "label": label,
            "base_url": base_url,
            "local": local,
            "model": model,
            "worker_model": said("worker_model", existing.worker_model if existing else ""),
            "better_model": said("better_model", existing.better_model if existing else ""),
            "best_model": said("best_model", existing.best_model if existing else ""),
        }
        if existing is None:
            fields["template"] = ""
            fields["reasoning_fields"] = field_names_from(
                form.get("reasoning_fields", "reasoning_content")
            )
            fields["extra_body"] = extra_body_from(form.get("extra_body", ""))
            fields["prices"] = prices_from(form.get("prices", ""))
        else:
            # A company that has been pointed somewhere else is no longer its template's.
            template = companies.TEMPLATES.get(existing.template)
            same_place = template is not None and template.base_url == base_url
            fields["template"] = existing.template if same_place else ""
            fields["stand_in"] = bool(form.get("stand_in")) if whole else existing.stand_in
            fields["reasoning_fields"] = (
                field_names_from(form["reasoning_fields"])
                if "reasoning_fields" in form
                else existing.reasoning_fields
            )
            fields["extra_body"] = (
                extra_body_from(form["extra_body"]) if "extra_body" in form else existing.extra_body
            )
            fields["prices"] = prices_from(form["prices"]) if "prices" in form else existing.prices
        return CompanyDef(**fields)
    except ValidationError as exc:
        raise FormError(complaint(exc)) from exc


def protection_lost(one: CompanyDef) -> companies.Template | None:
    """The template this company was added from, when its extra request fields no longer carry what
    the template asked for (OpenRouter's refusal of companies that keep what they are sent): the
    family's protection, which a person may remove but is told of."""
    template = companies.TEMPLATES.get(one.template)
    if template is None:
        return None
    return (
        template
        if any(one.extra_body.get(k) != v for k, v in template.extra_body.items())
        else None
    )


def duplicate_label(label: str, defined: tuple[CompanyDef, ...], skip: str = "") -> bool:
    lowered = label.strip().lower()
    built_in = {company.label.lower() for company in companies.BUILT_IN}
    return lowered in built_in or any(
        one.label.lower() == lowered for one in defined if one.slug != skip
    )


def stand_in_said(live: Settings, one: CompanyDef) -> bool:
    """What is said of standing in for this company: the family's word on the AI model page, else
    its own definition's. (Whether it may also depends on `provider_fallback`.)"""
    said = live.company_options.get(one.slug)
    return one.stand_in if said is None or said.stand_in is None else bool(said.stand_in)


def used_by(live: Settings, slug: str) -> list[str]:
    """What the company is chosen for, or answers now: the rows of the AI model page, by name."""
    found = []
    for use in uses.USES:
        said = uses.parse(live.model_choices.get(use.key))
        if uses.resolve(live, use.key).company == slug or (
            said.form == "model" and said.company == slug
        ):
            found.append(use.label)
    return found


def panel(company: companies.Company, live: Settings) -> dict[str, Any]:
    """What the card draws for one added company."""
    one = company.defined
    assert one is not None
    template = companies.TEMPLATES.get(one.template)
    return {
        "slug": one.slug,
        "label": one.label,
        "address": one.base_url,
        "local": one.local,
        "template": template,
        # What the template promised is said only while it is still true.
        "protected": template is not None and protection_lost(one) is None,
        "has_key": bool(company.key(live)),
        "needs_key": not one.local,
        "answering": uses.resolve(live, "chat").company == one.slug,
        "used_by": used_by(live, one.slug),
        "model": one.model,
        "worker_model": one.worker_model,
        "better_model": one.better_model,
        "best_model": one.best_model,
        "stand_in": stand_in_said(live, one),
        "reasoning_fields": ", ".join(one.reasoning_fields),
        "extra_body": extra_body_text(one.extra_body),
        "prices": prices_text(one.prices),
    }
