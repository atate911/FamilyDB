export const meta = {
  name: 'phosphor-tour-stage',
  description: 'One stage of a side-tour round of the Phosphor tournament: ledger, design, judge, learn or landing',
  phases: [
    { title: 'Ledger', detail: "the praised features of every lineage and donor, the grafts' menu" },
    { title: 'Plan', detail: "the lineage's creative lead writes its refinement and graft briefs" },
    { title: 'Design', detail: 'refinement, graft, revival and dice-mutant designers, on the real page' },
    { title: 'Second draft', detail: 'a studio crit and one revision' },
    { title: 'Judge', detail: 'one lens over both heats, with today and the main leader as yardsticks' },
    { title: 'Learn', detail: "the round's lessons and the ledger brought up to date" },
  ],
}

// The side tour runs as several of these side by side (a workflow runs two agents at once on this
// machine): one design workflow per lineage, one judge workflow per lens, one finish workflow.
// tour.py sets up each round, renders, tallies and chooses between them.
const H = '/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness'
const T = `${H}/tour`
const STAGE = args.stage
const N = args.roundNo
const R = args.round

const OWNER = `FamilyDB is a family planning app; its web page's look is called "Phosphor": a modern app lit the way an old green-screen monitor was. The owner likes the CRT theme and the Phosphor interface and wants to KEEP the green on black and the bright green phosphor (#6dff9c) as the signature colour. In their words: "all the bright green on a black background is a little bright and too contrasty"; it "just needs a little more variation"; and "there could also be some other subtle and tasteful colors used to augment the green so it doesn't appear completely monochromatic. The CRT is just a theme, not a strict limit." (Family feedback on the original: "that looks like the Matrix".) And, after seeing round 1's winners, the owner's latest word, which weighs above everything else: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." And: "small visual enhancements or refinements, even if there is a degree of randomness (changing in size, spacing, fonts, text size, orientation, headers/labels, icons, or anything else to improve visual appeal) are welcome, but not necessary. We are mimicking natural selection here." And the owner's direction for what the changes should be: \"Bright green where it needs to be to maintain the motif, more grounded coloration elsewhere.\" (the bright #6dff9c kept where the Phosphor motif needs it: the mark, the primary button, the glowing key word, focus, live lights, the monitors; elsewhere grounded, natural, material, lower-chroma colour in solid things with a job, not more glow or neon). And on rules: \\"For the purposes of this experimentation, treat the design constraints like README and other .md files as loose guidelines, not hard and fast rules. They were written to help, not restrict.\\" So docs/STYLE.md, the harness README and lessons.md are guidelines that may be broken when the page is better for it; only the harness's hard checks refuse a palette. And: \\"I enjoy typesetting/pagination in general and will appreciate even minor optimization of typography.\\" (typesetting counts: hierarchy, scale, measure, rhythm, tracking and leading, figures, pairing). The Phosphor Interface is the whole way the app is presented, not only its colours: the overall layout; the kinds of interface elements; the whitespace (darkspace) around each element and the pacing; how design elements relate; typefaces, bold and italic, and how titles, headers and labels are treated in size and colour; headers and footers; iconography and how icons relate to the type; graphics and their sparsity; the weight of lines, boxes and delimiters; rounding, shadows, glow and echoes (afterglow); pills, alignment and shades; pagination, scrolling and animation; the controls (dropdowns and select menus, radio buttons, checkboxes, free-form fields, scroll bars, focus and hover states); how a person uses the page (sight lines, clicks, moving between keyboard and mouse, taking in at a glance what the page is presenting); everything a senior interface engineer would weigh together; and most importantly the feel and personality of the presentation. The winner of this tournament defines the Phosphor Interface design standard for the whole app: so a coherent SYSTEM wins over a one-off effect (colours and faces with clear jobs, a type system with steps, rules that would hold on any page, Plans, To do and Settings included, not only the ones in the sheets). And the owner's latest word, after nine rounds: \"I'm concerned that in the goal of great interface design we've gained a lot but also lost a little of the unique effect of the original phosphor interface. I'd suggest bringing some of that back.\" That unique effect is the original page's light, a green-screen tube's: lit words and marks with a layered halo, the green screens' bloom, blur and scanlines, glowing dots on the black, highlights and afterglow. Its exact CSS is catalogued in ${H}/phosphor_kit.md. Bring it back where the phosphor is, and keep what the tournament gained: grounded colour elsewhere, a calmer page, a better structure. It is light where attention belongs, not glare across the page.`

const LINEAGE_LIST = `the track series, led by Track Diagram (round 10: the family's week as a signal box's illuminated track diagram, steel lines on slate with a lamp at each stop), with Track Diagram Aglow (round 13) beside it; Night Timetable (round 10: Vera's conversation as the line the page hangs from, the chat a timetable); Pocket Timeline (round 11: Home ordered as time on one spine, NOW to NEXT to LATER); Figure Ground (round 10: every section led by a figure drawn from its own data); Flight Console (round 11: a readout strip, the weeks as a flight plan, an annunciator); and Videotex Switchboard (round 12: Home as the map of every page, each a cell with a lamp and a count)`

const TITLE = `THE GREETING'S TITLE. The owner, during this tour: "I don't really like the title of 'What's on your mind?' as it really doesn't relate that well to the job the application is trying to do. Please iterate on better titles as well." The title is the question over the box the family writes to Vera in, on Home (templates/_ask.html: <h1 class="ask-question"><label for="text">What’s on your <span class="glow">mind</span>?</label></h1>). It is the box's label, so keep it the label (or give the box an aria-label with the same words). FamilyDB's job is the family's planner, run by telling Vera: weekends and outings, ideas worth keeping, plans on the shared calendar, things to do and their reminders, the kids' wish lists. A good title says that job in the family's own voice, reads as an invitation to tell her something, fits one line on a phone, and lights ONE word as the glowing key word (the phosphor signature "mind" carried). Every new design in this tour, except a dice mutant (which keeps its parent's words), proposes its own title, made for its lineage (a timetable, a console, a manual, a switchboard can each ask in its own way), and gives it in its "title" field with why. Refinements keep the best title their lineage has found so far or improve on it; the judges say which titles work. The box's placeholder ("Plans for the weekend, an idea to keep, a reminder, the calendar…") comes from code and stays.`

const TOUR = `THIS IS A SIDE TOUR of the Phosphor tournament, run at the owner's request after thirteen rounds. A review of the whole history found designs whose ideas the tournament passed over: strong structures that lost on faults that are easy to fix (tracked capitals, small targets, ISO dates, a costume colour, a missing glow), not on their ideas. Six of them come back as LINEAGES and each is developed over three rounds as seriously as the tournament developed its winners: ${LINEAGE_LIST}. Each round every lineage carries on its best design (the track series its best two) and gets new entrants: a REFINEMENT (the lineage's own judges' fixes, from every round it has been judged in, a studio crit and one revision), a GRAFT (the best FEATURES of the other lineages and of donor designs, taken feature by feature and rebuilt in the lineage's own terms, never the whole package; also a crit and a revision), and a DICE MUTANT (random changes rolled by the tournament's own dice: phosphor, type, graphics or a point mutation). In round 1 the track series also has a REVIVAL of its first line language. The field is judged in two heats of three lineages, by the tournament's eight lenses, each lens judging both heats; each heat also carries two yardsticks, today's page and Desk Terminal, Joined (the main tournament's leader after round 13), so the heats and the rounds can be read together. Each lineage carries on whichever of its designs scores best. After three rounds every lineage's final is judged beside where it started. The tour also iterates the greeting's title (below).\n\n${TITLE}`

const MAIN_LINE = `Do not import the main line's defining structures: Desk Terminal's cased terminal column standing beside a desk, Evening Listing's programme-listing bands with a head column, Backlit Plate's cut matte plate over one screen, Quote Board's one big quote per section. This tour exists to develop other ideas as far as they go. The small, universal fixes every panel asked of everyone (44px targets, sentence-case controls and links, late shown in words, tabular figures, underlined links, one control per filter, a strong "here") are free to take.`

const NUM = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen']

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    name: { type: 'string', description: 'two or three words, as written in the palette file' },
    tagline: { type: 'string' },
    concept: { type: 'string', description: '2-3 sentences: the idea and the feeling' },
    companions: { type: 'string', description: 'which colours keep the green company, and where each goes' },
    decisions: { type: 'array', items: { type: 'string' }, description: 'the main choices and why, including what you took from the brief, the judges or the dice, and how you bent any of it' },
    title: { type: 'string', description: "the greeting's title exactly as it reads on Home, with the lit word in *asterisks*, and in a sentence why it says FamilyDB's job (a dice mutant gives its parent's)" },
    floorsFailed: { type: 'integer' },
    measures: { type: 'string', description: 'final ink_on_bg, brand_on_bg, green share and hue entropy, small targets on Home, anything the check flagged' },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['id', 'name', 'tagline', 'concept', 'companions', 'decisions', 'title', 'floorsFailed', 'measures', 'strengths', 'weaknesses'],
}
const REVISED_SCHEMA = {
  ...DESIGN_SCHEMA,
  properties: { ...DESIGN_SCHEMA.properties, revisions: { type: 'array', items: { type: 'string' }, description: 'what you changed in this revision, and which notes you declined and why' } },
  required: [...DESIGN_SCHEMA.required, 'revisions'],
}
const CRIT_SCHEMA = {
  type: 'object',
  properties: {
    keep: { type: 'array', items: { type: 'string' }, description: 'what works and must stay' },
    notes: { type: 'array', items: { type: 'string' }, description: 'the four to eight most important concrete fixes, most important first: page, element, token or selector' },
    reading: { type: 'string', description: 'the idea as you see it on the page, in two sentences' },
  },
  required: ['keep', 'notes', 'reading'],
}

const COPY = (D, pid, id) => `copy ${D}/palettes/${pid}.json to ${D}/palettes/${id}.json (set "id": "${id}"), and when ${pid} has its own markup or sheet (${D}/variants/${pid}/), copy that whole folder to ${D}/variants/${id}/; if the palette names a "sheet", point it at your copy (variants/${id}/sheet.css)`

const HOW = (D, key, id, parent, o = {}) => `How to work:
1. Read ${D}/README.md (the palette format, "A palette's own markup", "A clean sheet", "Graphics, pictures and icons", "The phosphor's light", "Typesetting", ./check.sh, the floors, how to sample a pixel), ${T}/dossiers/${key}.md (every judge's words on your lineage, in every round, with the fixes they asked for), ${T}/lessons.md (the side tour's lessons so far) and ${H}/lessons.md (the main tournament's: follow what they have learned unless your design has a reason not to, and then say the reason). ${H}/phosphor_kit.md has the original page's light, each effect with its exact CSS.
2. Look at today (${D}/out/00-current/shots/), your parent's shots (${D}/out/${parent}/shots/: home, home-phone, chat, ideas, plans, todo, status, settings, form, general) and the main tournament's leader (${D}/out/r13-idea-1/shots/) for the bar a design has to reach.
3. ${o.start}${o.only ? " Make only these changes; everything else stays the parent's, so the judges can tell what the changes did." : ''} Iterate with ./check.sh run from ${D} (pages as you need while iterating, for example ./check.sh palettes/${id}.json home chat), fix every FAIL, and LOOK at the screenshots with the Read tool on every page at least twice, cropped and enlarged where it matters: home, home-phone, chat, ideas, plans, todo, status, settings and form.${o.only ? '' : ' The owner enjoys typesetting: make small typographic refinements wherever they truly improve the page.'}
4. Finish with a full render (./check.sh palettes/${id}.json, no page list) that passes every floor.

Rules: work only in ${D}; write only ${D}/palettes/${id}.json and ${D}/variants/${id}/; read anything else you need (the other designs in ${D} and in the other heat's folder, the donors in ${T}/donors/, the main rounds in ${H}/rounds/) but never edit it; never edit /home/user/FamilyDB; do not start or stop the server on port 8099. The owner's signature is the exact #6dff9c on a green-black ground: keep it unless your idea is better without it, and then say why. Be honest in the weaknesses.`

// ---- Ledger: the grafts' menu, built once before round 1 ------------------------------------------
const FEATURE_SCHEMA = {
  type: 'object',
  properties: {
    features: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          feature: { type: 'string', description: 'a short name for the device' },
          kind: { type: 'string', enum: ['drawing or diagram', 'component', 'page structure', 'state marking', 'typography', 'light effect', 'colour or material', 'control', 'motion', 'wording', 'icons or pictures'] },
          source: { type: 'string', description: 'the design id, as in the ranking' },
          sourceName: { type: 'string' },
          round: { type: 'integer' },
          standing: { type: 'string', description: "the design's standing: mean, rank of how many, e.g. '5.29, #11 of 12'" },
          what: { type: 'string', description: 'what it is, concretely: page, element, how it is drawn and what it does' },
          files: { type: 'string', description: 'where it lives: exact paths (palette json css, variants/<id>/templates/*.html, variants/<id>/sheet.css, static pictures) and the selectors or template names' },
          shot: { type: 'string', description: 'the screenshot path that shows it best' },
          praise: { type: 'string', description: "who praised it and how strongly (lens, score, a short quote), or 'not remarked by the judges'" },
          caveats: { type: 'string', description: 'what failed with it or around it, and how to make it work elsewhere' },
          suits: { type: 'string', description: 'which of the six lineages (track, timetable, pocket, figure, console, switchboard) it would suit, and how' },
        },
        required: ['feature', 'kind', 'source', 'sourceName', 'round', 'standing', 'what', 'files', 'shot', 'praise', 'caveats', 'suits'],
      },
    },
  },
  required: ['features'],
}
if (STAGE === 'ledger') {
  phase('Ledger')
  const out = await parallel(args.groups.map(g => () => agent(`You are a SCOUT for a side tour of the Phosphor tournament. The owner asked for this sweep in these words: "I also think a lot of failed designs have one or two elements that were fantastic, creative, and could work even better in a different design, and we should recognize them and incorporate these ideas into other designs that might work better as a whole, but lose by ignoring small good ideas that were lost." And: "There's a lot of creativity and very cool ideas in some of the low-rated pages that should not get lost."

${OWNER}

${TOUR}

Your share: ${g.rounds.map(n => `round ${n}`).join(' and ')} of the main tournament. For each round: its full judging record is ${g.rounds.map(n => n === 1 ? `${H}/round1/results.json` : `${H}/rounds/r${n}/results.json`).join(' and ')} (every design's ranking, each judge's score and reason, their fixes, promise votes and notes; "designs" holds what each new design set out to do), and the round's section of ${H}/lessons.md ("## Round N": what won, what lost, the FAILED REACHES). ${T}/gallery/index.json gives, for every design, where its screenshots are ("shots": home, home-phone, chat, ideas, plans, todo, status, settings, form) and where its files are ("palette", "variants").

Go through EVERY design of your rounds, the low-rated ones above all: open its screenshots (at least home, chat, ideas, status and todo; crop and enlarge where a detail matters) and read what every judge said of it. Then list its standout ELEMENTS: single devices that are fantastic, creative or unusually well made and could work even better in another design. One device each, never a whole design: a drawing or diagram, a component, a page structure, a way of marking state, a typographic device, a light effect, a colour or material idea with a job, a control, a motion, a wording. Look past the package: a design that sank on its colour, its capitals or its targets can still hold the best chat, the best status panel or the best page head the tournament made. Include what the judges praised, and also what you can SEE is good that the judges passed over. Leave out what is ordinary, and what the main line's leaders already carry (Desk Terminal's cased terminal column, Evening Listing's programme bands, Backlit Plate's cut plate, Quote Board's big quote).

For each element: where it lives, exactly (the palette's css selectors, the template file names, the sheet.css rules, pictures in its static folder), so a designer can study it and rebuild it; the screenshot that shows it best; the praise (lens and score, or a short quote; "not remarked by the judges" if you found it yourself); the caveats (what failed with it and how to make it work); and which of the six lineages it would suit, and how. Change no file.`,
    { label: `scout:${g.rounds.join('+')}`, phase: 'Ledger', schema: FEATURE_SCHEMA })))
  return { stage: 'ledger', features: out.filter(Boolean).flatMap(o => o.features) }
}

// ---- Design: one lineage's planner, briefs and mutant ----------------------------------------------
const LENS_ORDER = ['feedback', 'soul', 'style', 'system', 'interaction', 'type', 'usability', 'skeptic']
const SLOT_TEXT = {
  refine: (b) => `REFINEMENT of ${b.parent} (${b.parentName}): keep its idea, its structure and its mood, and make it as good as the judges' words say it could be. Apply their concrete fixes, most-cited first (name each and which lenses asked); fix every usability fault they found (small targets, tracked capitals on controls and links, ISO dates, late not shown, a one-sided chat, a lost task: whatever sank it); bring the phosphor light back where its soul scores say it was lost (${H}/phosphor_kit.md); and carry the idea through every page (Plans, To do, Settings and the form too). It may borrow a small feature where that answers a fault, but its job is to perfect this idea, not to add others.`,
  refine2: (b) => `REFINEMENT of the lineage's second carried design, ${b.parent} (${b.parentName}), on the same terms as the first: keep its idea and apply its own judges' fixes, most-cited first, so the lineage's two lines both get better and stay distinct.`,
  graft: (b) => `GRAFT onto ${b.parent} (${b.parentName}): cross-pollination. Choose two to four FEATURES (not whole designs) from the ledger (${T}/ledger-index.md, with full entries in ${T}/ledger.md: single devices from every design the tournament ever made, found by scouts who looked at every page), the other lineages' current designs and the donors: the ones that would most improve this lineage and fit its idea. At least one must be a GEM (the index's first part): a small good idea from a design that finished in the lower half of its round and was lost with its package (the owner: "a lot of failed designs have one or two elements that were fantastic, creative, and could work even better in a different design"). A design's files and screenshots are listed in ${T}/gallery/index.json. For each, name its ledger number, its source design and where it lives (exact paths: palette css, templates, sheet.css), what it replaces or where it goes on which pages, and why it fits; the designer rebuilds each in this lineage's own colours, type and line, so it reads as native, not pasted. The lineage's idea must stay recognisable at a glance. ${MAIN_LINE} The graft may also apply the lineage's most important fixes.`,
  revival: (b) => `REVIVAL on ${b.parent} (${b.parentName}): the track series began as Signal Box (round 7, r7-idea-2, files in ${T}/donors/), whose mimic-line language was much praised and then mostly lost as the line narrowed (Signal Lines, round 9, r9-idea-4, carried it through every page and was marked down for decoration). Rebuild Track Diagram with that line language complete and carried through every page: the Coming up track from a lit NOW lamp, To do's timetable margin with a lamp at each item, the chat hung from Vera's mark and ending in a ring at the box, the page heads ringed and bracketed to hold their controls, the setup steps as a track, and a clear mark under the current page in the bar. Answer what sank it before, from the dossier: draw a line only where there is order (time, sequence, belonging), keep ticks square so controls never look like timeline stops, make "here" strong, keep every target 44px, and light the live things (the NOW lamp, the lit run of track, "mind", Send) with the tube's real halo.`,
}
if (STAGE === 'design') {
  const K = args.key
  const lin = args.lin
  const D = lin.dir
  const others = `listed in ${T}/${R}/args.json under "lineages" (each one's carried designs and its heat folder "dir": files in <dir>/palettes/ and <dir>/variants/, shots in <dir>/out/<id>/shots/)`
  const CARRIED = lin.carried.map(c => `${c.id} (${c.name})`).join(', ')
  const PLAN_SCHEMA = {
    type: 'object',
    properties: {
      reading: { type: 'string', description: "your reading of the lineage's judging so far: what the judges love, what sank it, what would make it win" },
      briefs: {
        type: 'array', minItems: lin.briefs.length, maxItems: lin.briefs.length,
        items: {
          type: 'object',
          properties: {
            slot: { type: 'string', enum: lin.briefs.map(b => b.slot) },
            name: { type: 'string', description: 'a working name, two or three words' },
            hypothesis: { type: 'string', description: 'why this should beat the lineage\'s carried design' },
            brief: { type: 'string', description: 'what the designer should build, concretely, page by page and element by element' },
            borrows: { type: 'string', description: 'the judges\' fixes it applies (with which lenses asked), and for a graft each feature with its source design and exact file paths' },
            avoids: { type: 'string', description: 'which criticisms it answers' },
            title: { type: 'string', description: "the greeting's title this brief proposes (lit word in *asterisks*), and why it says FamilyDB's job; the briefs' titles differ" },
          },
          required: ['slot', 'name', 'hypothesis', 'brief', 'borrows', 'avoids', 'title'],
        },
      },
    },
    required: ['reading', 'briefs'],
  }
  const runPlan = () => agent(`You are the creative lead of one lineage in round ${N} of a side tour of the Phosphor tournament.

${OWNER}

${TOUR}

Your lineage: ${lin.name}. Its idea: ${lin.idea}. Carried into this round: ${CARRIED}: their files are ${D}/palettes/<id>.json and ${D}/variants/<id>/, their fresh renders ${D}/out/<id>/shots/.

Read, in full:
- ${T}/dossiers/${K}.md: every judge's words on every design of this lineage, in every round it was judged (the main tournament's and this tour's), with the fixes they asked for. This is your main source: all of it informs this round.
- ${T}/lessons.md (the tour's lessons so far) and ${H}/lessons.md (the main tournament's; its FAILED REACHES say what sank each wild idea and how to try again).
- ${T}/ledger-index.md, in full: the graft's menu, one line per feature (270 single devices from every design the tournament ever made, found by scouts who looked at every page; the GEMS come from designs that finished in the lower half of their round). For each feature you consider, read its full entry (files, screenshot, praise, caveats) in ${T}/ledger.md (search for its number, e.g. '### L042'); ${T}/ledger-for-${K}.md holds the full entries of those the scouts said would suit this lineage (large: search it rather than read it all). ${T}/dossiers/donors.md has the donors' full judging.
Look at: the carried designs' shots on every page (home, home-phone, chat, ideas, plans, todo, status, settings, form), today's (${D}/out/00-current/shots/), the main tournament's leader (${D}/out/r13-idea-1/shots/) for the bar it has to reach, the other lineages' current designs (${others}), and the donors (${T}/donors/out/<id>/shots/).

Then write ${NUM[lin.briefs.length]} briefs, one for each slot:
${lin.briefs.map(b => `- slot "${b.slot}": ${SLOT_TEXT[b.slot](b)}`).join('\n')}

Every brief starts from its parent's files (the designer copies them) and may change its markup, stylesheet, pictures and icons. Each keeps the owner's asks and the harness's hard checks, may break any written guideline when the page is better for it, and must be concrete enough to build: name pages, elements, tokens and selectors. The briefs must differ from each other. Each also proposes the greeting's title (see THE GREETING'S TITLE above), and the titles of your briefs differ, so the judges can compare them. ${N > 1 ? `Every title the tour has tried so far, with the designs that carried it, their scores and what the judges said of the titles, is in ${T}/titles.md: read it. A refinement keeps the best title its lineage has found or improves on it; at least one of your briefs proposes a title NOT yet tried, so the search keeps widening instead of settling early on two phrasings.` : 'A refinement starts from the best title its lineage has found.'}`,
    { label: `plan:${R}:${K}`, phase: 'Plan', schema: PLAN_SCHEMA })

  const secondDraft = (id, what, kind, parent) => async (draft) => {
    if (!draft) return null
    try {
      const crit = await agent(`You are a studio critic in round ${N} of a side tour of the Phosphor tournament.

${OWNER}

${TOUR}

A designer has just made a first draft of ${id} (${draft.name}), ${what}. Their idea: ${draft.concept} Companions: ${draft.companions} Their own weaknesses: ${draft.weaknesses.join(' | ')}

Your job is to make THIS design as good as it can be before the panel judges it. ${kind === 'phosphor'
        ? `Keep it true to its parent: judge whether the original Phosphor light is really back (${H}/phosphor_kit.md has each effect with its exact CSS; compare with today's shots, cropped and enlarged): does each lit thing read as light from a tube at 100%, the halo visible, the screens with bloom and scanlines, the dots glowing on the black? Does the change show at a glance beside the parent (${D}/out/${parent}/shots/) at half size, or only up close? Does it stay scarce, with no glare, the rest of the page grounded and every word still easy to read? Do not undo the parent's design.`
        : kind === 'graft'
        ? `Keep it true to its lineage and its brief: judge whether each grafted feature has been made the lineage's own (its colours, type and line) and earns its place, or reads pasted on; whether the lineage's idea is still recognisable at a glance beside its parent (${D}/out/${parent}/shots/); and how well the brief is carried out on every page. Do not pull it towards the other designs or towards today's page.`
        : `Keep it true to its lineage and its brief: judge how fully and how well the brief is carried out on every page, whether the judges' fixes it set out to apply really landed (${T}/dossiers/${K}.md has them), and what would make it better. Do not pull it towards the other designs or towards today's page.`}

Look at its full-size shots, ${D}/out/${id}/shots/ (home, home-phone, chat, ideas, status, plans, todo, settings, form and general, and the controls and focus shots), beside its parent's (${D}/out/${parent}/shots/) and today's (${D}/out/00-current/shots/). Its tokens are ${D}/palettes/${id}.json and its markup ${D}/variants/${id}/. The floors and the palette roles are in ${D}/README.md; the pitfalls earlier panels found are in ${H}/lessons.md and ${T}/lessons.md.

Say what works and must stay, then the four to eight most important concrete fixes, most important first: where the idea is not carried through every page (Plans, To do, Settings and the form too), the hierarchy and sight lines, legibility, whether colour is grounded away from the lit green, the light where the phosphor is, the typesetting, the controls and focus states, the targets, and anything broken, clipped or awkward on the phone. Name the page, the element and the token or selector. Change no file; do not run ./check.sh.`,
        { label: `crit:${id}`, phase: 'Second draft', schema: CRIT_SCHEMA })
      if (!crit) { log(`${id}: the crit failed; judged on its first draft`); return { ...draft, secondDraft: 'failed' } }
      const rev = await agent(`You are the designer of ${id} (${draft.name}) in round ${N} of a side tour of the Phosphor tournament.

${OWNER}

${TOUR}

${id} is ${what}. Your first draft is ${D}/palettes/${id}.json, with its markup in ${D}/variants/${id}/. What it set out to be: ${draft.concept} Its companions: ${draft.companions} Its main decisions: ${draft.decisions.join(' | ')}

A studio critic has looked at it on every page. Their reading: ${crit.reading}
What works and must stay:
${crit.keep.map(k => `- ${k}`).join('\n')}
The fixes, most important first:
${crit.notes.map(k => `- ${k}`).join('\n')}

Make one revision. Keep the idea; act on the notes that make the page better (you may decline a note that would betray the idea, and say why); look at the pages again before you finish.

${HOW(D, K, id, parent, { start: `Revise ${D}/palettes/${id}.json and ${D}/variants/${id}/ in place, keeping its id.` })}

Return the whole design as it now stands, with "revisions" saying what you changed and which notes you declined.`,
        { label: `revise:${id}`, phase: 'Second draft', schema: REVISED_SCHEMA })
      if (!rev) { log(`${id}: the revision failed; its files may be part-revised, so it is rendered again before judging`); return { ...draft, secondDraft: 'failed' } }
      return { ...rev, id, crit: crit.notes, firstDraft: { name: draft.name, concept: draft.concept } }
    } catch (e) {
      log(`${id}: second draft stopped (${e}); judged as it stands`)
      return { ...draft, secondDraft: 'failed' }
    }
  }

  const KIND_NAME = { refine: 'the REFINEMENT', refine2: 'a REFINEMENT of the second carried design', graft: 'the GRAFT', revival: 'the REVIVAL' }
  const briefChain = (slot, b) => {
    const id = `${R}-${K}-${slot.slot}`
    const what = `${KIND_NAME[slot.slot]} of the ${lin.name} lineage, built on ${slot.parent} (${slot.parentName}) from this brief. ${b.name}: ${b.hypothesis} Brief: ${b.brief}`
    return agent(`You are a designer in round ${N} of a side tour of the Phosphor tournament.

${OWNER}

${TOUR}

Your design is ${KIND_NAME[slot.slot]} of the ${lin.name} lineage (its idea: ${lin.idea}), briefed by the lineage's creative lead from every judge's words on it:

Working name: ${b.name}
Hypothesis: ${b.hypothesis}
Brief: ${b.brief}
Borrows: ${b.borrows}
Answers: ${b.avoids}
Proposed title: ${b.title}

Build it faithfully, improving on the brief where what you see on the page tells you to. ${slot.slot === 'graft' ? `For each borrowed feature, first read its source's files and look at its shots (${T}/gallery/index.json lists every design's files and screenshots; the donors are rendered in full in ${T}/donors/, the other lineages in their heat folders), then rebuild it in this lineage's own colours, type and line, so it reads as native. ${MAIN_LINE}` : ''}

Your id: ${id}.

${HOW(D, K, id, slot.parent, { start: `First ${COPY(D, slot.parent, id)}. Give it its own "name" of two or three words and a "tagline". Then build the brief on every page it reaches.` })}`,
      { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
      .then(draft => secondDraft(id, what, slot.slot === 'graft' ? 'graft' : 'brief', slot.parent)(draft))
  }

  const mutantChain = () => {
    const m = lin.mutant
    const id = m.id
    const copy = COPY(D, m.parent, id)
    const body = m.kind === 'graphics'
      ? `Your page is a GRAPHICS MUTANT: the lineage's design ${m.parent} (${m.parentName}) with only its graphics, pictures and iconography changed, rolled by the dice, so the panel can see what they alone do to it. Big changes are welcome. The changes the dice rolled, one major and one or two minor:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then draw the changes as real assets, well made and in one style, carried through every page they reach. When a rolled change touches the icons, redraw ${D}/variants/${id}/static/icons.svg, starting from your parent's sprite when it has one, otherwise from the real /home/user/FamilyDB/src/familydb/web/static/icons.svg, and keep every icon id. Put SVG (or PNG and WebP) pictures beside it, placed through your templates or loaded by your css. Read README "Graphics, pictures and icons". Change nothing else: the colours, type and layout stay the parent's, except where a picture needs room; say where. If a change hurts the page, make the nearest version that does not, and say so.`
      : m.kind === 'type'
      ? `Your page is a TYPE MUTANT: the lineage's design ${m.parent} (${m.parentName}) with only typographic changes, rolled by the dice, so the panel can see what the typesetting alone does to it. The changes the dice rolled, one major and two minor:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then make these changes fully and well, as a careful typesetter would: carry each one through every page and every level it reaches (titles, heads, body, labels, figures, controls, and the tubes when a change reaches them), and tune what a new face needs to sit well (size, leading, tracking, weights, figures). Faces come from the library in README "Refinements beyond colour". Change nothing else: the colours, the layout and every other rule stay the parent's, except where a type change needs the markup; say where. If a change hurts the page, make the nearest version that does not, and say so.`
      : m.kind === 'phosphor'
      ? `Your page is a PHOSPHOR MUTANT: the lineage's design ${m.parent} (${m.parentName}) with the original Phosphor page's light brought back, as the owner asks above, so the panel can see what a green-screen tube's light does for it. What to bring back:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy}; give it a "name" of two or three words that says it is a variation, and a "tagline". Read ${H}/phosphor_kit.md: the original's effects, each with its exact CSS, where it was used and how a design re-creates it. Look at your parent's shots beside today's, cropped and enlarged, to see what it lost. Then bring the light back wherever this design shows phosphor (its monitors and screens, the lit states, the machine's words and readouts, the live dots and lamps, the mark and the primary actions), in the parent's own terms: its green, its cases, its type, its lines. The two emphases above go furthest. Keep everything else the parent's. Keep the light scarce: it goes where the phosphor is and attention belongs; a halo too faint to see at 100% is lost, and glare or text blurred past easy reading is a fault. The change must show at a glance beside the parent at about half size, not only up close. Keep each effect's reduced-motion and more-contrast behaviour as the kit gives it. If an effect hurts the page, make the nearest version that does not, and say so. A studio critic will look at it afterwards and you will make one revision.`
      : `Your page is a MUTANT: the lineage's design ${m.parent} (${m.parentName}) with a few RANDOM changes, the way evolution tries a variation on something that already works. The changes the dice rolled, one of colour, one of structure and one of type:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then make these changes fully and visibly, with taste: carry a structural change through every page it touches, changing the markup where it needs to. Keep everything else the parent has, except what the changes or the floors force. If a change cannot be made without hurting the page, make the nearest version that does not, and say so.`
    const first = agent(`You are a designer in round ${N} of a side tour of the Phosphor tournament.

${OWNER}

${TOUR}

${body}

Your id: ${id}.

${HOW(D, K, id, m.parent, { start: `Make ${D}/palettes/${id}.json as above.`, only: true })}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
    return m.kind === 'phosphor'
      ? first.then(draft => secondDraft(id, `a phosphor mutant: ${m.parentName} (${m.parent}) with the original Phosphor page's light brought back (${m.changes.slice(1).join('; ')})`, 'phosphor', m.parent)(draft))
      : first
  }

  phase('Design')
  const jobs = []
  if (args.mutant) jobs.push(() => mutantChain().then(d => d ? [d] : []))
  let plan = null
  if (args.plan) jobs.push(async () => {
    plan = await runPlan()
    if (!plan || !plan.briefs) { log(`${K}: the planner failed; no briefs this round`); return [] }
    const bySlot = Object.fromEntries(plan.briefs.map(b => [b.slot, b]))
    const done = await parallel(lin.briefs.filter(s => bySlot[s.slot]).map(s => () => briefChain(s, bySlot[s.slot])))
    return done.filter(Boolean)
  })
  const designs = (await parallel(jobs)).filter(Boolean).flat()
  log(`${K}: ${designs.length} new designs (${designs.filter(d => d.revisions).length} revised after a crit); floors failed: ${designs.filter(d => d.floorsFailed > 0).map(d => d.id).join(', ') || 'none'}`)
  return { stage: 'design', designs, plans: plan ? { [K]: plan } : {} }
}

// ---- Judge: one lens over both heats ---------------------------------------------------------------
const LENSES = [
  { key: 'feedback', title: 'The owner\'s judge', prompt: `You are the OWNER'S JUDGE, the panel's stand-in for the owner. Read ${H}/owner_judge.md first: the owner's own first-hand reactions to earlier winners, which calibrate you to the owner's taste (they are one judge's opinion among the panel's, for you alone, not rules; still score every candidate on its merits as you see it). Then judge on the owner's words: less bright, less contrasty, more variation, subtle tasteful colours augmenting the green so it is not completely monochromatic, the bright green on green-black still unmistakably the signature, and above all the owner's direction: bright green where the motif needs it, more grounded coloration elsewhere (natural, material, lower-chroma colour in solid things across the page, not more glow).` },
  { key: 'soul', title: 'Phosphor soul', prompt: `Judge whether each keeps what the owner likes: the CRT theme and the Phosphor interface, lit and alive, the monitors still real 1980s green screens, glow scarce and meaningful (read "Why the green jumps" in /home/user/FamilyDB/docs/STYLE.md, as a guide to what the owner likes, not a rule). Calmer is wanted, lifeless is not; the CRT is a theme, not a strict limit.` },
  { key: 'style', title: 'Creativity and style', prompt: `Judge as an art director with taste: a fresh, considered, memorable identity with a clear mood; companions inspired rather than predictable; would the family say "oh, that's lovely"? Penalise the generic (well-known editor themes, stock dark mode), the timid and the gimmicky.` },
  { key: 'system', title: 'Design system (a senior interface engineer)', prompt: `Judge as a senior interface engineer weighing the whole system together: layout and the kinds of elements, darkspace and pacing, the weight of lines, boxes and delimiters, rounding, shadows, glow and echoes, pills, alignment and shades, headers and footers, iconography and how it relates to the type, graphics and their sparsity, the controls (selects, checkboxes, fields, focus, hover, scroll bars: see the details strips), motion, and whether it all reads as ONE coherent system that would hold on any page of the app (Plans, To do, Settings and the form included). Beautiful, current and comfortable for a family's daily use; links that look like links; nothing that reads as a warning when it is not one.` },
  { key: 'interaction', title: 'Interaction and comprehension', prompt: `Judge how a person uses and understands each page: sight lines (does the eye go title, then the one action, then the content?), what a glance tells you the page is presenting (use the squint strips and sheets/squint.png: blurred, is the hierarchy still clear?), the size and spacing of click targets (health.json counts those under 44px), moving between keyboard and mouse (the Tab order in health.json, the focus rings in the details strips), how clearly controls say what they do and what state they are in, and how quickly a family member finds what they came for. Compare each with today's page.` },
  { key: 'type', title: 'Typography and typesetting', prompt: `Judge as a typographer who loves typesetting (the owner does, and appreciates even minor typographic improvements): the hierarchy of titles, headings, body, labels and figures; the type scale and its rhythm; line length (measure) and leading; tracking at each size; how the faces pair and whether each does a job; numerals (tabular in lists and tables, figures that line up); how labels, dates and small text are set; spacing between blocks (vertical rhythm); anything a careful typesetter would fix. Compare each with today's typesetting (00-current): reward real improvements, even small ones; penalise fonts that fight the Phosphor feel, reduce legibility, or are change for its own sake. Look closely at full-size shots, not only the sheets.` },
  { key: 'usability', title: 'Usability (a family member using it)', prompt: `Judge as a usability specialist who walks through what the family actually does, on each candidate's own pages: send Vera a message and read her reply; see what is on this weekend; add an idea and find it again; show only the restaurants; tick off a to-do and see what is overdue; find a date on Plans; open a kid's wish list; change a setting; sign in. For each task, ask whether a family member using it for the first time sees where to start, gets it done in few steps, can tell what state things are in, and can recover from a mistake. Use the full-size shots, the phone shots, the new-idea form and the settings pages, the details strips (a field being typed in, a ticked box, an open select, focus rings) and health.json (the Tab order, the targets under 44px). Weigh legibility for tired eyes on a phone at night (the measured contrast and text sizes, now reported rather than refused), consistency (one kind of control looks and behaves one way everywhere), and anything a design removed or hid (listed in the candidates' notes): a removal that simplifies is a gain, one that loses a task the family needs is a real cost. Beauty and novelty are the other lenses' concern: a striking design that is hard to use scores low here, a plain one that is effortless scores high. Say concretely which task breaks, on which page, and how to fix it.` },
  { key: 'skeptic', title: 'Adversarial skeptic', prompt: `Be the skeptic: hunt for what is wrong in each (muddy or bronze washes, a greyed or tinted ground, a signature without spark, companions too faint or clashing, links that do not look like links, anything that reads as a warning or a costume, the Matrix, an editor theme, near-duplicates). Give real, spread-out scores.` },
]
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    scores: {
      type: 'array',
      items: { type: 'object', properties: { id: { type: 'string' }, score: { type: 'number', description: '0-10' }, why: { type: 'string' } }, required: ['id', 'score', 'why'] },
    },
    top4: { type: 'array', items: { type: 'string' }, description: 'ids, best first' },
    promise: { type: 'array', items: { type: 'string' }, maxItems: 3, description: 'up to three ids whose idea is most worth developing further, whatever their score now' },
    fixes: {
      type: 'array',
      items: { type: 'object', properties: { id: { type: 'string' }, suggestion: { type: 'string' } }, required: ['id', 'suggestion'] },
    },
    titles: { type: 'string', description: "which greeting titles in this field say FamilyDB's job best and which fail, and why; name the best one or two" },
    notes: { type: 'string' },
  },
  required: ['lens', 'scores', 'top4', 'promise', 'fixes', 'titles', 'notes'],
}
const lensOf = (key) => {
  const l = LENSES.find(x => x.key === key)
  return key === 'feedback' ? { ...l, prompt: l.prompt.replace(`${H}/owner_judge.md`, `${T}/owner_judge.md`) } : l
}
const cover = async (l, r, ids, D, label) => {
  const missing = ids.filter(id => !r.scores.some(s => s.id === id))
  if (!missing.length) return r
  log(`${label} left out ${missing.join(', ')}; asking for them`)
  const SCORES_SCHEMA = { type: 'object', properties: { scores: JUDGE_SCHEMA.properties.scores }, required: ['scores'] }
  const more = await agent(`You are the ${l.title} judge on a panel of the Phosphor tournament's side tour, and you have scored the field, but you left out ${missing.join(', ')}. ${l.prompt}

Your scores so far, to keep the same scale: ${r.scores.map(s => `${s.id} ${s.score}`).join('; ')}. The candidates are described in ${D}/stage/candidates.md and the measures in ${D}/stage/table.md; each one's strip is ${D}/strips/<id>.png (and <id>-details.png, <id>-squint.png) and its full-size shots ${D}/out/<id>/shots/. Look at the ones you missed, beside two or three you already scored, and score only ${missing.join(', ')} 0-10 through your lens, with one or two sentences why.`,
    { label: `${label}:missed`, phase: 'Judge', schema: SCORES_SCHEMA })
  const got = ((more && more.scores) || []).filter(s => missing.includes(s.id))
  return { ...r, scores: [...r.scores, ...got] }
}
const LOOK = (D, n) => `Look before you score. The screenshots are of the real page with each design applied:
- Contact sheets, every design side by side: ${D}/sheets/home.png, home-phone.png, chat.png, status.png, ideas.png, plans.png, todo.png, settings.png, lost.png, login.png
- One strip per design: ${D}/strips/<id>.png (Home, Chat, Ideas, Status, Plans and To do), ${D}/strips/<id>-details.png (controls, focus, afterglow, power-on) and ${D}/strips/<id>-squint.png; full-size shots ${D}/out/<id>/shots/*.png; tokens ${D}/palettes/<id>.json and markup ${D}/variants/<id>/
Open every strip, details strip and squint strip, the sheets, and zoom into full-size shots (the greeting, the phone, Status, the chat, To do) where differences are subtle. There are ${NUM[n] || n} designs to judge: take the time each deserves.
The measures table: ${D}/stage/table.md (ink/brand_on_bg: contrast of text and of the green, today 17.1/15.2; green_share_of_colour_pct, today ~83; hue_entropy 0-1; other_colour_neon_pct: how much of the non-green colour is neon-bright, low = grounded; targets_under_44_home).`
const JUDGE_CORE = `The owner's latest word is the test that weighs most: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." Small visual refinements beyond colour are welcome when they make the page more appealing and cost nothing in readability.

Big changes are welcome, and this panel rewards new ideas. Judge each design on what it sets out to do and how well it does it, on its merits alone, wherever it came from: never mark a design down for being unfamiliar, and never reward one for being familiar. Where a bold idea falls short, criticise it constructively: say exactly what fails, what in it works, and how it could be made to work, because each lineage's next round is built from your words.`

if (STAGE === 'judge') {
  phase('Judge')
  const l = lensOf(args.lens)
  const judges = (await parallel(Object.entries(args.heats).map(([h, heat]) => () => {
    const D = heat.dir
    const n = heat.ids.length
    return agent(`You are one judge on the panel of round ${N} of a side tour of the Phosphor tournament, judging heat ${h}. Your lens: **${l.title}**.

${OWNER}

${TOUR}

${l.prompt}

${JUDGE_CORE}

This heat's lineages: ${heat.lineages.map(x => `${x.name} (${x.idea}): ${x.ids.join(', ')}`).join('; ')}. Each lineage's candidates are its carried design(s) and this round's new entrants (a refinement, a graft and a dice mutant, and in round 1 the track series' revival), described in ${D}/stage/candidates.md with what each set out to do: read it all. The refinements, grafts, revival and phosphor mutants have had one studio crit and one revision. The other three lineages are judged in a parallel heat by the same lenses.

ALSO score the two yardsticks through your lens, on the same scale: 00-current (today's page) and r13-idea-1 (Desk Terminal, Joined, the main tournament's leader after round 13). They are not candidates; their scores let the heats and rounds be compared and show how far each lineage has come.

${LOOK(D, n)}

Score every candidate AND both yardsticks 0-10 through your lens with one or two sentences why; then your top 4 of the candidates, best first; up to three PROMISING ideas (the candidates most worth developing further, whatever their score now); concrete FIXES for at least the best design of each lineage and for any other whose idea is worth keeping (what to keep and what to fix, by page and element); TITLES: which greeting titles in this heat say FamilyDB's job best and which fail, and why (weigh the title as part of the page's wording, through your lens); and notes (including which grafted features worked and which did not).`,
      { label: `judge:${R}:${h}:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA })
      .then(r => r && { ...r, lens: l.key, heat: h })
      .then(r => r && cover(l, r, heat.ids, D, `judge:${R}:${h}:${l.key}`))
  }))).filter(Boolean)
  log(`${l.key}: judged heats ${judges.map(j => j.heat).join(', ')}`)
  return { stage: 'judge', judges }
}

// ---- Finish: the round's lessons and the ledger brought up to date --------------------------------
if (STAGE === 'finish') {
  phase('Learn')
  const [lessons, ledger] = await parallel([
    () => agent(`Round ${N} of the side tour of the Phosphor tournament has been judged.

${TOUR}

Read ${T}/${R}/results.json in full (both heats' rankings, every judge's scores and reasons, top fours, promise votes, fixes and notes, and what each lineage carries on), ${T}/${R}/args.json (each lineage's carried designs, its briefs and its dice mutant with the changes rolled), ${T}/${R}/stage/designs.json (what each new design set out to do and its revisions) and the planners' briefs in ${T}/${R}/stage/plan-*.json.

Append a section to ${T}/lessons.md headed "## Tour round ${N}" (change nothing else in that file, nor any other file), with:
- one line per lineage: where it stands (its best mean against today's page and Desk Terminal, Joined in its heat, and against where it stood last round), which of its designs carries on, and why that one won;
- at most eight bullets of NEW, concrete, reusable lessons: what the refinements fixed that the judges noticed and what they did not; which GRAFTED FEATURES took (named, with their source) and which read as pasted, and why; how the dice mutants fared by kind (phosphor, type, graphics, point) and what the rolled changes did; FAILED REACHES (the boldest ideas that fell short this round, what worked in each, how to try again); and anything that sank several lineages alike;
- TITLES: the greeting titles this round tried (each design's "title" in designs.json and on its Home), which the judges' "titles" notes favoured and why, and which to try next;
- at most three CANDIDATE PRINCIPLES for the Phosphor Interface standard that this round's evidence supports.
Do not repeat lessons already in the file; say where this round overturned or refined an earlier lesson. Return the section you appended, verbatim.`,
      { label: `learn:${R}`, phase: 'Learn' }),
    () => agent(`Round ${N} of the side tour of the Phosphor tournament has been judged.

${TOUR}

${T}/ledger.md (full entries) and ${T}/ledger-index.md (one line each) are the menu of praised features the lineages' grafts take from each other and from every earlier design. Bring it up to date from this round's judging: read ${T}/${R}/results.json (every judge's reasons, fixes and notes, both heats), ${T}/${R}/args.json and ${T}/${R}/stage/designs.json, and look at the new designs' strips (${T}/${R}-a/strips/<id>.png and ${T}/${R}-b/strips/<id>.png) where the words are not enough.

Append a section headed "## After tour round ${N}" to ${T}/ledger.md, and a matching short section (one line per item, new features numbered T${N}-01, T${N}-02 and so on) to ${T}/ledger-index.md (change nothing above them, nor any other file), with:
- GRAFT RESULTS: each feature grafted this round, onto which lineage, and whether the judges thought it took (made native, earning its place) or read pasted, with their words;
- NEW FEATURES: devices this round's judges praised in the new designs (a drawing, a component, a way of marking state, a type device, a light effect), each with its design id, what it is, where it lives (exact paths in ${T}/${R}-a/ or ${T}/${R}-b/: palettes/<id>.json, variants/<id>/templates, variants/<id>/sheet.css), the praise and the caveats, and which lineages it would suit;
- RETIRED: any ledger feature this round showed does not work, and why.
Return the section you appended, verbatim.`,
      { label: `ledger:${R}`, phase: 'Learn' }),
  ])
  return { stage: 'finish', lessons, ledger }
}

// ---- Landing: every lineage's final beside where it started ---------------------------------------
if (STAGE === 'landing') {
  phase('Judge')
  const D = `${T}/landing`
  const out = (await parallel(args.lenses.map(key => () => {
    const l = lensOf(key)
    return agent(`You are one judge on the LANDING PANEL of a side tour of the Phosphor tournament. Your lens: **${l.title}**.

${OWNER}

${TOUR}

The tour has ended. On this panel are each lineage's FINAL design after three rounds (${args.finals.join(', ')}), each lineage's ORIGIN as the tournament passed it over (${args.origins.join(', ')}), and two yardsticks: 00-current (today's page) and r13-idea-1 (Desk Terminal, Joined, the main tournament's leader after round 13). Which lineage each belongs to: ${args.lineages}. Judge every design on its merits alone, on one scale, through your lens: how good it is now, not how far it came.

${l.prompt}

${JUDGE_CORE}

${LOOK(D, args.n)}
The candidates: ${D}/stage/candidates.md.

Score every design (finals, origins and both yardsticks) 0-10 through your lens with one or two sentences why; then your top 4 of all, best first; up to three PROMISING ideas; FIXES for each final (what it would still need to beat the main tournament's best); TITLES: which greeting titles on this panel say FamilyDB's job best, and your pick; and notes: for each lineage, what three rounds of development did for it, and whether its final belongs in the main tournament's next round beside its current entrants.`,
      { label: `landing:${key}`, phase: 'Judge', schema: JUDGE_SCHEMA })
      .then(r => r && { ...r, lens: key })
      .then(r => r && cover(l, r, args.ids, D, `landing:${key}`))
  }))).filter(Boolean)
  return { stage: 'landing', judges: out }
}

throw new Error(`unknown stage ${STAGE}`)
