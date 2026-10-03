"""Re-set Branch Lines' sources in the condensed system (t2-track-mut, a type mutant).

Reads the parent's sources (variants/t1-track-graft/src) and writes this design's copies here,
changing only type: which face each rule names, its size, weight, tracking and leading. Every
replacement must match exactly once, so a change in the parent shows up as an error here rather
than as a rule quietly left in the old face. type.css (appended last by build.py) holds what the
parent never set: the base sheet's controls and labels, the dotted zero and the hung markers."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parents[1] / "t1-track-graft" / "src"

EDITS = {
    "track.css": [
        # The faces: the condensed Plex for the panel's legends, Plex Sans to read, Plex Mono for
        # the few things the machine prints (its name, the small print, code).
        ('  --head: "Archivo", var(--sans);',
         '  --head: "IBM Plex Sans Condensed", "IBM Plex Sans", sans-serif;\n'
         '  --sans: "IBM Plex Sans", system-ui, sans-serif;\n'
         '  --mono: "IBM Plex Mono", ui-monospace, monospace;'),
        ("  font-family: var(--head);\n  font-stretch: 84%;\n  word-spacing: 0.08em;\n",
         "  font-family: var(--head);\n  word-spacing: 0.03em;\n"),
        (".page-head h1 { font-size: clamp(2.3rem, 4.4vw, 3.05rem); font-weight: 700; line-height: 1; letter-spacing: -0.012em; }",
         ".page-head h1 { font-size: clamp(2.3rem, 4.4vw, 3.05rem); font-weight: 600; line-height: 1; letter-spacing: -0.008em; }"),
        ("h2, .h2, .section-head h2, .panel > h2, .panel > summary .h2 { font-size: 1.42rem; font-weight: 650; line-height: 1.15; letter-spacing: -0.006em; }",
         "h2, .h2, .section-head h2, .panel > h2, .panel > summary .h2 { font-size: 1.5rem; font-weight: 600; line-height: 1.15; letter-spacing: 0; }"),
        (".month-head h2 { font-size: 1.7rem; font-weight: 700; letter-spacing: -0.01em; }",
         ".month-head h2 { font-size: 1.75rem; font-weight: 600; letter-spacing: -0.005em; }"),
        # Every stamp, count and small label is a legend now, not the typewriter.
        (".stamp, .hang, .rel, .said-by, .eyebrow, .chip-mon, .chip-dow, .count, .facts .at, .legal {\n  font-family: var(--mono);",
         ".stamp, .hang, .rel, .said-by, .eyebrow, .chip-mon, .chip-dow, .count, .facts .at {\n  font-family: var(--head);"),
        (".stamp, .hang { font-size: 0.8125rem; font-weight: 500; line-height: 1.3; letter-spacing: 0;",
         ".stamp, .hang { font-size: 0.875rem; font-weight: 500; line-height: 1.25; letter-spacing: 0.01em;"),
        ("{ font: 500 0.8125rem/1.3 var(--sans); letter-spacing: 0; text-transform: none; color: var(--label); }",
         "{ font: 500 0.875rem/1.25 var(--head); letter-spacing: 0.01em; text-transform: none; color: var(--label); }"),
        (".eyebrow, .chip-mon, .chip-dow { font-size: 0.8125rem; letter-spacing: 0;",
         ".eyebrow, .chip-mon, .chip-dow { font-size: 0.875rem; letter-spacing: 0.01em;"),
        (".rel { padding: 0; font-size: 0.8125rem; font-weight: 500; letter-spacing: 0;",
         ".rel { padding: 0; font-size: 0.875rem; font-weight: 500; letter-spacing: 0.01em;"),
        ("min-height: 2.75rem; font-size: 0.92rem; font-weight: 500; color: var(--steel); text-decoration: underline;",
         "min-height: 2.75rem; font: 500 1rem/1.2 var(--head); color: var(--steel); text-decoration: underline;"),
        (".ask-question { font-family: var(--sans); font-stretch: 100%; font-weight: 650; letter-spacing: -0.02em; color: var(--heading); }",
         ".ask-question { font-family: var(--head); font-weight: 600; color: var(--heading); }"),
        (".ask .who label, .ask .who .from { font: 500 0.875rem/1 var(--sans);",
         ".ask .who label, .ask .who .from { font: 500 0.9375rem/1 var(--head);"),
        ("font-family: var(--head); font-stretch: 84%; font-size: 1.9rem; font-weight: 700; line-height: 0.9; letter-spacing: -0.01em;",
         "font-family: var(--head); font-size: 2.125rem; font-weight: 600; line-height: 0.9; letter-spacing: -0.01em;"),
        (".agenda .when .t { font: 500 0.82rem/1.3 var(--mono);",
         ".agenda .when .t { font: 500 0.875rem/1.3 var(--head);"),
        ("  .across .rel { font-size: 0.72rem; }", "  .across .rel { font-size: 0.8125rem; }"),
        (".facts .at { font-size: 0.8rem; font-weight: 500;", ".facts .at { font-size: 0.875rem; font-weight: 500;"),
        (".count { margin: 0 0 0.75rem 0.1rem; font-size: 0.8rem;", ".count { margin: 0 0 0.75rem 0.1rem; font-size: 0.875rem;"),
    ],
    "phosphor.css": [
        ("font: 500 0.8125rem/1 var(--mono); letter-spacing: 0.02em; color: var(--brand);",
         "font: 600 0.875rem/1 var(--head); letter-spacing: 0.01em; color: var(--brand);"),
    ],
    "branch.css": [
        ('  --fig: "Archivo", var(--sans);', "  --fig: var(--head);"),
        # Home's question is the page's title, so it is set at the title's step, in its face.
        (".ask-question { font-size: clamp(1.55rem, 3vw, 2rem); letter-spacing: -0.022em; }",
         ".ask-question { font-size: clamp(1.875rem, 4.4vw, 3.05rem); line-height: 1.02; letter-spacing: -0.008em; }"),
        (".now-word { position: absolute; left: -0.1rem; top: 1.35rem; font: 500 0.8125rem/1 var(--mono);",
         ".now-word { position: absolute; left: -0.1rem; top: 1.35rem; font: 600 0.875rem/1 var(--head);"),
        (".checklist .hang .stamp, .hang .stamp { font-size: 0.8rem; }",
         ".checklist .hang .stamp, .hang .stamp { font-size: 0.875rem; }"),
        (".kind-word { margin-left: 0.45rem; font-size: 0.82rem; font-weight: 500;",
         ".kind-word { margin-left: 0.5rem; font: 500 0.875rem var(--head); letter-spacing: 0.01em;"),
        (".kid-rows .count-open { grid-column: 4; font: 500 0.875rem/1.3 var(--sans);",
         ".kid-rows .count-open { grid-column: 4; font: 500 0.9375rem/1.3 var(--head);"),
        (".said-by { gap: 0.1rem 0.55rem; margin-bottom: 0.2rem; font-size: 0.8125rem; }",
         ".said-by { gap: 0.1rem 0.55rem; margin-bottom: 0.2rem; font-size: 0.875rem; }"),
        (".said-when { font: 500 0.75rem/1 var(--mono);", ".said-when { font: 500 0.875rem/1 var(--head);"),
        ("width: 28px; height: 28px; font: 600 0.78rem/1 var(--sans);",
         "width: 28px; height: 28px; font: 600 0.875rem/1 var(--head);"),
        ("padding: 2px 4px; font: 500 13px/1.2 var(--mono);", "padding: 2px 4px; font: 500 14px/1.2 var(--head);"),
        # Hung by hand: every list's markers stand in the margin under its head's icon, and its
        # words on the head's own text edge (the rows were 4-5px in from it).
        (".lately-rows > li, .kid-rows > li { display: grid; grid-template-columns: 1.9rem minmax(0, 1fr) auto; align-items: center; gap: 0 0.8rem; min-height: 2.9rem; padding: 0.2rem 0.5rem 0.2rem 0.25rem;",
         ".lately-rows > li, .kid-rows > li { display: grid; grid-template-columns: 1.9rem minmax(0, 1fr) auto; align-items: center; gap: 0 0.75rem; min-height: 2.9rem; padding: 0.2rem 0.5rem 0.2rem 0;"),
        ("align-items: center; gap: 0.1rem 1rem; min-height: 2.75rem; padding: 0.3rem 0.5rem 0.3rem 0;",
         "align-items: center; gap: 0.1rem 0.7rem; min-height: 2.75rem; padding: 0.3rem 0.5rem 0.3rem 0;"),
        (".colheads { display: grid; align-items: end; gap: 0 0.9rem; margin: 0; padding: 0.35rem 0.5rem 0.4rem; }",
         ".colheads { display: grid; align-items: end; gap: 0 0.9rem; margin: 0; padding: 0.35rem 0.5rem 0.4rem 0.25rem; }"),
        ("padding-left: 6.8rem; }", "padding-left: 6.8rem; padding-right: 0.4rem; }"),
        # One text edge a page: a list's names stand on the title's own edge, the rings and icons
        # hanging to its left (Ideas and Settings were 3-4px in from it).
        (".idea-board .colheads, .idea-rows > li { grid-template-columns: 1.9rem minmax(0, 1fr) minmax(7rem, 11rem) 7.5rem 2.6rem; }",
         ".idea-board .colheads, .idea-rows > li { grid-template-columns: 1.9rem minmax(0, 1fr) minmax(7rem, 11rem) 7.5rem 2.6rem; column-gap: 0.7rem; }"),
        ("align-items: center; gap: 0 1rem; min-height: 3rem; margin: 0; padding: 0.55rem 0.5rem 0.55rem 0.35rem;",
         "align-items: center; gap: 0 0.85rem; min-height: 3rem; margin: 0; padding: 0.55rem 0.5rem 0.55rem 0.35rem;"),
        (".tie { position: relative; display: inline-flex; align-items: center; gap: 0.6rem; font: 500 13px/1.2 var(--mono);",
         ".tie { position: relative; display: inline-flex; align-items: center; gap: 0.6rem; font: 500 14px/1.2 var(--head); letter-spacing: 0.01em;"),
        (".kids-talk h2 { font-size: 1.2rem; }", ".kids-talk h2 { font-size: 1.25rem; }"),
        ("gap: 0 0.4rem; margin: 0 0 -0.35rem; font: 400 15px/1.2 var(--sans);",
         "gap: 0 0.4rem; margin: 0 0 -0.35rem; font: 500 16px/1.2 var(--head);"),
        (".tally .figure { font: 600 40px/1 var(--fig); font-stretch: 75%;", ".tally .figure { font: 600 42px/1 var(--fig);"),
        (".idea-tools .filters label { display: block; margin: 0 0 0.3rem; font: 500 0.8rem/1.2 var(--sans);",
         ".idea-tools .filters label { display: block; margin: 0 0 0.3rem; font: 500 0.875rem/1.2 var(--head);"),
        (".idea-row .on { margin-left: 0.4rem; font: 500 0.8rem var(--mono);",
         ".idea-row .on { margin-left: 0.5rem; font: 500 0.875rem var(--head);"),
        ("grid-template-columns: minmax(0, 1fr) 2.2ch; gap: 0.5ch; font: 500 0.84rem/1.2 var(--mono);",
         "grid-template-columns: minmax(0, 1fr) 1.55em; gap: 0.3em; font: 500 0.9375rem/1.2 var(--head);"),
        (".idea-row .drive.pending { display: block; font: italic 400 0.84rem var(--sans);",
         ".idea-row .drive.pending { display: block; font: italic 400 0.875rem var(--sans);"),
        (".idea-row .n { font: 500 0.8rem/1.2 var(--mono);", ".idea-row .n { font: 500 0.875rem/1.2 var(--head);"),
        ("  .idea-rows .drive { grid-area: d; display: flex; gap: 0.5ch; font-size: 0.8125rem;",
         "  .idea-rows .drive { grid-area: d; display: flex; gap: 0.3em; font-size: 0.875rem;"),
        (".keys-name { margin-right: 0.35rem; font: 500 0.8rem/1 var(--sans);",
         ".keys-name { margin-right: 0.35rem; font: 500 0.875rem/1 var(--head);"),
        ("  font: 500 0.92rem/1 var(--sans); color: var(--ink-2); text-decoration: none; list-style: none; cursor: pointer;",
         "  font: 500 1rem/1 var(--head); color: var(--ink-2); text-decoration: none; list-style: none; cursor: pointer;"),
        (".add-task-head h2 { display: flex; align-items: center; gap: 0.5rem; margin: 0; font-size: 1.2rem; }",
         ".add-task-head h2 { display: flex; align-items: center; gap: 0.5rem; margin: 0; font-size: 1.25rem; }"),
        (".task-line .reminder { margin-left: 0.5rem; font-size: 0.82rem; font-weight: 400;",
         ".task-line .reminder { margin-left: 0.5rem; font: 500 0.875rem var(--head);"),
        (".task-line .due { font-size: 0.9rem; font-variant-numeric: tabular-nums;",
         ".task-line .due { font: 500 0.9375rem/1.3 var(--head); letter-spacing: 0.01em;"),
        (".task-line details.more > summary { padding: 0 0.75rem; font-size: 0.88rem; }",
         ".task-line details.more > summary { padding: 0 0.75rem; }"),
        ("  .task-line .due { grid-area: u; text-align: left; font-size: 0.85rem; }",
         "  .task-line .due { grid-area: u; text-align: left; font-size: 0.875rem; }"),
        (".rows .what .t, .rows .hang .t { font: 500 0.8125rem var(--mono);",
         ".rows .what .t, .rows .hang .t { font: 500 0.875rem var(--head);"),
        ("font: 500 0.8125rem/1.2 var(--mono); border-radius: 3px; }",
         "font: 500 0.9375rem/1.2 var(--head); border-radius: 3px; }"),
        (".event small { display: block; font: 500 0.75rem/1.2 var(--mono);",
         ".event small { display: block; font: 500 0.8125rem/1.2 var(--head);"),
        (".head-fig { display: flex; align-items: flex-end;", ".head-fig { display: flex; align-items: last baseline;"),
        (".fig-n { font: 500 clamp(2.3rem, 4.4vw, 3.05rem)/0.84 var(--fig); font-stretch: 75%;",
         ".fig-n { font: 400 clamp(2.3rem, 4.4vw, 3.05rem)/0.84 var(--fig);"),
        (".fig-u { display: grid; font: 500 0.8125rem/1.25 var(--sans);",
         ".fig-u { display: grid; font: 500 0.875rem/1.2 var(--head); letter-spacing: 0.01em;"),
    ],
    "relight.css": [],
}

for name, edits in EDITS.items():
    text = (PARENT / name).read_text()
    for old, new in edits:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: expected one match, found {n}: {old[:80]}")
        text = text.replace(old, new)
    (HERE / name).write_text(text)
print("re-set:", ", ".join(EDITS))
