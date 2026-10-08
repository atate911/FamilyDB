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

from familydb.agent.providers import companies
from familydb.config import CompanyDef, ModelPrice, Settings
from familydb.integrations import address

# Most companies a family would add; Settings holds twelve.
MOST = 12

OTHER = "other"
NO_NAME = "Give the company a name, so you can tell it from the others."
NO_ADDRESS = "Type the web address its chat service lives at, such as https://api.example.com/v1."
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


def check_address(base_url: str, *, local: bool) -> None:
    """A service not on the family's own network must be out on the internet: a company's address
    is typed by a person, but this server is the one that goes there with a key."""
    host = urlsplit(base_url.strip()).hostname
    if host and not local and not address.is_public(host):
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
    """A company from what the add form (no `existing`) or an edit form held."""
    label = form.get("label", existing.label if existing else "").strip()
    if not label:
        raise FormError(NO_NAME)
    base_url = form.get("base_url", existing.base_url if existing else "").strip()
    if not base_url:
        raise FormError(NO_ADDRESS)
    local = bool(form.get("local"))
    model = form.get("model", existing.model if existing else "").strip()
    if not model:
        raise FormError(NO_MODEL)
    try:
        fields: dict[str, Any] = {
            "slug": existing.slug if existing else slug_for(label, taken),
            "label": label,
            "base_url": base_url,
            "local": local,
            "template": existing.template if existing else "",
            "model": model,
            "worker_model": form.get("worker_model", "").strip(),
            "better_model": form.get("better_model", "").strip(),
            "best_model": form.get("best_model", "").strip(),
        }
        if existing is None:
            fields["reasoning_fields"] = field_names_from(
                form.get("reasoning_fields", "reasoning_content")
            )
            fields["extra_body"] = extra_body_from(form.get("extra_body", ""))
            fields["prices"] = prices_from(form.get("prices", ""))
        else:
            fields["stand_in"] = bool(form.get("stand_in"))
            fields["reasoning_fields"] = field_names_from(form.get("reasoning_fields", ""))
            fields["extra_body"] = extra_body_from(form.get("extra_body", ""))
            fields["prices"] = prices_from(form.get("prices", ""))
        return CompanyDef(**fields)
    except ValidationError as exc:
        raise FormError(complaint(exc)) from exc


def duplicate_label(label: str, defined: tuple[CompanyDef, ...], skip: str = "") -> bool:
    lowered = label.strip().lower()
    built_in = {company.label.lower() for company in companies.BUILT_IN}
    return lowered in built_in or any(
        one.label.lower() == lowered for one in defined if one.slug != skip
    )


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
        "has_key": bool(company.key(live)),
        "needs_key": not one.local,
        "answering": live.provider == one.slug,
        "model": one.model,
        "worker_model": one.worker_model,
        "better_model": one.better_model,
        "best_model": one.best_model,
        "stand_in": one.stand_in,
        "reasoning_fields": ", ".join(one.reasoning_fields),
        "extra_body": extra_body_text(one.extra_body),
        "prices": prices_text(one.prices),
    }
