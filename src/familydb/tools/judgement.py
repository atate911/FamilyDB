"""Hand-back tools of the judgement calls (familydb/judgement.py), never the chat model's. Each
checks its input against what was asked; a wrong answer goes back as an error, never the store."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from familydb.base.errors import ToolError
from familydb.tools.registry import ToolContext, tool
from familydb.tools.urls import clean_url


class Pick(BaseModel):
    question: str = Field(description="The question's name, exactly as given.")
    choice: str = Field(description="One of that question's options, exactly as given.")
    reason: str = Field(description="One short line an admin reads: why this one.")


class GiveJudgementInput(BaseModel):
    picks: list[Pick] = Field(description="One pick for every question asked.")


@tool(
    name="give_judgement",
    description=(
        "Hand back your judgement: one pick for each question, from that question's options "
        "only, with a short reason. Call it once, with every question answered. Not for chat."
    ),
    worker_only=True,
)
def give_judgement(ctx: ToolContext, args: GiveJudgementInput) -> dict[str, Any]:
    asked: dict[str, list[str]] = ctx.scratch.get("questions") or {}
    picked: dict[str, dict[str, str]] = {}
    for pick in args.picks:
        options = asked.get(pick.question)
        if options is None:
            raise ToolError(f"no question is called {pick.question!r}; they are {sorted(asked)}")
        if pick.choice not in options:
            raise ToolError(f"{pick.choice!r} is not an option for {pick.question}: {options}")
        picked[pick.question] = {"choice": pick.choice, "reason": " ".join(pick.reason.split())}
    missing = sorted(set(asked) - set(picked))
    if missing:
        raise ToolError(f"answer every question; still to answer: {missing}")
    ctx.scratch["picks"] = picked
    return {"recorded": len(picked)}


class ReportPriceInput(BaseModel):
    model: str = Field(description="The model, as named in the request.")
    found: bool = Field(description="Whether the company's own page gives its price.")
    input: float | None = Field(default=None, description="US$ per million input tokens.")
    output: float | None = Field(default=None, description="US$ per million output tokens.")
    cached: float | None = Field(
        default=None, description="US$ per million cached input tokens read, if given."
    )
    source_url: str | None = Field(default=None, description="The page it was read on.")


@tool(
    name="report_price",
    description=(
        "Hand back what the company's own pricing page says a model costs, per million tokens, "
        "and the page. found=false when its page does not say. Not for chat."
    ),
    worker_only=True,
)
def report_price(ctx: ToolContext, args: ReportPriceInput) -> dict[str, Any]:
    wanted = ctx.scratch.get("price_of")
    if args.model.lower() != str(wanted).lower():
        raise ToolError(f"the price asked for is {wanted}'s, not {args.model}'s")
    if not args.found:
        ctx.scratch["price"] = {"found": False}
        return {"recorded": False}
    url = clean_url(args.source_url)
    if args.input is None or args.output is None or url is None:
        raise ToolError("a price found needs input, output and the page it is on")
    for value in (args.input, args.output, args.cached):
        if value is not None and not 0 <= value <= 1000:
            raise ToolError("prices are US$ per million tokens, between 0 and 1000")
    ctx.scratch["price"] = {
        "found": True,
        "input": args.input,
        "output": args.output,
        "cached": args.cached,
        "source_url": url,
    }
    return {"recorded": True}
