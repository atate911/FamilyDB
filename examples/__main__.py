"""`python -m examples`: write the example sites, or serve the example household live.

    uv run python -m examples                  # writes them to ./example-sites
    uv run python -m examples --out DIR
    uv run python -m examples --serve 8099     # the household live, signed in as anyone

Live, every page works as on a real install; a message to Vera would call the model company with
the example's made-up key, so it fails as an unanswerable message does.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from examples import export, household


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m examples", description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("example-sites"), help="where to write")
    parser.add_argument("--serve", type=int, metavar="PORT", help="serve the household live")
    parser.add_argument("--start-only", action="store_true", help="rewrite only the start page")
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
        return
    if args.start_only:
        written = {
            person.key: {"/": "index.html"} for person in export.PEOPLE if person.key != "board"
        }
        written["board"] = {"/board": "board.html"}
        export.write_start(args.out, _found(args.out) or written)
        print(f"Rewrote the start page in {args.out}")
        return
    counts = export.export(args.out)
    for key, count in counts.items():
        print(f"{key}: {count} pages")
    print(f"Open {args.out / 'index.html'} in a browser.")


def _found(out: Path) -> dict[str, dict[str, str]]:
    """What an earlier run wrote, read back from its files, for the start page's links."""
    found: dict[str, dict[str, str]] = {}
    for person in export.PEOPLE:
        folder = out / person.key
        if not folder.is_dir():
            continue
        names = {path.name for path in folder.glob("*.html")}
        found[person.key] = {}
        for door in __import__("examples.start", fromlist=["DOORS"]).DOORS:
            if door["key"] != person.key:
                continue
            for address in ("/", "/board", *(address for _, address in door["more"])):
                name = export.file_for(address)
                if name in names:
                    found[person.key][address] = name
    return found


def serve(port: int) -> None:
    from waitress import serve as waitress_serve

    from familydb.web import create_app

    folder = Path(tempfile.mkdtemp(prefix="familydb-example-"))
    app, _ = household.build(folder)
    print(f"The example household on http://127.0.0.1:{port}/ (passwords in examples/household.py)")
    waitress_serve(create_app(app), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
