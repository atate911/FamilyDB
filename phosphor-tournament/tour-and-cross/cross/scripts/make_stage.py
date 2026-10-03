"""Builds cross_stage.js from the side tour's stage script: the same design, crit, revision and judging
machinery, with the crossing rounds' framing, the CROSS brief and judging with anchors."""
from pathlib import Path

X = Path(__file__).resolve().parent
s = (X.parent / "tour" / "tour_stage.js").read_text()


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, (c, old[:90])
    s = s.replace(old, new)


rep("name: 'phosphor-tour-stage'", "name: 'phosphor-cross-stage'")
rep("description: 'One stage of a side-tour round of the Phosphor tournament: ledger, design, judge, learn or landing'",
    "description: 'One stage of a crossing round (14a, 14b) of the Phosphor tournament: design, judge or learn'")
rep("const T = `${H}/tour`", "const T = `${H}/cross`\nconst TOURDIR = `${H}/tour`\nconst RL = args.label || args.round")

i = s.index("const TOUR = `")
j = s.index("\n", i)
s = s[:i] + (X / "framing.txt").read_text().strip() + s[j:]

i = s.index("const MAIN_LINE = `")
j = s.index("\n", i)
s = s[:i] + ("const MAIN_LINE = `Take from the other camp freely: its structures and components are what this round is for, "
             "as long as each is rebuilt in this line's own colours, type and line and the line's own idea stays recognisable "
             "at a glance. The small, universal fixes every panel asked of everyone (44px targets, sentence-case controls and "
             "links, late shown in words, tabular figures, underlined links, one control per filter, a strong \"here\") are "
             "free to take.`") + s[j:]

s = s.replace("round ${N} of a side tour of the Phosphor tournament", "crossing round ${RL} of the Phosphor tournament")
s = s.replace("a panel of the Phosphor tournament's side tour", "a panel of the Phosphor tournament's crossing rounds")
rep("${N > 1 ? `Every title the tour has tried", "${true ? `Every title the side tour and the crossing rounds have tried")
s = s.replace("Round ${N} of the side tour of the Phosphor tournament has been judged.", "Crossing round ${RL} of the Phosphor tournament has been judged.")
rep('headed "## Tour round ${N}"', 'headed "## Crossing round ${RL}"')
rep('headed "## After tour round ${N}"', 'headed "## After crossing round ${RL}"')
rep("new features numbered T${N}-01, T${N}-02", "new features numbered X${RL}-01, X${RL}-02")
s = s.replace("${T}/dossiers/donors.md", "${TOURDIR}/dossiers/donors.md")
s = s.replace("${T}/donors/", "${TOURDIR}/donors/")

rep("const SLOT_TEXT = {", """const SLOT_TEXT = {
  cross: (b) => `CROSS of ${b.parent} (${b.parentName}): keep this line's idea, its structure and its mood, recognisable at a glance, and make it better in two ways. (1) Its own judges' fixes: apply the most-cited ones from its dossier (name each and which lenses asked). (2) The OTHER camp's best FEATURES: study the other camp's current designs (${args.lin.otherCamp.map(o => `${o.id} ${o.name}: files ${o.dir}/palettes/${o.id}.json and ${o.dir}/variants/${o.id}/, shots ${o.dir}/out/${o.id}/shots/`).join('; ')}) and what their judges praised (each line's dossier is ${T}/dossiers/<line>.md: ${['desk', 'quote', 'dessau', 'plate', 'listing', 'folio', 'trued', 'manual', 'departures', 'settled', 'sill', 'pocket', 'waypoint'].join(', ')}), and take two to four features from them that would most improve this line, each rebuilt in this line's own colours, type and line so it reads native. Name each with its source design and exact file paths. The ledger (${T}/ledger-index.md, full entries in ${T}/ledger.md) may add one more. Say what the line keeps, what it takes, and what it gives up to make room.`,""")
rep("const KIND_NAME = { refine:", "const KIND_NAME = { cross: 'the CROSS', refine:")
rep("${slot.slot === 'graft' ? `For each borrowed feature", "${['graft', 'cross'].includes(slot.slot) ? `For each borrowed feature")
rep("secondDraft(id, what, slot.slot === 'graft' ? 'graft' : 'brief', slot.parent)",
    "secondDraft(id, what, ['graft', 'cross'].includes(slot.slot) ? 'graft' : 'brief', slot.parent)")
rep('const others = `listed in ${T}/${R}/args.json under "lineages"', 'const others = `listed in ${T}/${R}/args.json under "lines"')
s = s.replace("of the ${lin.name} lineage", "of the line ${lin.name}")
rep("You are the creative lead of one lineage in crossing round ${RL}", "You are the creative lead of one LINE in crossing round ${RL}")
rep("Your lineage: ${lin.name}. Its idea: ${lin.idea}.", "Your line: ${lin.name}, of the ${lin.camp} camp. Its idea: ${lin.idea}.")
s = s.replace("every design of this lineage, in every round it was judged (the main tournament's and this tour's)",
              "every design of this line, in every round it was judged (the main tournament's, the side tour's and the crossing rounds')")
s = s.replace("the other lineages' current designs (${others})", "the other lines' current designs, the other camp's above all (${others})")

# Judging: candidates and anchors.
i = s.index("This heat's lineages: ${heat.lineages")
j = s.index("${LOOK(D, n)}", i)
s = s[:i] + ("This heat's lines: ${heat.lineages.map(x => `${x.name} (${x.idea}): ${x.ids.join(', ')}`).join('; ')}. "
             "${args.final ? `This is the FINAL PANEL before round 14: each line's best design after the two crossing rounds, all in one heat, on one scale. Your scores decide which designs start round 14.` : "
             "`Each line's candidates are its carried design and this round's CROSS of it (its own judges' fixes, plus features taken from the other camp), described in ${D}/stage/candidates.md with what each set out to do and what it took: read it all. The crosses have had one studio crit and one revision. The other heat is judged in parallel by the same lenses.`}\n\n"
             "ALSO score these yardsticks through your lens, on the same scale: ${heat.yardsticks.join(', ')} (00-current is today's page, r13-idea-1 Desk Terminal, Joined, t3-track-refine2 Trued, Relit). They let the heats and rounds be put on one scale.\n\n") + s[j:]
rep("Score every candidate AND both yardsticks 0-10", "Score every candidate AND every yardstick 0-10")
rep("concrete FIXES for at least the best design of each lineage", "concrete FIXES for at least the best design of each line")
rep("and notes (including which grafted features worked and which did not).`",
    "and notes (including which features taken across camps worked and which read pasted, and how the two camps compare).`")
# The finish stage reads the crossing round's files.
s = s.replace("${T}/${R}/results.json (both heats' rankings", "${T}/${R}/results.json (both heats' rankings, with 'linked' scores putting heat b on heat a's scale")
s = s.replace("each lineage's carried designs, its briefs and its dice mutant with the changes rolled", "each line's carried design, its camp and its cross")
s = s.replace("one line per lineage: where it stands (its best mean against today's page and Desk Terminal, Joined in its heat, and against where it stood last round), which of its designs carries on, and why that one won;",
              "one line per line: where it stands (its best linked score against today's page, Desk Terminal, Joined and Trued, Relit, and against last round), whether its cross beat its carried design, and why;")
s = s.replace("which GRAFTED FEATURES took (named, with their source) and which read as pasted, and why; how the dice mutants fared by kind (phosphor, type, graphics, point) and what the rolled changes did;",
              "which FEATURES TAKEN ACROSS CAMPS took (named, with their source) and which read as pasted, and why; how the two camps compare and what each has that the other lacks;")
(X / "cross_stage.js").write_text(s)
print("cross_stage.js", len(s))
