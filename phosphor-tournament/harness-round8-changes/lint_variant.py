"""Check a palette's own markup before it is served: its templates (taken with the real ones it
does not override) must keep everything the page does, and add nothing the page's security
policy forbids. Its static files may add pictures and icons, never scripts, and keep every icon.

Usage: python3 lint_variant.py VARIANT_DIR      (VARIANT_DIR holds templates/ and/or static/)
Exit status 1, with the reasons, when it refuses.
"""

import re
import sys
from pathlib import Path

REPO = Path("/home/user/FamilyDB/src/familydb/web")
ORIG_T, ORIG_S = REPO / "templates", REPO / "static"


def effective(over: Path) -> dict[str, str]:
    files = {str(p.relative_to(ORIG_T)): p.read_text() for p in ORIG_T.rglob("*.html")}
    if over.exists():
        for p in over.rglob("*.html"):
            files[str(p.relative_to(over))] = p.read_text()
    return files


def facts(files: dict[str, str]) -> dict[str, set | int]:
    text = "\n".join(files.values())
    return {
        "field names": set(re.findall(r'\bname="([^"]+)"', text)),
        "form actions": set(re.findall(r'\baction="([^"]+)"', text)),
        # A static asset is not a link the family follows: a design without icons may drop it.
        "endpoints": set(re.findall(r"url_for\(\s*['\"]([^'\"]+)", text)) - {"static"},
        "csrf and once tokens": set(re.findall(r"(csrf_token|once_token)", text)),
        "scripts": len(re.findall(r"<script\b", text)),
        "safe": len(re.findall(r"\|\s*safe\b", text)) + len(re.findall(r"Markup\(", text)),
        "inline style": len(re.findall(r"\sstyle\s*=", text)) + len(re.findall(r"<style\b", text)),
        "handlers": len(re.findall(r"\son[a-z]+\s*=", text)),
        # An SVG's namespace (xmlns="http://www.w3.org/2000/svg") names no address to load.
        "external": set(re.findall(r"(https?://(?!www\.w3\.org/)[^\s\"'<>]+)", text)),
    }


def main() -> None:
    root = Path(sys.argv[1])
    problems = []
    t_over = root / "templates"
    if t_over.exists():
        for p in t_over.rglob("*"):
            if p.is_file() and p.suffix != ".html":
                problems.append(f"templates/{p.relative_to(t_over)}: only .html templates")
        orig, new = facts(effective(Path("/nonexistent"))), facts(effective(t_over))
        # Per template: what an overridden template had must still be in it, or in a new partial
        # of the palette's own (a form may move into one).
        originals = {str(p.relative_to(ORIG_T)) for p in ORIG_T.rglob("*.html")}
        mine = {str(p.relative_to(t_over)): p.read_text() for p in t_over.rglob("*.html")}
        for name, text in mine.items():
            if name not in originals:
                continue
            before = facts({name: (ORIG_T / name).read_text()})
            after = facts({name: text})
            partials = facts({k: v for k, v in mine.items() if k != name})
            for key in ("field names", "form actions", "endpoints", "csrf and once tokens"):
                gone = before[key] - after[key] - partials[key]
                if gone:
                    problems.append(f"{name}: {key} missing: {sorted(gone)[:8]} (every form, field and link must still work)")
        for key, why in (("scripts", "no new scripts"), ("safe", "no new unescaped output (|safe, Markup)"),
                         ("inline style", "no inline style attributes (the page's policy allows none)"),
                         ("handlers", "no inline event handlers")):
            if new[key] > orig[key]:
                problems.append(f"{why}: {orig[key]} before, {new[key]} now")
        added = new["external"] - orig["external"]
        if added:
            problems.append(f"no new outside addresses: {sorted(added)[:5]}")
    s_over = root / "static"
    if s_over.exists():
        for p in s_over.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(s_over)
            if p.suffix.lower() not in {".svg", ".png", ".webp", ".jpg", ".jpeg"}:
                problems.append(f"static/{rel}: only pictures and icons (svg, png, webp, jpg)")
            if p.suffix.lower() == ".svg" and re.search(r"<script|\son[a-z]+\s*=|javascript:", p.read_text(), re.I):
                problems.append(f"static/{rel}: no script inside an svg")
        sprite = s_over / "icons.svg"
        if sprite.exists():
            before = set(re.findall(r'<symbol[^>]*\bid="([^"]+)"', (ORIG_S / "icons.svg").read_text()))
            after = set(re.findall(r'<symbol[^>]*\bid="([^"]+)"', sprite.read_text()))
            if before - after:
                problems.append(f"icons.svg must keep every icon: missing {sorted(before - after)[:8]}")
    if problems:
        print("variant refused:\n  - " + "\n  - ".join(problems))
        sys.exit(1)
    print("variant ok")


if __name__ == "__main__":
    main()
