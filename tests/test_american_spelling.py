"""What the family reads is spelled the American way (docs/STYLE.md, "Words"). Names that are data
or code (the stored "cancelled" status, the `judgement` module and its settings) are not what is
read, so they stay."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "familydb"
BRITISH = re.compile(
    r"\b(colours?|coloured|organis\w+|neighbourhoods?|kilometres?|metres?|grey|centres?|"
    r"behaviours?|humour|honou\w+|favourites?|recognis\w+|summaris\w+|cancell(?:ed|ing))\b",
    re.I,
)


def _read(paths) -> list[tuple[Path, str]]:
    return [(path, path.read_text()) for path in sorted(paths)]


def test_what_is_read_is_in_american_english() -> None:
    web = SRC / "web"
    texts = _read((web / "templates").rglob("*.html"))
    # A template's comments are for whoever edits it; a stored value like 'cancelled' is data.
    texts = [(path, re.sub(r"\{#.*?#\}", "", text, flags=re.S)) for path, text in texts]
    texts = [(path, re.sub(r"'cancelled'", "", text)) for path, text in texts]
    texts += _read((SRC / "personas").rglob("*.md")) + _read((SRC / "personas").rglob("*.toml"))
    texts += _read((SRC / "agent" / "prompts").glob("*.md"))
    texts += _read([SRC / "voice.py", web / "fields.py", web / "looks.py"])
    found = {
        f"{path.relative_to(SRC)}: {word[0]}"
        for path, text in texts
        for word in BRITISH.finditer(text)
        if not word[0].isupper()  # BEHAVIOUR is a name in the code
        # in code files, only quoted prose counts: names like theme_colours are not read
        if not (path.suffix == ".py" and _in_code(text, word.start()))
    }
    assert not found, sorted(found)


def _in_code(text: str, at: int) -> bool:
    """Whether the match sits in an identifier or a comment, not in a quoted sentence."""
    line_start = text.rfind("\n", 0, at) + 1
    line = text[line_start : text.find("\n", at)]
    before = line[: at - line_start]
    if before.lstrip().startswith(("#", '"""')) or "#" in before:
        return True
    return before.count('"') % 2 == 0 or text[at - 1] == "_" or text[at + 1 :][:1] == "_"
