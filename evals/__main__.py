"""`uv run python -m evals`: run the cases against a real model and say what passed."""

from __future__ import annotations

import argparse
import json
import sys

from evals.cases import CASES, by_name
from evals.harness import grade, run_case
from familydb.agent import providers
from familydb.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals", description=__doc__)
    parser.add_argument("--case", action="append", help="run only this case (repeatable)")
    parser.add_argument("--repeat", type=int, default=1, help="runs per case (default 1)")
    parser.add_argument("--provider", choices=providers.NAMES, help="answer with this vendor")
    parser.add_argument("--model", help="and this model, instead of the configured one")
    parser.add_argument("--show", action="store_true", help="print each reply and its calls")
    parser.add_argument(
        "--budget", type=float, default=0.50, help="stop once this many estimated dollars are spent"
    )
    parser.add_argument("--json", dest="json_path", help="also write the results here")
    args = parser.parse_args(argv)

    base = Settings()  # the keys, as the bot itself would find them
    if args.provider:
        base = base.model_copy(update={"provider": args.provider})
    if args.model:
        base = base.model_copy(update={f"{base.provider}_model": args.model})
    if not providers.ready(base, "chat"):
        print(f"No key for {base.provider}: set it in .env or the environment.", file=sys.stderr)
        return 2
    model = getattr(base, f"{base.provider}_model")
    cases = [by_name(name) for name in args.case] if args.case else list(CASES)
    print(f"{len(cases)} case(s) x {args.repeat} on {base.provider} {model}\n")

    spent = 0.0
    results = []
    for case in cases:
        passes = 0
        problems: list[str] = []
        for _ in range(args.repeat):
            if spent >= args.budget:
                print(f"\nStopped: ${spent:.4f} spent, the budget is ${args.budget:.2f}.")
                return _finish(results, spent, args.json_path, stopped=True)
            run = run_case(case, base)
            spent += run.cost
            wrong = grade(case, run)
            passes += not wrong
            problems.extend(wrong)
            if args.show:
                print(f"--- {case.name}")
                for call in run.calls:
                    print(f"    {call.name} {json.dumps(call.input, sort_keys=True)}")
                print("    > " + run.reply.replace("\n", "\n      "))
        mark = "ok  " if passes == args.repeat else "FAIL"
        print(f"{mark} {passes}/{args.repeat}  {case.name}")
        for problem in sorted(set(problems)):
            print(f"         - {problem}")
        results.append(
            {"case": case.name, "passes": passes, "runs": args.repeat, "problems": problems}
        )
    return _finish(results, spent, args.json_path, stopped=False)


def _finish(results: list[dict], spent: float, json_path: str | None, *, stopped: bool) -> int:
    runs = sum(r["runs"] for r in results)
    passed = sum(r["passes"] for r in results)
    print(f"\n{passed}/{runs} runs passed, about ${spent:.4f} (estimated from the price table)")
    if json_path:
        with open(json_path, "w", encoding="utf-8") as out:
            json.dump({"results": results, "spent_usd": spent}, out, indent=2)
    return 0 if passed == runs and not stopped else 1


if __name__ == "__main__":
    raise SystemExit(main())
