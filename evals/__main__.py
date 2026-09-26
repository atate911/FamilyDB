"""`uv run python -m evals`: run the cases against a real model and say what passed."""

from __future__ import annotations

import argparse
import json
import sys

from evals.cases import CASES, by_name
from evals.harness import grade, run_case, under_persona
from familydb import personas
from familydb.agent import gateway, providers
from familydb.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals", description=__doc__)
    parser.add_argument("--case", action="append", help="run only this case (repeatable)")
    parser.add_argument("--repeat", type=int, default=1, help="runs per case (default 1)")
    parser.add_argument("--provider", choices=providers.NAMES, help="answer with this vendor")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--model", help="and this model, instead of the configured one")
    which.add_argument(
        "--level", choices=providers.catalog.LEVELS, help="or its model at this level"
    )
    parser.add_argument(
        "--persona",
        action="append",
        help="answer as this persona, by key ("
        + ", ".join((*personas.available(), personas.NONE))
        + "), or with this file's text as a rewrite of the default persona; repeat it to run "
        "every case under each and compare them (without it: the configured persona, as she "
        "ships)",
    )
    parser.add_argument("--show", action="store_true", help="print each reply and its calls")
    parser.add_argument(
        "--budget",
        type=float,
        default=0.50,
        help="estimated dollars to spend at most, across every persona; checked before every "
        "model call, so only the call that crosses it can go over (default 0.50)",
    )
    parser.add_argument("--json", dest="json_path", help="also write the results here")
    args = parser.parse_args(argv)

    base = Settings()  # the keys, as the bot itself would find them
    if args.provider:
        base = base.model_copy(update={"provider": args.provider})
    if args.model:
        # A model named is the everyday one, so a level set in the environment cannot pass it by.
        base = base.model_copy(
            update={f"{base.provider}_model": args.model, "chat_level": "everyday"}
        )
    if args.level:
        base = base.model_copy(update={"chat_level": args.level})
    if not providers.ready(base, "chat"):
        print(f"No key for {base.provider}: set it in .env or the environment.", file=sys.stderr)
        return 2
    try:
        # By what the results call each: the same persona asked for twice runs once.
        under = dict(under_persona(base, choice) for choice in args.persona or [base.persona])
    except (OSError, ValueError) as exc:  # pydantic's ValidationError is a ValueError
        print(f"--persona: {exc}", file=sys.stderr)
        return 2
    _, model = gateway.answering(base, "chat")
    cases = [by_name(name) for name in args.case] if args.case else list(CASES)
    several = len(under) > 1
    print(
        f"{len(cases)} case(s) x {args.repeat} on {base.provider} {model}, "
        f"persona{'s' if several else ''} {', '.join(under)}\n"
    )

    spent = 0.0
    sent = 0
    results = []
    # Each case under every persona in turn, so a budget that runs out leaves them compared on
    # the same cases rather than one persona finished and the next barely started.
    for case in cases:
        for label, settings in under.items():
            named = f"{case.name} ({label})" if several else case.name
            passes = tokens = 0
            cost = 0.0
            problems: list[str] = []
            for _ in range(args.repeat):
                if spent >= args.budget:
                    print(f"\nStopped: ${spent:.4f} spent, the budget is ${args.budget:.2f}.")
                    return _finish(results, spent, sent, args.json_path, stopped=True)
                # What is left of the budget is the run's own daily limit, checked before each
                # call.
                run = run_case(case, settings, limit=args.budget - spent)
                spent += run.cost
                sent += run.input_tokens
                if spent >= args.budget:
                    # The limit stopped it partway, or it just finished at the edge: not graded.
                    print(f"\nStopped in {named}: ${spent:.4f} spent of ${args.budget:.2f}.")
                    return _finish(results, spent, sent, args.json_path, stopped=True)
                wrong = grade(case, run)
                passes += not wrong
                problems.extend(wrong)
                tokens += run.input_tokens
                cost += run.cost
                if args.show:
                    print(f"--- {named}")
                    for call in run.calls:
                        print(f"    {call.name} {json.dumps(call.input, sort_keys=True)}")
                    print("    > " + run.reply.replace("\n", "\n      "))
            mark = "ok  " if passes == args.repeat else "FAIL"
            print(f"{mark} {passes}/{args.repeat}  {named}")
            for problem in sorted(set(problems)):
                print(f"         - {problem}")
            results.append(
                {
                    "case": case.name,
                    "persona": label,
                    "passes": passes,
                    "runs": args.repeat,
                    "input_tokens": tokens,
                    "cost_usd": cost,
                    "problems": problems,
                }
            )
    return _finish(results, spent, sent, args.json_path, stopped=False)


def _finish(
    results: list[dict], spent: float, sent: int, json_path: str | None, *, stopped: bool
) -> int:
    # Each persona's totals over its graded runs, to compare them by. A run the budget cut short
    # is counted in what was spent and sent, but in no persona's line.
    compared: dict[str, dict] = {}
    for result in results:
        total = compared.setdefault(result["persona"], {"persona": result["persona"]})
        for key in ("passes", "runs", "input_tokens", "cost_usd"):
            total[key] = total.get(key, 0) + result[key]
    print()
    if len(compared) > 1:
        width = max(len(label) for label in compared)
        for total in compared.values():
            print(
                f"{total['persona']:<{width}}  {total['passes']}/{total['runs']} runs passed, "
                f"{total['input_tokens']:,} input tokens, about ${total['cost_usd']:.4f}"
            )
    runs = sum(r["runs"] for r in results)
    passed = sum(r["passes"] for r in results)
    print(
        f"{passed}/{runs} runs passed, {sent:,} input tokens, about ${spent:.4f} "
        "(estimated from the price table)"
    )
    if json_path:
        with open(json_path, "w", encoding="utf-8") as out:
            summary = {
                "results": results,
                "personas": list(compared.values()),
                "input_tokens": sent,
                "spent_usd": spent,
            }
            json.dump(summary, out, indent=2)
    return 0 if passed == runs and not stopped else 1


if __name__ == "__main__":
    raise SystemExit(main())
