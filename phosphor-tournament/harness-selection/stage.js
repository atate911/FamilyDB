export const meta = {
  name: 'phosphor-round-stage',
  description: 'One stage of a tournament round (design, screen, final, judge or finish), so several run side by side and use every core',
  phases: [
    { title: 'Plan', detail: 'the creative lead writes the informed briefs' },
    { title: 'Design', detail: 'random-seed, mutant, crossover and informed designers, on the real page' },
    { title: 'Second draft', detail: 'a studio crit and one revision for each random entrant and crossover' },
    { title: 'Judge', detail: "this stage's lenses score every candidate, and today's page as a fixed yardstick" },
    { title: 'Screen', detail: 'five lenses score the whole field from one card each' },
    { title: 'Final', detail: 'all eight lenses score and order the finalists' },
    { title: 'Curate', detail: 'each newcomer sorted into a motif family for the hall of fame' },
    { title: 'Learn', detail: "the round's lessons appended for the next round" },
  ],
}

// A round is run as several of these side by side, since each workflow runs only two agents at
// once: design stages (a share of the random entrants and mutants each, and one with the planner
// and the informed entrants), then judge stages (a share of the lenses each), then a finish stage.
// stages.py splits the work, renders and tallies between them, and assembles results.json.
const H = '/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness'
const R = args.round
const D = `${H}/rounds/${R}`
const STAGE = args.stage
const CARRIED = args.carried
const HISTORY = args.history || []
// A design stage may carry only its own mutants (mutantsBySlot) and how many there are (nMutants).
const MUTANTS = args.mutants || Array.from({ length: args.nMutants || 0 }, (_, i) => (args.mutantsBySlot || {})[i + 1] || { kind: (args.mutantsBySlot || {})[1]?.kind || 'step' })
const NR = args.nRandom
const NM = MUTANTS.length
const NI = args.nInformed
const MODE = args.mode || 'explore'
// The planner's share of the informed entrants (the rest were briefed at the owner's request).
const NP = args.nPlanned ?? NI
const NREF = MODE === 'refine' ? Math.floor(NP / 2) : 0
const NUM = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', ...Array.from({ length: 40 }, (_, i) => String(17 + i))]
// The wild lane: its carried designs, its new clean-sheet designs and its mutants.
const WILDC = args.wildCarried || []
const NW = args.nWild ?? (args.wild || []).length
const NWM = args.nWildMutants ?? (args.wildMutants || []).length
const NC = CARRIED.length + WILDC.length
const NT = NC + NR + NW + NM + NWM + NI
const NTW = NUM[NT] || String(NT)
// Work an earlier run already finished, by id: {final} skips it; {draft} skips the design; {crit} the crit.
const RESUME = args.resume || {}

const OWNER = `FamilyDB is a family planning app; its web page's look is called "Phosphor": a modern app lit the way an old green-screen monitor was. The owner likes the CRT theme and the Phosphor interface and wants to KEEP the green on black and the bright green phosphor (#6dff9c) as the signature colour. In their words: "all the bright green on a black background is a little bright and too contrasty"; it "just needs a little more variation"; and "there could also be some other subtle and tasteful colors used to augment the green so it doesn't appear completely monochromatic. The CRT is just a theme, not a strict limit." (Family feedback on the original: "that looks like the Matrix".) And, after seeing round 1's winners, the owner's latest word, which weighs above everything else: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." And: "small visual enhancements or refinements, even if there is a degree of randomness (changing in size, spacing, fonts, text size, orientation, headers/labels, icons, or anything else to improve visual appeal) are welcome, but not necessary. We are mimicking natural selection here." And the owner's direction for what the changes should be: \"Bright green where it needs to be to maintain the motif, more grounded coloration elsewhere.\" (the bright #6dff9c kept where the Phosphor motif needs it: the mark, the primary button, the glowing key word, focus, live lights, the monitors; elsewhere grounded, natural, material, lower-chroma colour in solid things with a job, not more glow or neon). And on rules: \\"For the purposes of this experimentation, treat the design constraints like README and other .md files as loose guidelines, not hard and fast rules. They were written to help, not restrict.\\" So docs/STYLE.md, the harness README and lessons.md are guidelines that may be broken when the page is better for it; only the harness's hard checks refuse a palette. And: \\"I enjoy typesetting/pagination in general and will appreciate even minor optimization of typography.\\" (typesetting counts: hierarchy, scale, measure, rhythm, tracking and leading, figures, pairing). The Phosphor Interface is the whole way the app is presented, not only its colours: the overall layout; the kinds of interface elements; the whitespace (darkspace) around each element and the pacing; how design elements relate; typefaces, bold and italic, and how titles, headers and labels are treated in size and colour; headers and footers; iconography and how icons relate to the type; graphics and their sparsity; the weight of lines, boxes and delimiters; rounding, shadows, glow and echoes (afterglow); pills, alignment and shades; pagination, scrolling and animation; the controls (dropdowns and select menus, radio buttons, checkboxes, free-form fields, scroll bars, focus and hover states); how a person uses the page (sight lines, clicks, moving between keyboard and mouse, taking in at a glance what the page is presenting); everything a senior interface engineer would weigh together; and most importantly the feel and personality of the presentation. The winner of this tournament defines the Phosphor Interface design standard for the whole app: so a coherent SYSTEM wins over a one-off effect (colours and faces with clear jobs, a type system with steps, rules that would hold on any page, Plans, To do and Settings included, not only the ones in the sheets). And the owner's latest word, after nine rounds: \"I'm concerned that in the goal of great interface design we've gained a lot but also lost a little of the unique effect of the original phosphor interface. I'd suggest bringing some of that back.\" That unique effect is the original page's light, a green-screen tube's: lit words and marks with a layered halo, the green screens' bloom, blur and scanlines, glowing dots on the black, highlights and afterglow. Its exact CSS is catalogued in ${H}/phosphor_kit.md. Bring it back where the phosphor is, and keep what the tournament gained: grounded colour elsewhere, a calmer page, a better structure. It is light where attention belongs, not glare across the page.`

const CARRIED_LIST = CARRIED.map(c => `${c.id} (${c.name})`).join(', ')

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    name: { type: 'string', description: 'two or three words, as written in the palette file' },
    tagline: { type: 'string' },
    concept: { type: 'string', description: '2-3 sentences: the idea and the feeling' },
    companions: { type: 'string', description: 'which colours keep the green company, and where each goes' },
    decisions: { type: 'array', items: { type: 'string' }, description: 'the main choices and why, including how you bent any roll or lesson' },
    tokens: { type: 'object' },
    glow: { type: 'number' }, screenGlow: { type: 'number' }, topGlow: { type: 'number' }, washGlow: { type: 'number' },
    floorsFailed: { type: 'integer' },
    measures: { type: 'string', description: 'final ink_on_bg, brand_on_bg, green share and hue entropy per page, kinds and sections dE typ/deu/pro, the greeting corner pixel' },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
    elements: { type: 'array', description: 'the design as a set of liftable parts: one line per slot it changes or is best at', items: { type: 'object', properties: { slot: { type: 'string' }, what: { type: 'string', description: 'what the element is and where it lives (selector or template partial), one line' } }, required: ['slot', 'what'] } },
  },
  required: ['id', 'name', 'tagline', 'concept', 'companions', 'decisions', 'tokens', 'floorsFailed', 'measures', 'strengths', 'weaknesses'],
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

// From round 14 everyone reads the digest, a few pages rewritten each round by the learn agent;
// lessons.md keeps the whole history and is read only by the learn agent, or searched for a detail.
const DIGEST = `${H}/lessons-digest.md`
const LESSONS = {
  follow: `${DIGEST} (what the judges have learned so far, distilled: follow it unless you have a reason not to, and then say the reason; ${H}/lessons.md is the whole history, to search with grep for a detail, never to read through)`,
  reference: `${DIGEST} (what earlier judges liked, and the pitfalls they found: read it for the pitfalls, and treat its taste as a reference you are free to leave when your roll's idea needs it)`,
  none: `the files the README points you to, but not lessons.md or its digest: as a wildcard you do not read them, which records what the judges liked about the leaders, the lane you are here to leave (the pitfalls that matter, such as a warm wash turning bronze on green-black or a greyed ground, are in the README and the floors)`,
}
// How a designer looks at a page: the four cards check.sh draws (contact.py), each about 1,500
// tokens, read several in one message, instead of a dozen full-size screenshots one at a time.
const CARDS_OF = (id) => `${D}/cards/${id}-home.png and ${D}/cards/${id}-lists.png (Home above and below the fold, Chat, Ideas; Status, Plans, To do, Settings: every page at half size), with ${D}/cards/${id}-use.png (the phone, the controls, the focus rings, Home squinted) and ${D}/cards/${id}-close.png (crops at 100%: the top corners, the heads, the lit monitor, the afterglow)`
const LOOKING = `Read images several at a time, in one message with several Read calls, never one per message: every message sends again everything already read, so one image a message costs many times more. Open a full-size shot (out/<id>/shots/<page>.png) only to check a detail the cards cannot show, and no more than six in all.`
const ONLY = 'Make only the rolled changes; everything else stays the parent\'s (the reminders below about page-wide roles and typographic refinements do not apply to a mutant, so the judges can tell what the changes did).'
const SLOTS = JSON.parse(/* slots.json, inlined by stages.py */ args.slotsJson || '{"slots":[],"visible":{},"points":{}}')
const SLOT_LIST = SLOTS.slots.map(x => `${x.key} (${x.what})`).join('; ')
const SLOTS_NOTE = `The panel now carries ELEMENTS forward, not only whole designs: it votes on the best element in each slot (${SLOT_LIST}), and the winners are lifted out of their designs to be built into the next round's designs. So build each slot as a self-contained part (its own classes, markup in one partial or block, tokens by role) that could be lifted out and translated into another design, and in "elements" list one line per slot you change or are best at, naming the selector or template block.`
const HOW = (id, o = {}) => `How to work:
1. Read ${D}/README.md (the palette format with its roles lit, halo, accent, wash and top-glow; ./check.sh; the floors, including the signature floors and the accent-apart-from-sections floor; how to sample a pixel; a palette's own markup) and ${LESSONS[o.lessons || 'follow']}.
2. Look at today's home card (${D}/cards/00-current-home.png) and the carried palettes' home cards (${D}/cards/<id>-home.png for ${CARRIED_LIST}), in one message, so you know what yours must stand beside and beat.
3. ${o.start || `Write ${D}/palettes/${id}.json (start from a copy of palettes/00-current.json; set "id": "${id}" and your own "name" and "tagline").`}${o.only ? ` ${ONLY}` : ''} Iterate with ./check.sh run from ${D} (pages as you need while iterating), fix every FAIL, and LOOK at your cards at least twice, after two different renders: ${CARDS_OF(id)}; the home and lists cards every time, the use and close cards where your changes reach. ${LOOKING} Sample the greeting's corner with python rather than by eye. The family must be able to see the difference from today at a glance ACROSS THE PAGE (Home below the fold, Chat, Ideas, Status), not only in the greeting's corner: use the page-wide roles in the README (heading, label, card-edge, secondary with quietFilter, bubble and bubble-them, bezel, bar, ambient, a tinted surface) with taste, so the companion and the calmer tones carry through the whole page while the #6dff9c on green-black stays the signature. The owner enjoys typesetting and appreciates even minor typographic improvement: whatever your roll, consider small typographic refinements in the palette's "css" (README: "Typesetting"), and make them only where they truly improve the page.
4. Finish with a full render (./check.sh palettes/${id}.json, no page list) that passes every floor.

${SLOTS_NOTE}

Rules: work only in ${D} (and read the digest where step 1 says to); write only ${D}/palettes/${id}.json and, for your own markup, ${D}/variants/${id}/; never edit /home/user/FamilyDB, another palette or anything in ${H} outside ${D}; do not start or stop the server on port 8099. The owner's signature is the exact #6dff9c on a green-black ground: keep it unless your idea is better without it, and then say why. Be honest in the weaknesses.`


const HOW_WILD = (id, start, parent) => `How to work:
1. Read ${D}/README.md (the palette format, "A clean sheet", "Graphics, pictures and icons", ./check.sh and what it still refuses). Do not read lessons.md or its digest, and do not look at any other design in this tournament${parent ? ` but your parent, ${parent}` : ''}.
2. Look at today's cards (${D}/cards/00-current-home.png and 00-current-lists.png, in one message) for what the app contains, not for how yours should look.
3. ${start} Iterate with ./check.sh run from ${D} (pages as you need while iterating), fix every FAIL, and LOOK at all four of your cards, every page, at least three times: ${CARDS_OF(id)}. ${LOOKING}
4. Finish with a full render (./check.sh palettes/${id}.json, no page list).

${SLOTS_NOTE}

Rules: work only in ${D}; write only ${D}/palettes/${id}.json and ${D}/variants/${id}/; never edit /home/user/FamilyDB or anything in ${H} outside ${D}; do not start or stop the server on port 8099. Be honest in the weaknesses.`

// ---- Plan: the informed briefs, from all the feedback so far ---------------------------------
const runPlan = () => agent(
  `You are the creative lead of round ${args.roundNo} of a palette tournament for FamilyDB's Phosphor look.

${OWNER}

This round has ${NTW} palettes: the four carried from the last round (${CARRIED_LIST}), ${NUM[NR]} drawn from random starting points (colour and structure), ${NM ? `${NUM[NM]} mutants (carried winners with a few random changes of colour, structure and type${MUTANTS.some(m => m.kind === 'type') ? ', one with typographic changes only' : ''}${MUTANTS.some(m => m.kind === 'graphics') ? ', one with graphics and icon changes only' : ''}${MUTANTS.some(m => m.kind === 'crossover') ? ', a crossover of two carried winners' : ''}${MUTANTS.some(m => m.kind === 'phosphor') ? ', and the original Phosphor light brought back to a carried winner' : ''}: ${MUTANTS.map(m => m.kind === 'crossover' ? `${m.parentName}'s structure with ${m.colourParentName}'s colours` : `${m.parentName}${m.kind === 'type' ? ' (type only)' : m.kind === 'graphics' ? ' (graphics only)' : m.kind === 'phosphor' ? ' (the original light)' : ''}: ${m.changes.join('; ')}`).join(' | ')}), ` : ''}and ${NUM[NI]} informed, ${NUM[NP]} of which YOU brief now, informed by everything the judges have said about every palette so far. Yours must be real attempts to beat the carried four.

Read, in full:
- ${DIGEST} (the accumulated lessons, distilled)
- ${D}/stage/brief-pack.md (the last three rounds' rankings with their promise votes, and the last round's judges: their notes, and their reasons and fixes for every design carried into this round)
- the carried four's tokens (${D}/palettes/<id>.json) and their home and lists cards (${D}/cards/<id>-home.png, <id>-lists.png), read several at once

Search, never read whole (each is far larger than you can hold; use python or jq for what you need): every judging record so far, ${HISTORY.join(', ')} (every judge's scores, reasons, fixes and notes for every palette); ${H}/lessons.md (the whole history behind the digest); the hall of fame, ${H}/archive.json (every palette ever entered, where its files live and how it scored), ${H}/families.json (each palette's motif family) and ${H}/archive_distances.json (how alike every pair LOOKS, measured on the screenshots: [mean Delta E, % of points differing by more than 5]; about 0.5 = the same page, 1 = siblings, 2-3 = clearly different, 4+ = another direction).

The tournament must not narrow into one idea or iterate into an average. ${MODE === 'refine' ? `This is a REFINING round: the first ${NUM[NREF]} of your briefs are refinements of the carried winners (one each, the strongest first): keep the winner's idea and apply the judges' concrete fixes and small improvements, so good ideas get better. The rest are new offspring, and at least one of those must be a NOVELTY brief.` : 'At least one of your briefs must be a NOVELTY brief.'} A novelty brief opens a motif family that is not among the carried four: either one the hall of fame has never tried, or a family that did well once and dropped out, bred from DISTANT parents rather than neighbours of the leader; it must look clearly different (look-distance 1.5 or more) from every carried palette. Mark it in the hypothesis.

Then write ${NUM[NP]} briefs, each a distinct hypothesis about what would beat the carried four, for example: a hybrid that takes the element each judge praised in two palettes and drops what they criticised; a fix for a promising palette that fell short for one clear reason; an idea the judges asked for that no palette has tried yet; a bolder or calmer take on the leader. Each must keep the owner's asks and the harness's hard checks (the #6dff9c signature on a green-black ground; plain legibility; the page's integrity) and may break any written guideline when the page is better for it, must be clearly different from the carried four and from each other, and must be something a designer can build with the palette roles in ${D}/README.md (bg and neutrals, ink, brand, lit, halo, accent, wash, top-glow, screen, the section colours, outing, glow numbers). Briefs may change the page's markup too (layout, grouping, the kinds of elements, headers and footers, icons and pictures: README "A palette's own markup"), and the arrangement, size, position and even the existence of any element: what a design removes is listed for the judges to weigh. Briefs may also include small visual refinements beyond colour (size, spacing, type, corners, labels, icons: the palette's "css" field, README "Refinements beyond colour"), bred from the carried winners' refinements or new. Name the palettes whose elements it borrows and the criticisms it answers. New ideas are what this tournament rewards: read each ranking's "promise" votes (the ideas the judges most want developed, whatever their score) and the FAILED REACHES in the digest, and let at least one brief develop a promising idea from a low-scoring, random or wild entrant rather than the leaders.`,
  {
    label: `plan:${R}`, phase: 'Plan',
    schema: {
      type: 'object',
      properties: {
        briefs: {
          type: 'array', minItems: NP, maxItems: NP,
          items: {
            type: 'object',
            properties: {
              name: { type: 'string', description: 'a working name, two or three words' },
              hypothesis: { type: 'string', description: 'why this should beat the carried four' },
              brief: { type: 'string', description: 'what the designer should build, concretely, by role' },
              borrows: { type: 'string', description: 'which palettes and which praised elements' },
              avoids: { type: 'string', description: 'which criticisms it answers' },
            },
            required: ['name', 'hypothesis', 'brief', 'borrows', 'avoids'],
          },
        },
        reading: { type: 'string', description: 'your reading of the feedback so far, in a few sentences' },
      },
      required: ['briefs', 'reading'],
    },
  })

// A random entrant or a crossover meets winners refined over several rounds, so before judging it
// gets what they had: a studio crit, then one revision that keeps its idea.
const secondDraft = (id, what, lessons, kind, resume = {}) => async (draft) => {
  if (!draft) return null
  try {
  const crit = resume.crit || (resume.file && resume.critInFile ? 'file' : null) || await agent(`You are a studio critic in round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface.

${OWNER}

A designer has just made a first draft of ${id} (${draft.name}), ${what}. ${resume.file ? `Their idea, companions and own weaknesses are under "draft" in ${resume.file}: read it.` : `Their idea: ${draft.concept} Companions: ${draft.companions} Their own weaknesses: ${draft.weaknesses.join(' | ')}`}

Your job is to make THIS idea as good as it can be before the panel judges it beside winners refined over several rounds. ${kind === 'crossover'
    ? `Keep it true to both parents: judge how well the structure parent's system and the colour parent's colours have been reconciled into one page; do not pull it towards the other carried winners or towards today's page.`
    : kind === 'wild'
    ? `Keep it wild: judge how far and how well it carries its own design language and its twist, and what would make that work better. Do not pull it towards the other designs, towards today's page or towards any taste but its own; name what works, what fails and how to make it work.`
    : kind === 'phosphor'
    ? `Keep it true to its parent: judge whether the original Phosphor light is really back (${H}/phosphor_kit.md has each effect with its exact CSS; compare its close card with today's, ${D}/cards/00-current-close.png): does each lit thing read as light from a tube at 100%, the halo visible, the screens with bloom and scanlines, the dots glowing on the black? Does the change show at a glance beside the parent (its home card, ${D}/cards/<parent>-home.png) at half size, or only up close? And does it stay scarce, with no glare, the rest of the page grounded and every word still easy to read? Do not pull it towards the other carried winners or undo the parent's design.`
    : kind === 'features'
    ? `Keep it true to its parent and to the features it was asked to take: judge whether each feature is drawn in the parent's own materials on every page it reaches (not pasted on), whether the parent's identity survived, whether the features work together instead of piling up, and what the parent lost. Do not pull it towards the other designs or today's page.`
    : kind === 'brief'
    ? `Keep it true to its brief: judge how fully and how well the brief is carried out on every page, and what would make it better; do not pull it towards the other carried winners or towards today's page.`
    : `Do not pull it towards the carried winners (${CARRIED_LIST}) or towards today's page, and do not ask it to be safer: keep its idea, its structure and its mood, and judge the execution. Its roll was ${lessons === 'none' ? 'only a spark, which a wildcard may keep any part of or none' : 'a starting point, which it may bend or drop where the page is better for it'}: judge what the designer made, not how closely it follows the roll.`}

Look at its four cards, ${CARDS_OF(id)}, beside today's home card (${D}/cards/00-current-home.png), all in one message. ${LOOKING} Its tokens are ${D}/palettes/${id}.json and its markup, if it has any, ${D}/variants/${id}/. The floors and the palette roles are in ${D}/README.md; ${lessons === 'none'
    ? 'this is a WILDCARD: do not read lessons.md or bring its taste in (it records the lane the wildcard is here to leave); the pitfalls that matter are in the README and the floors.'
    : `the pitfalls earlier panels found are in ${DIGEST} (read it for the pitfalls, not for its taste).`}

Say what works and must stay, then the four to eight most important concrete fixes, most important first: where the idea is not carried through every page (Plans, To do, Settings and the form too), the hierarchy and sight lines, legibility, whether colour is grounded away from the lit green, the typesetting (scale, measure, leading, tracking, figures), the controls and focus states, and anything broken, clipped or awkward on the phone. Name the page, the element and the token or selector. Change no file; do not run ./check.sh.`,
    { label: `crit:${id}`, phase: 'Second draft', schema: CRIT_SCHEMA })
  if (!crit) { log(`${id}: the crit failed; judged on its first draft`); return { ...draft, secondDraft: 'failed' } }
  const rev = await agent(`You are the designer of ${id} (${draft.name}) in round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface.

${OWNER}

${id} is ${what}. Your first draft is ${D}/palettes/${id}.json${`, with its markup in ${D}/variants/${id}/ if it has any`}. ${resume.file ? `Its record (what it set out to be, its companions and its main decisions) is under "draft" in ${resume.file}: read it.` : `What it set out to be: ${draft.concept} Its companions: ${draft.companions} Its main decisions: ${draft.decisions.join(' | ')}`}

${crit === 'file' ? `A studio critic has looked at it on every page: their reading, what works and must stay, and the fixes, most important first, are under "crit" in ${resume.file}. Read them all.` : `A studio critic has looked at it on every page. Their reading: ${crit.reading}
What works and must stay:
${crit.keep.map(k => `- ${k}`).join('\n')}
The fixes, most important first:
${crit.notes.map(k => `- ${k}`).join('\n')}`}

Make one revision. Keep the idea; act on the notes that make the page better (you may decline a note that would betray the idea, and say why); look at your cards again before you finish.

${kind === 'wild' ? HOW_WILD(id, `Revise ${D}/palettes/${id}.json and ${D}/variants/${id}/ in place, keeping its id.`) : HOW(id, { lessons, start: `Revise ${D}/palettes/${id}.json (and ${D}/variants/${id}/, if it has markup) in place, keeping its id.` })}

Return the whole design as it now stands, with "revisions" saying what you changed and which notes you declined.`,
    { label: `revise:${id}`, phase: 'Second draft', schema: REVISED_SCHEMA })
  if (!rev) { log(`${id}: the revision failed; its files may be part-revised, so Prepare renders it again`); return { ...draft, secondDraft: 'failed' } }
  return { ...rev, id, crit: crit === 'file' ? undefined : crit.notes, firstDraft: { name: draft.name, concept: draft.concept } }
  } catch (e) {
    log(`${id}: second draft stopped (${e}); judged as it stands`)
    return { ...draft, secondDraft: 'failed' }
  }
}

const designRandom = (seed, slot) => {
  const id = `${R}-rand-${slot}`
  const wild = seed.ambition === 'wildcard'
  return agent(`You are a designer in round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface.

${OWNER}

Your page starts from a RANDOM roll of the dice, to bring in ideas nobody would have planned. The roll has two halves: its COLOUR (mood, material, companion hues and their roles, ground, ink, contrast and glow) and its STRUCTURE (layout, type_system, controls, icons, graphics, motion, pacing: how the page is built), with type_details (typesetting moves to carry through every level they reach). ${wild
    ? `You are a WILDCARD: this round's licence for a bold leap, and the roll is only a spark: keep any part of it, or none. Rethink the page's whole visual system within the hard checks: its layout and the kinds of elements, its colour, its type system (faces, scale, weights, tracking, figures), its spacing and rhythm, how cards, panels, headings, labels, chips, the bar, the tab bar and the controls are drawn, the monitors' cases, the icons. Change the markup wherever the idea needs it (README: "A palette's own markup"; your templates in ${D}/variants/${id}/templates/). Keep the owner's asks: the bright #6dff9c signature where the motif needs it on a green-black ground, grounded colour elsewhere, legibility. Aim for a genuinely different, coherent, beautiful direction, not a variation of the carried four, and iterate at least three times on what you see.`
    : `The roll is a STARTING POINT, not a specification: carry it through the whole page, bend or drop any part that fights the rest or hurts the page, and say what you kept, bent, dropped and added. The structure is as much yours as the colour: where it needs the markup, change the markup (README: "A palette's own markup"; your templates in ${D}/variants/${id}/templates/).`} The css budget is 25000 characters. After your draft a studio critic will look at it and you will make one revision, so make the draft whole and brave, not safe. The roll:

${JSON.stringify(seed, null, 1)}

${wild ? 'If you keep any of the roll, make it visible across the page, not a corner. ' : ''}${wild ? '' : `Turn the roll into a page the family would see is different at a glance: the mood is your theme, ${seed.material ? `the material (${seed.material}) is how the companion should feel: a grounded, solid, real-world colour at that hue, carried in solid things with a job, never a glow,` : ''} the companion hue(s) your company for the green (at OKLCH hue ${seed.companion_hue_deg}${seed.second_companion_hue_deg != null ? ` and ${seed.second_companion_hue_deg}` : ''}), the roles where it goes, the ground, ink, contrast and glow numbers your starting settings, and the structure how the page is laid out, set, pictured, controlled and paced; carry the type_details through every level they reach. If the roll brings refinements (small visual mutations), make them with taste in the palette's "css" field (README: "Refinements beyond colour"), or bend them; they are optional. Where a roll conflicts with the owner's constraints or a hard check (for example a lifted ground, or a halo in a colour that is not green), bend it and say how. `}Keep it clearly different from the carried four (${CARRIED_LIST}).

Your file: ${D}/palettes/${id}.json (id "${id}").

${HOW(id, { lessons: wild ? 'none' : 'reference' })}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
}
const randomChain = (s) => {
  const { slot, ...seed } = s
  const id = `${R}-rand-${slot}`
  const r = RESUME[id] || {}
  if (r.final) return Promise.resolve(r.final)
  const known = r.draft || (r.file ? { id, name: r.name } : null)
  return (known ? Promise.resolve(known) : designRandom(seed, slot)).then(draft => secondDraft(id,
    `a ${seed.ambition === 'wildcard' ? 'WILDCARD ' : ''}random entrant from this roll: ${JSON.stringify(seed)}`,
    seed.ambition === 'wildcard' ? 'none' : 'reference', 'random', r)(draft))
}

const designMutant = (m, slot) => {
  const id = `${R}-mut-${slot}`
  const copy = (pid) => `copy ${D}/palettes/${pid}.json to ${D}/palettes/${id}.json (set "id": "${id}"), and when ${pid} has its own markup (${D}/variants/${pid}/), copy that whole folder to ${D}/variants/${id}/`
  const body = m.kind === 'graphics'
    ? `Your page is a GRAPHICS MUTANT: one of the carried winners with only its graphics, pictures and iconography changed, rolled by the dice, so the panel can see what they alone do to a design that already works. Big changes are welcome. Parent: ${m.parent} (${m.parentName}). The changes the dice rolled, one major and one or two minor:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy(m.parent)}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then draw the changes as real assets, well made and in one style, carried through every page they reach. When a rolled change touches the icons, redraw ${D}/variants/${id}/static/icons.svg, starting from your parent's sprite (copied with its folder) when it has one, otherwise from the real /home/user/FamilyDB/src/familydb/web/static/icons.svg, and keep every icon id. Put SVG (or PNG and WebP) pictures beside it, placed through your templates or loaded by your css (url(name.svg), relative to /static/). Read README "Graphics, pictures and icons". Change nothing else: the colours, type and layout stay the parent's, except where a picture needs room; say where. If a change hurts the page, make the nearest version that does not, and say so.`
    : m.kind === 'type'
    ? `Your page is a TYPE MUTANT: one of the carried winners with only typographic changes, rolled by the dice, so the panel can see what the typesetting alone does to a design that already works. Parent: ${m.parent} (${m.parentName}). The changes the dice rolled, one major and two minor:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy(m.parent)}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then make these changes fully and well, as a careful typesetter would: carry each one through every page and every level it reaches (titles, heads, body, labels, figures, controls, and the tubes when a change reaches them), and tune what a new face needs to sit well (size, leading, tracking, weights, figures). Faces come from the library in README "Refinements beyond colour", added for you when named. Change nothing else: the colours, the layout and every other rule stay the parent's, except where a type change needs the markup (a class on a figure, a span for small caps); say where. If a change hurts the page, make the nearest version that does not, and say so.`
    : m.kind === 'phosphor'
    ? `Your page is a PHOSPHOR MUTANT: one of the carried winners with the original Phosphor page's light brought back, as the owner asks above, so the panel can see what a green-screen tube's light does for a design that already works. Parent: ${m.parent} (${m.parentName}). What to bring back:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy(m.parent)}; give it a "name" of two or three words that says it is a variation, and a "tagline". Read ${H}/phosphor_kit.md: the original's effects, each with its exact CSS, where it was used and how a design re-creates it. ${H}/phosphor_audit.md says what the carried designs kept and lost of it, when your parent is among them. Look at your parent's close and home cards beside today's (${D}/cards/<id>-close.png and -home.png, for ${m.parent} and 00-current, in one message), and crop a full-size shot only where you need more, to see what it lost. Then bring the light back wherever this design shows phosphor (its monitors and screens, the lit states, the machine's words and readouts, the live dots and lamps, the mark and the primary actions), in the parent's own terms: its green, its cases, its type, its lines. The two emphases above go furthest. Keep everything else the parent's: its layout, its colours away from the phosphor, its type, its lines and its structure. Keep the light scarce: it goes where the phosphor is and attention belongs, and the rest stays grounded and quiet; a halo too faint to see at 100% is lost, and glare or text blurred past easy reading is a fault. The change must show at a glance, beside the parent on the round's sheet (each page at about half size), not only up close: the owner said of an early round that changes a viewer cannot see do not count. Where the original's light lived in a shape (the glowing edge of the box you type in, the case that spills light, the lit tile), bring the light back even where the parent's shape differs. Keep each effect's reduced-motion and more-contrast behaviour as the kit gives it. If an effect hurts the page, make the nearest version that does not, and say so. A studio critic will look at it afterwards and you will make one revision.`
    : m.kind === 'step'
    ? `Your page is a CHILD in a natural-selection tournament: one carried design with a few small changes, at most ONE change per slot, so the panel can tell, slot by slot, which changes helped, and the winners survive into the next generation. Parent: ${m.parent} (${m.parentName}), which scored ${m.parentMean} in round 13. Your changes, one per slot:
${m.changes.map(c => `- [${c.slot}] ${c.text}${c.donor ? ` (an informed graft from ${c.donor}, ${c.donorName}: open its cards with your parent's, in one message, ${D}/cards/${c.donor}-home.png and -lists.png; its markup ${D}/variants/${c.donor}/templates/ and sheet.css; draw the element in your parent's own materials, never copy the donor's colours or page)` : ' (a blind random tweak: carry it out well, or make the nearest version that works)'}`).join('\n')}

First ${copy(m.parent)}; give it a "name" of two or three words: the parent's name and what changed. Then make each change fully and well on every page it reaches, and nothing else: every other slot stays exactly the parent's, so a slot's change is the only difference in that slot; make the changes sit together as one page. Keep each change small and self-contained, in its own classes, so it could be lifted into another design. In "elements" put one line per slot you changed, saying what it is and where it lives. No critic follows you and there is no second draft: this is one careful edit.`
    : m.kind === 'features'
    ? `Your page is a FEATURE CROSS: a design from round 13 that takes on the best features of the winners of the crossing rounds (14a and 14b), the way a line is improved by what the best of the other lines found. Parent: ${m.parent} (${m.parentName}), which scored ${m.parentMean} in round 13 (today's page ${m.todayMean}). Its identity stays: its structure, its colours and its mood are what make it a line of its own, and a feature is worked into it in its own terms, never pasted on. The features to bring in, with what the crossing rounds' judges said of each:
${m.changes.map(c => `- ${c}`).join('\n')}

${m.donors ? `The donors are in this round's field. Open their cards first, several in one message: ${m.donors.map(d => `${d} (cards ${D}/cards/${d}-home.png and -lists.png; markup ${D}/variants/${d}/templates/ and sheet.css)`).join('; ')}.\n\n` : ''}Adopt every one of them that this parent can carry well, carried through every page it reaches (Home, Ideas, Plans, To do, Status, Settings and the phone), and say in your decisions which you adopted, which you bent to fit and which you set aside and why. Where a feature's own origin design is a different idea, translate it: the lit line, the count strip, the dial, the big figure and the rule with its end mark all have to be drawn in this parent's materials. Record in "elements" one line per feature you adopted, under the slot it belongs to (each feature names its slot), saying how it differs from the donor's; this is what lets the panel tell which features worked. Also fix what the judges said of the parent (${m.parentFixes}). First ${copy(m.parent)}; give it a "name" of two or three words that says it is a cross (the parent's name and what it took), and a "tagline". A studio critic will look at it afterwards and you will make one revision. If a feature hurts the page, make the nearest version that does not, and say so.`
    : m.kind === 'crossover'
    ? `Your page is a CROSSOVER of two carried winners from different families, the way two lines breed: the STRUCTURE of ${m.parentName} (${m.parent}): its markup, layout, type system, controls, icons, spacing, rounding, line weights and the non-colour rules in its "css"; with the COLOURS of ${m.colourParentName} (${m.colourParent}): its tokens, its glow numbers, its colour roles, its material and its companion's jobs (${D}/palettes/${m.colourParent}.json).

First ${copy(m.parent)}. Then put in ${m.colourParent}'s colour tokens and glow numbers, re-map every colour that ${m.parent}'s css or markup names (by hex or by role) to the colour parent's matching role, and reconcile what clashes: the child must read as one coherent page, not a collage, keeping the best of each parent. Give it a "name" of two or three words for the cross and a "tagline", and say in your decisions which traits came from which parent and what you reconciled. A studio critic will look at it afterwards and you will make one revision.`
    : `Your page is a MUTANT: one of the carried winners with a few RANDOM changes, the way evolution tries a variation on something that already works. Parent: ${m.parent} (${m.parentName}). The changes the dice rolled, one of colour, one of structure and one of type:
${m.changes.map(c => `- ${c}`).join('\n')}

First ${copy(m.parent)}; give it a "name" of two or three words that says it is a variation, and a "tagline". Then make these changes fully and visibly, with taste: carry a structural change through every page it touches, changing the markup where it needs to (README: "A palette's own markup"). Keep everything else the parent has, its "css" refinements included, except what the changes or the floors force. If a change cannot be made without hurting the page, make the nearest version that does not, and say so.`
  return agent(`You are a designer in round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface.

${OWNER}

${body}

${HOW(id, { start: `Make ${D}/palettes/${id}.json as above.`, only: !['crossover', 'features'].includes(m.kind) })}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
}
// ---- The wild lane ------------------------------------------------------------------------------
const WILD_MANDATE = `Nothing is off the table if your idea wants it: the layout; the arrangement, size, position and even the existence of every element (move, resize, merge, hide or remove anything, forms and links included); the kinds of elements, the type, the colour, the pictures and icons, the density, the wording of headings and labels, even the owner's green signature. The panel judges every design on its own merits, rewards what works and says constructively what does not; a bold idea that falls short is worth more to this tournament than a safe one. What you remove is listed for the judges, who weigh what the family loses against what the page gains. What the check still refuses is only what would make the page unsafe: anything loaded from outside, scripts, unescaped output, inline styles, and a form you keep that has lost its security token.`

const designWild = (w, slot) => {
  const id = `${R}-wild-${slot}`
  return agent(`You are a designer in round ${args.roundNo} of a tournament for FamilyDB's web interface.

${OWNER}

Your design is WILD: this round's licence for an extreme idea, in a lane of its own where new ideas are what is rewarded. ${WILD_MANDATE}

Your starting point is a design language the dice rolled: ${w.language}. With this twist: ${w.twist}. If you want a companion for the green, one at OKLCH hue ${w.companion_hue_deg} is yours to use or ignore. Take the language as far as it goes, on every page: Home, Chat, Ideas, Plans, To do, Status, Settings, the new-idea form, Sign in, and the phone.

Start from a CLEAN SHEET (README "A clean sheet"): write your own stylesheet from nothing in ${D}/variants/${id}/sheet.css and set "sheet": "variants/${id}/sheet.css" in your palette file, so nothing of today's look is inherited. Write your own templates in ${D}/variants/${id}/templates/ wherever the idea needs its own markup, and your own pictures and icons (README "Graphics, pictures and icons"). Rebuild each page from its content, not from today's layout.

Your file: ${D}/palettes/${id}.json (id "${id}", your own "name" of two or three words and a "tagline"). Its "tokens" still name your colours (bg, surface, ink, brand and the rest, README "A palette"): your sheet uses them as custom properties (var(--bg), var(--ink), var(--brand) and so on), and the measures read them.

${HOW_WILD(id, `Write ${D}/palettes/${id}.json and ${D}/variants/${id}/sheet.css.`)}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
}
const wildChain = (w) => {
  const id = `${R}-wild-${w.slot}`
  const r = RESUME[id] || {}
  if (r.final) return Promise.resolve(r.final)
  const known = r.draft || (r.file ? { id, name: r.name } : null)
  return (known ? Promise.resolve(known) : designWild(w, w.slot)).then(draft =>
    secondDraft(id, `a WILD design on this design language: ${w.language}, with this twist: ${w.twist}`, 'none', 'wild', r)(draft))
}
const designWildMutant = (m, slot) => {
  const id = `${R}-wmut-${slot}`
  return agent(`You are a designer in round ${args.roundNo} of a tournament for FamilyDB's web interface.

${OWNER}

Your page is a WILD MUTANT: one of the wild lane's carried designs, ${m.parent} (${m.parentName}), with two big changes rolled by the dice, the way evolution tries a large leap from something that showed promise. ${WILD_MANDATE}

The changes the dice rolled:
${m.changes.map(c => `- ${c}`).join('\n')}

First copy ${D}/palettes/${m.parent}.json to ${D}/palettes/${id}.json (set "id": "${id}") and, when ${m.parent} has its own markup or sheet (${D}/variants/${m.parent}/), copy that whole folder to ${D}/variants/${id}/; if the palette names a "sheet", point it at your copy (variants/${id}/sheet.css). Give it a "name" of two or three words and a "tagline". Then make both changes fully and boldly, carried through every page they reach. Keep what made the parent promising, and say what you kept and what you changed.

${HOW_WILD(id, `Make ${D}/palettes/${id}.json as above.`, m.parent)}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
}
const wildMutantChain = (slot) => {
  const m = (args.wildMutants || [])[slot - 1]
  const id = `${R}-wmut-${slot}`
  const r = RESUME[id] || {}
  if (r.final) return Promise.resolve(r.final)
  const known = r.draft || (r.file ? { id, name: r.name } : null)
  return (known ? Promise.resolve(known) : designWildMutant(m, slot)).then(draft =>
    secondDraft(id, `a WILD mutant of ${m.parentName} (${m.parent}) with two big changes: ${m.changes.join('; ')}`, 'none', 'wild', r)(draft))
}

const mutantChain = (slot) => {
  const m = MUTANTS[slot - 1]
  const id = `${R}-mut-${slot}`
  const r = RESUME[id] || {}
  if (r.final) return Promise.resolve(r.final)
  const known = r.draft || (r.file ? { id, name: r.name } : null)
  const first = known ? Promise.resolve(known) : designMutant(m, slot)
  return m.kind === 'crossover'
    ? first.then(draft => secondDraft(id, `a crossover: the structure of ${m.parentName} (${m.parent}) with the colours of ${m.colourParentName} (${m.colourParent})`, 'follow', 'crossover', r)(draft))
    : m.kind === 'features'
    ? first.then(draft => secondDraft(id, `a feature cross: ${m.parentName} (${m.parent}) with the best features of the crossing rounds worked in`, 'follow', 'features', r)(draft))
    : m.kind === 'phosphor'
    ? first.then(draft => secondDraft(id, `a phosphor mutant: ${m.parentName} (${m.parent}) with the original Phosphor page's light brought back (${m.changes.slice(1).join('; ')})`, 'follow', 'phosphor', r)(draft))
    : first
}

const briefChain = (x) => {
  const id = `${R}-idea-${x.slot}`
  const r = RESUME[id] || {}
  if (r.final) return Promise.resolve(r.final)
  const known = r.draft || (r.file ? { id, name: r.name } : null)
  const first = known ? Promise.resolve(known) : designInformed(x.brief, x.slot)
  return x.secondDraft
    ? first.then(draft => secondDraft(id, `an informed entrant built from this brief. ${x.brief.name}: ${x.brief.hypothesis} Brief: ${x.brief.brief}`, 'follow', 'brief', r)(draft))
    : first
}

const designInformed = (b, slot) => {
  const id = `${R}-idea-${slot}`
  return agent(`You are a colour designer in round ${args.roundNo} of a palette tournament for FamilyDB's Phosphor look.

${OWNER}

Your palette is an INFORMED attempt to beat the four carried into this round (${CARRIED_LIST}), briefed by the creative lead from all the judges' feedback so far:

Working name: ${b.name}
Hypothesis: ${b.hypothesis}
Brief: ${b.brief}
Borrows: ${b.borrows}
Answers: ${b.avoids}

Build it faithfully, improving on the brief where what you see on the page tells you to. You may change the page's markup as well as its stylesheet, when the brief or the page calls for it (README: "A palette's own markup": your templates in ${D}/variants/${id}/templates/, checked and served for your render only). Like offspring, it may inherit the carried winners' traits, including their small visual refinements (the "css" field in their palette files), and add refinements of its own (README: "Refinements beyond colour"). Your file: ${D}/palettes/${id}.json (id "${id}").

${HOW(id)}`, { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA })
}

const LENSES = [
  { key: 'feedback', title: 'The owner\'s judge', prompt: `You are the OWNER'S JUDGE, the panel's stand-in for the owner. Read ${H}/owner_judge.md first: the owner's own first-hand reactions to earlier winners, which calibrate you to the owner's taste (they are one judge's opinion among the panel's, for you alone, not rules; still score every candidate on its merits as you see it). Then judge on the owner's words: less bright, less contrasty, more variation, subtle tasteful colours augmenting the green so it is not completely monochromatic, the bright green on green-black still unmistakably the signature, and above all the owner's direction: bright green where the motif needs it, more grounded coloration elsewhere (natural, material, lower-chroma colour in solid things across the page, not more glow).` },
  { key: 'soul', title: 'Phosphor soul', prompt: `Judge whether each keeps what the owner likes: the CRT theme and the Phosphor interface, lit and alive, the monitors still real 1980s green screens, glow scarce and meaningful (read "Why the green jumps" in /home/user/FamilyDB/docs/STYLE.md, as a guide to what the owner likes, not a rule). Calmer is wanted, lifeless is not; the CRT is a theme, not a strict limit.` },
  { key: 'style', title: 'Creativity and style', prompt: `Judge as an art director with taste: a fresh, considered, memorable identity with a clear mood; companions inspired rather than predictable; would the family say "oh, that's lovely"? Penalise the generic (well-known editor themes, stock dark mode), the timid and the gimmicky.` },
  { key: 'system', title: 'Design system (a senior interface engineer)', prompt: `Judge as a senior interface engineer weighing the whole system together: layout and the kinds of elements, darkspace and pacing, the weight of lines, boxes and delimiters, rounding, shadows, glow and echoes, pills, alignment and shades, headers and footers, iconography and how it relates to the type, graphics and their sparsity, the controls (selects, checkboxes, fields, focus, hover, scroll bars: see the details strips), motion, and whether it all reads as ONE coherent system that would hold on any page of the app (Plans, To do, Settings and the form included). Beautiful, current and comfortable for a family's daily use; links that look like links; nothing that reads as a warning when it is not one.` },
  { key: 'interaction', title: 'Interaction and comprehension', prompt: `Judge how a person uses and understands each page: sight lines (does the eye go title, then the one action, then the content?), what a glance tells you the page is presenting (use the squint strips and sheets/squint.png: blurred, is the hierarchy still clear?), the size and spacing of click targets (health.json counts those under 44px), moving between keyboard and mouse (the Tab order in health.json, the focus rings in the details strips), how clearly controls say what they do and what state they are in, and how quickly a family member finds what they came for. Compare each with today's page.` },
  { key: 'type', title: 'Typography and typesetting', prompt: `Judge as a typographer who loves typesetting (the owner does, and appreciates even minor typographic improvements): the hierarchy of titles, headings, body, labels and figures; the type scale and its rhythm; line length (measure) and leading; tracking at each size; how the faces pair and whether each does a job; numerals (tabular in lists and tables, figures that line up); how labels, dates and small text are set; spacing between blocks (vertical rhythm); anything a careful typesetter would fix. Compare each with today's typesetting (00-current): reward real improvements, even small ones; penalise fonts that fight the Phosphor feel, reduce legibility, or are change for its own sake. Look closely at full-size shots, not only the sheets.` },
  { key: 'usability', title: 'Usability (a family member using it)', prompt: `Judge as a usability specialist who walks through what the family actually does, on each candidate's own pages: send Vera a message and read her reply; see what is on this weekend; add an idea and find it again; show only the restaurants; tick off a to-do and see what is overdue; find a date on Plans; open a kid's wish list; change a setting; sign in. For each task, ask whether a family member using it for the first time sees where to start, gets it done in few steps, can tell what state things are in, and can recover from a mistake. Use the full-size shots, the phone shots, the new-idea form and the settings pages, the details strips (a field being typed in, a ticked box, an open select, focus rings) and health.json (the Tab order, the targets under 44px). Weigh legibility for tired eyes on a phone at night (the measured contrast and text sizes, now reported rather than refused), consistency (one kind of control looks and behaves one way everywhere), and anything a design removed or hid (listed in the candidates' notes): a removal that simplifies is a gain, one that loses a task the family needs is a real cost. Beauty and novelty are the other lenses' concern: a striking design that is hard to use scores low here, a plain one that is effortless scores high. Say concretely which task breaks, on which page, and how to fix it.` },
  { key: 'systemuse', title: 'System and use (a senior interface engineer who also watches the family use it)', prompt: `Judge as a senior interface engineer who also watches the family use the page: whether it reads as ONE coherent system that would hold on any page (layout and the kinds of elements, darkspace and pacing, lines, boxes and rounding, glow and echoes, the controls, headers and footers, icons beside the type); what a glance tells you the page is presenting, and whether the eye goes title, then the one action, then the content (the squinted Home on the use card); the controls and focus rings, and the click targets under 44px (in the measures table); and whether a family member using it for the first time could send Vera a message, find this weekend's plans, find and add an idea, tick off a to-do and see what is overdue, change a setting, legibly on a phone at night. Weigh anything a design removed (in the candidates' notes): a removal that simplifies is a gain, one that loses a task the family needs is a real cost. A striking design that is hard to use scores low here.` },
  { key: 'skeptic', title: 'Adversarial skeptic', prompt: `Be the skeptic: hunt for what is wrong in each (muddy or bronze washes, a greyed or tinted ground, a signature without spark, companions too faint or clashing, links that do not look like links, anything that reads as a warning or a costume, the Matrix, an editor theme, near-duplicates). Give real, spread-out scores.` },
]
// What each lens reads, by panel: the cards contact.py draws for every palette (home: Home above
// and below the fold, Chat, Ideas; lists: Status, Plans, To do, Settings; use: the phone, the
// controls, the focus rings, Home squinted; close: crops at 100% and the motion). The screen gives
// each lens one card per design, the five together covering every page; the final, with far fewer
// designs, two or three.
const CARDS = {
  screen: { feedback: ['home'], soul: ['close'], style: ['home'], systemuse: ['use'], skeptic: ['lists'] },
  final: {
    feedback: ['home', 'lists'], soul: ['close', 'home'], style: ['home', 'lists'], system: ['home', 'lists', 'use'],
    interaction: ['use', 'home'], type: ['close', 'home'], usability: ['use', 'lists'], skeptic: ['home', 'lists', 'use'],
  },
}
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    scores: {
      type: 'array',
      items: { type: 'object', properties: { id: { type: 'string' }, score: { type: 'number', description: '0-10' }, why: { type: 'string' } }, required: ['id', 'score', 'why'] },
    },
    top4: { type: 'array', items: { type: 'string' }, description: 'ids, best first' },
    promise: { type: 'array', items: { type: 'string' }, maxItems: 3, description: 'up to three ids whose idea is most worth developing further, new ideas above all, whatever their score now' },
    fixes: {
      type: 'array',
      items: { type: 'object', properties: { id: { type: 'string' }, suggestion: { type: 'string' } }, required: ['id', 'suggestion'] },
    },
    notes: { type: 'string' },
  },
  required: ['lens', 'scores', 'top4', 'promise', 'fixes', 'notes'],
}

// ---- The stages -----------------------------------------------------------------------------
if (STAGE === 'design') {
  phase('Design')
  const chains = [
    ...(args.seeds || []).map(s => () => randomChain(s)),
    ...(args.mutantSlots || []).map(k => () => mutantChain(k)),
    ...(args.briefs || []).map(x => () => briefChain(x)),
    ...(args.wildHere || []).map(w => () => wildChain(w)),
    ...(args.wildMutantSlots || []).map(k => () => wildMutantChain(k)),
  ]
  const planGroup = args.plan
    ? runPlan().then(plan => !(plan && plan.briefs)
      ? (log('planner failed: no informed entrants this round'), { plan, informed: [] })
      : pipeline(plan.briefs, (b, _s, i) => {
        const id = `${R}-idea-${i + 1}`
        return RESUME[id] && RESUME[id].final ? RESUME[id].final : designInformed(b, i + 1)
      }).then(informed => ({ plan, informed })))
    : Promise.resolve({ plan: null, informed: [] })
  const [done, group] = await Promise.all([parallel(chains), planGroup])
  const designs = [...done, ...group.informed].filter(Boolean)
  log(`${designs.length} new palettes here (${designs.filter(d => d.revisions).length} revised after a crit); floors failed: ${designs.filter(d => d.floorsFailed > 0).map(d => d.id).join(', ') || 'none'}`)
  return { stage: 'design', designs, plan: group.plan }
}

// ---- The screen and the final (from round 14) ---------------------------------------------------
// The screen: five lenses score the whole field, each from one card per design. The final: all
// eight lenses score the finalists (stages.py cut picks them) and put them in a strict order.
const PARTS_SCHEMA = { type: 'array', description: 'element votes: the best design for each slot you can judge from your cards', items: { type: 'object', properties: { slot: { type: 'string' }, best: { type: 'string', description: 'design id' }, runner: { type: 'string', description: 'design id, optional' }, what: { type: 'string', description: 'a few words: what the element is, so it can be lifted out' } }, required: ['slot', 'best', 'what'] } }
const SCREEN_SCHEMA = {
  type: 'object',
  properties: {
    parts: PARTS_SCHEMA,
    lens: { type: 'string' },
    scores: JUDGE_SCHEMA.properties.scores,
    top4: JUDGE_SCHEMA.properties.top4,
    promise: JUDGE_SCHEMA.properties.promise,
    fixes: JUDGE_SCHEMA.properties.fixes,
    notes: { type: 'string', description: 'a short paragraph' },
  },
  required: ['lens', 'scores', 'top4', 'promise', 'fixes', 'notes', 'parts'],
}
const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    parts: PARTS_SCHEMA,
    lens: { type: 'string' },
    scores: JUDGE_SCHEMA.properties.scores,
    order: { type: 'array', items: { type: 'string' }, description: 'every finalist id (not 00-current), best first, no ties' },
    fixes: JUDGE_SCHEMA.properties.fixes,
    notes: { type: 'string', description: 'a short paragraph' },
  },
  required: ['lens', 'scores', 'order', 'fixes', 'notes', 'parts'],
}
const partsPrompt = (l, panel) => {
  const vis = panel === 'screen' ? (SLOTS.visible[l.key] || SLOTS.slots.map(x => x.key)) : SLOTS.slots.map(x => x.key)
  return `

ELEMENTS. The panel carries the best parts of designs forward, not only whole designs, so also vote on elements. The slots: ${SLOTS.slots.map(x => `${x.key} = ${x.what}`).join('; ')}. ${panel === 'screen' ? `Your cards show these slots: ${vis.join(', ')}. Vote on those` : `Vote on the slots your cards let you judge best, at least three`}: for each, name the one design whose element in that slot is best (its id), optionally a runner-up, and a few words on what the element is so it can be lifted out. Judge the element alone, not the design's score: a middling design may have the best head, a leader may have a dull list. Name only elements you can see on your cards; leave a slot out when no design stands out.`
}
const panelPrompt = (l, panel, ids) => {
  const kinds = CARDS[panel][l.key]
  const n = ids.length
  const paths = ['00-current', ...ids].map(id => kinds.map(k => `${D}/cards/${id}-${k}.png`).join(', ')).join('\n')
  return `You are one judge on the panel of round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface. Your lens: **${l.title}**.

${OWNER}

${l.prompt}

The owner's latest word is the test that weighs most: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." Score a candidate whose difference from today is confined to a corner, a link colour and a tab pill LOW, however tasteful; reward a tasteful change the family would see across the pages. Small refinements beyond colour (sizes, spacing, type, corners, labels, icons) are welcome when they make the page more appealing and cost nothing in readability; typographic refinements count, even small ones: the owner enjoys typesetting.

${panel === 'screen'
    ? `This is the SCREEN. You and four other lenses score the whole field of ${NUM[n] || n} designs: ${NUM[NC]} carried from the last round and the rest new this round (mutants of the carried, informed entrants, and a wild lane built from clean sheets on design languages of their own). The seven best by the screen's scores, and the two the screen most wants developed (its promise votes), go on to a FINAL where all eight lenses look closer and put them in order. So what matters most is which designs deserve the final, and which ideas deserve developing: spread your scores, and cast your promise votes with care.`
    : `This is the FINAL. A screening panel scored the whole field of ${NUM[args.nField] || args.nField} designs; these ${NUM[n] || n} went on (its seven best and the ideas it most wants developed). Each finalist is here because it is good, so the differences are fine: look closely, compare them with each other, and put them in a strict ORDER, best first, with no ties. Your scores and your order must agree; the order is what ranks them, so where two score alike, the order says which is better.`}

Big changes are welcome, and this panel rewards new ideas. Judge each design on what it sets out to do and how well it does it, wherever it came from; never mark a design down for being unfamiliar or reward one for being familiar. Where a bold idea falls short, say exactly what fails, what in it works, and how it could be made to work.

ALSO score 00-current (today's page) through your lens, on the same scale, as a fixed yardstick: it is not a candidate, but its score lets the rounds be compared.

Look before you score. Your cards (${kinds.map(k => `"${k}"`).join(' and ')}: ${kinds.map(k => ({ home: 'Home above and below the fold, Chat and Ideas at half size', lists: 'Status, Plans, To do and Settings at half size', use: "the phone's Home, the controls, the focus rings and Home squinted", close: "crops at 100%: Home's top corners, the heads of Ideas and Status, Next up's monitor switched on, a card's afterglow" })[k]).join('; ')}), today's first, then one line per design:
${paths}
Read them several at a time: one message with six to eight Read calls, never one per message (every message sends again everything already read, so reading one image a message costs many times more). Then, only where your cards leave a real doubt, you may open up to four more images: another card of a design (${D}/cards/<id>-<home|lists|use|close>.png) or a full-size shot (${D}/out/<id>/shots/<page>.png).

The measures (ink/brand_on_bg: contrast of text and of the green on the page, today 17.1/15.2; green_share_of_colour_pct, today ~83; hue_entropy 0-1, today ~0.29; other_colour_neon_pct: how much of the NON-green colour is neon-bright, low = grounded; targets under 44px on Home): read ${D}/stage/table.md.

The designs: read ${D}/stage/candidates-short.md (each one's id, name, idea and, for the newcomers, its designer's own weaknesses and what it removed; ${D}/stage/candidates.md has the long version, for one design you need more on). ${DIGEST} says what earlier panels found, if you want it.

${panel === 'screen'
    ? `Score every design AND 00-current 0-10 through your lens with one sentence why, then your top 4, best first, then up to three PROMISING ideas (the designs whose idea is most worth developing further, new ideas above all, whatever their score now), then fixes, one or two sentences each, for the designs you rate highest and for the bold ones that fell short (what to keep and what to fix), and a short note.`
    : `Score every finalist AND 00-current 0-10 through your lens with one or two sentences why, then your ORDER of the finalists (every one, best first, no ties, 00-current left out), then a concrete fix or two for each finalist (what to keep and what to fix), and a short note.`}${partsPrompt(l, panel)}`
}
if (STAGE === 'screen' || STAGE === 'final') {
  phase(STAGE === 'screen' ? 'Screen' : 'Final')
  const ids = args.ids
  const schema = STAGE === 'screen' ? SCREEN_SCHEMA : FINAL_SCHEMA
  const SCORES_SCHEMA = { type: 'object', properties: { scores: JUDGE_SCHEMA.properties.scores }, required: ['scores'] }
  const pool = LENSES
  // A judge that leaves a design out is asked, once, for just the ones it missed, on its own scale.
  const cover = async (l, r) => {
    const missing = ['00-current', ...ids].filter(id => !r.scores.some(s => s.id === id))
    let out = r
    if (missing.length) {
      log(`${l.key} left out ${missing.join(', ')}; asking for them`)
      const more = await agent(`You are the ${l.title} judge on the panel of round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface, and you have scored the ${STAGE}, but you left out ${missing.join(', ')}. ${l.prompt}

Your scores so far, to keep the same scale: ${r.scores.map(s => `${s.id} ${s.score}`).join('; ')}. The designs are described in ${D}/stage/candidates-short.md and the measures are in ${D}/stage/table.md. Look at the cards of the ones you missed (${missing.map(id => CARDS[STAGE][l.key].map(k => `${D}/cards/${id}-${k}.png`).join(', ')).join('; ')}) beside the same cards of two you already scored, all in one message, and score only ${missing.join(', ')} 0-10 through your lens, with one sentence why.`,
        { label: `${STAGE}:${R}:${l.key}:missed`, phase: STAGE === 'screen' ? 'Screen' : 'Final', schema: SCORES_SCHEMA, model: 'sonnet' })
      const got = ((more && more.scores) || []).filter(s => missing.includes(s.id))
      out = { ...r, scores: [...r.scores, ...got] }
    }
    if (STAGE === 'final') {  // an order that leaves one out, or names one twice, is completed by its scores
      const seen = new Set()
      const order = (out.order || []).filter(id => ids.includes(id) && !seen.has(id) && seen.add(id))
      const rest = ids.filter(id => !seen.has(id)).sort((a, b) =>
        ((out.scores.find(s => s.id === b) || {}).score || 0) - ((out.scores.find(s => s.id === a) || {}).score || 0))
      if (rest.length) log(`${l.key}'s order left out ${rest.join(', ')}; placed by its scores`)
      out = { ...out, order: [...order, ...rest], top4: [...order, ...rest].slice(0, 4), promise: [] }
    }
    return out
  }
  const mine = pool.filter(l => args.lenses.includes(l.key))
  const judges = (await parallel(mine.map(l => () => agent(panelPrompt(l, STAGE, ids),
    { label: `${STAGE}:${R}:${l.key}`, phase: STAGE === 'screen' ? 'Screen' : 'Final', schema })
    .then(r => r && { ...r, lens: l.key }).then(r => r && cover(l, r))))).filter(Boolean)
  log(`${STAGE} judged by ${judges.map(j => j.lens).join(', ')}`)
  return { stage: STAGE, judges }
}

if (STAGE === 'judge') {
  phase('Judge')
  // Every candidate and today's page must carry a score from every lens: a judge that skips one
  // is asked, once, for just the ones it missed, on the scale it already used.
  const ALL_IDS = ['00-current', ...CARRIED.map(c => c.id), ...(args.wildCarried || []).map(c => c.id),
    ...Array.from({ length: NR }, (_, i) => `${R}-rand-${i + 1}`), ...Array.from({ length: NM }, (_, i) => `${R}-mut-${i + 1}`),
    ...Array.from({ length: NW }, (_, i) => `${R}-wild-${i + 1}`), ...(args.wildMutants || []).map(m => `${R}-wmut-${m.slot}`),
    ...Array.from({ length: NI }, (_, i) => `${R}-idea-${i + 1}`)]
  const SCORES_SCHEMA = { type: 'object', properties: { scores: JUDGE_SCHEMA.properties.scores }, required: ['scores'] }
  const cover = async (l, r) => {
    const missing = ALL_IDS.filter(id => !r.scores.some(s => s.id === id))
    if (!missing.length) return r
    log(`${l.key} left out ${missing.join(', ')}; asking for them`)
    const more = await agent(`You are the ${l.title} judge on the panel of round ${args.roundNo} of a palette tournament for FamilyDB's Phosphor look, and you have scored the round, but you left out ${missing.join(', ')}. ${l.prompt}

Your scores so far, to keep the same scale: ${r.scores.map(s => `${s.id} ${s.score}`).join('; ')}. The candidates are described in ${D}/stage/candidates.md and the measures in ${D}/stage/table.md; each one's strip is ${D}/strips/<id>.png (and <id>-details.png, <id>-squint.png) and its full-size shots ${D}/out/<id>/shots/. Look at the ones you missed, beside two or three you already scored, and score only ${missing.join(', ')} 0-10 through your lens, with one or two sentences why.`,
      { label: `judge:${R}:${l.key}:missed`, phase: 'Judge', schema: SCORES_SCHEMA })
    const got = ((more && more.scores) || []).filter(s => missing.includes(s.id))
    return { ...r, scores: [...r.scores, ...got] }
  }
  const mine = LENSES.filter(l => args.lenses.includes(l.key))
  const judges = (await parallel(mine.map(l => () => agent(
  `You are one judge on the panel of round ${args.roundNo} of a palette tournament for FamilyDB's Phosphor look. Your lens: **${l.title}**.

${OWNER}

${l.prompt}

The owner's latest word is the test that weighs most: "Those look nearly identical... the changes need to reflect more of the page content, not a wash in the corner or a few icons." Score a candidate whose difference from today is confined to the greeting's corner, a link colour and a tab pill LOW, however tasteful; reward a tasteful change that the family would see across Home below the fold, Chat, Ideas and Status.

Small visual refinements beyond colour (sizes, spacing, type, corners, labels, icons) are welcome when they make the page more appealing and cost nothing in readability; they are optional, so judge the whole page, not whether it has them.

There are ${NTW} candidates: ${NUM[NC]} carried from the last round, ${NUM[NR + NW]} from random starting points${NW ? ` (${NUM[NW]} of them wild, built from a clean sheet on a design language of their own)` : ''}, ${NM + NWM ? `${NUM[NM + NWM]} mutants (a carried winner with a few random changes${MUTANTS.some(m => m.kind === 'crossover') ? ', one of them a crossover of two carried winners' : ''}${MUTANTS.some(m => m.kind === 'phosphor') ? `, ${MUTANTS.filter(m => m.kind === 'phosphor').length === 1 ? 'one' : 'some'} with the original Phosphor page's light brought back` : ''}${MUTANTS.some(m => m.kind === 'features') ? `; ${MUTANTS.filter(m => m.kind === 'features').length} are FEATURE CROSSES, each a round-13 design that took on five features from the crossing rounds' best designs (the "x14b-" donors are in this field, carried: judge whether each cross beat both its parent's old self and the donors, and whether the feature is drawn in the parent's own materials or pasted on)` : ''}), ` : ''}${NUM[NI]} informed by earlier feedback. The random entrants${MUTANTS.some(m => m.kind === 'crossover') ? ' and the crossover' : ''} have had one studio crit and one revision. Judge each on its merits alone, wherever it came from; a bold new structure that is well made should not lose to a familiar one for being unfamiliar.

Big changes are welcome, and this panel rewards new ideas. Judge each candidate on what it sets out to do and how well it does it. Reward what works, however far it strays from today's page, from the leading designs' style or from your own habits; never mark a design down for being unfamiliar, and never reward one for being familiar. Where a bold idea falls short, criticise it constructively: say exactly what fails, what in it works or is worth keeping, and how it could be made to work, so the next round learns from the reach instead of abandoning it.

ALSO score 00-current (today's page) through your lens, on the same scale, as a fixed yardstick: it is not a candidate, but its score lets the rounds be compared (how far the best has come from today).

Look before you score. The screenshots are of the real page with each palette applied:
- Contact sheets, today (00-current, reference only) and all ${NTW} side by side: ${D}/sheets/home.png, home-phone.png, chat.png, status.png, ideas.png, lost.png, login.png
- One 2x2 strip per candidate: ${D}/strips/<id>.png; full-size shots ${D}/out/<id>/shots/*.png; tokens ${D}/palettes/<id>.json
Open every strip (Home, Chat, Ideas, Status, Plans and To do), every details strip (${D}/strips/<id>-details.png: controls, focus, afterglow, power-on) and squint strip (${D}/strips/<id>-squint.png), and the home, home-phone, chat, status, settings, form, general and squint sheets at least, and zoom into full-size shots (the greeting and its corner, the phone's tab bar, Status) where differences are subtle. ${H}/lessons.md says what earlier panels found.

The measures (ink/brand_on_bg: contrast of text and of the green on the page, today 17.1/15.2; green_share_of_colour_pct, today ~83; hue_entropy 0-1, today ~0.29; other_colour_neon_pct: how much of the NON-green colour is neon-bright, low = grounded; kinds and sections dE floors 12/5/5):

Read the measures table: ${D}/stage/table.md.

Typographic refinements count, even small ones: the owner enjoys typesetting.

The candidates: read ${D}/stage/candidates.md (each one's id, name, idea, companions and, for the newcomers, its designer's own weaknesses).

Score every candidate AND 00-current 0-10 through your lens with one or two sentences why, then your top 4, best first, then up to three PROMISING ideas (the candidates whose idea is most worth developing further, new ideas above all, whatever their score now), concrete fixes (for the ones you rate highly, and for the bold ones that fell short: what to keep and what to fix), and notes.`,
    { label: `judge:${R}:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA }
  ).then(r => r && { ...r, lens: l.key }).then(r => r && cover(l, r))))).filter(Boolean)
  log(`judged by ${judges.map(j => j.lens).join(', ')}`)
  return { stage: 'judge', judges }
}

// A merge builds a lineage's next head: the head design with the elements that won last round lifted
// in from the children (or, for an all-star, from the parts bin's best designs), built exactly as their
// authors built them and reconciled into one page. Run before the round's children, which start from it.
if (STAGE === 'merge') {
  phase('Merge')
  const out = await parallel((args.merges || []).map(m => () => agent(
`You are a designer in round ${args.roundNo} of a tournament for FamilyDB's Phosphor Interface, and you are MERGING: building the next head of a lineage from a carried design and the elements that won the last round's vote.

${OWNER}

The base: ${m.base} (${m.baseName}). The winning elements to put into it, one per slot (each lives in the design named, which is in ${D}: palettes/<id>.json, variants/<id>/templates and sheet.css, cards in ${D}/cards/<id>-home.png and -lists.png):
${m.lifts.map(l => `- [${l.slot}] ${l.text}: from ${l.child} (${l.childName})${l.spec ? `; spec ${l.spec}` : ''}`).join('\n')}

First copy ${D}/palettes/${m.base}.json to ${D}/palettes/${m.id}.json (set "id": "${m.id}"), and when ${m.base} has its own markup (${D}/variants/${m.base}/), copy that folder to ${D}/variants/${m.id}/ (and fix the "sheet" path inside the palette). Then, for each element, open the source design's cards with the base's (in one message), find the markup and rules that draw it (grep -n, then sed -n: never read whole files), and lift them in exactly as their author built them: same markup, same classes, the rules moved into the head's own sheet; re-map any colour or font the element names to the base's roles. Where two lifts touch the same page region, make them sit together. Change nothing else: the base's other slots stay as they are. Give it a "name" of two or three words (the base's name and what it took) and a "tagline". ${SLOTS_NOTE}

${HOW(m.id, { start: `Make ${D}/palettes/${m.id}.json as above.`, only: true })}`,
    { label: `merge:${m.id}`, phase: 'Merge', schema: DESIGN_SCHEMA })))
  return { stage: 'merge', designs: out.filter(Boolean) }
}

// The parts curator: each winning element of a round, lifted out of its design as a spec the next
// generation can build from. Cheap work (grep and copy), so a smaller model, a batch of parts each.
if (STAGE === 'extract') {
  phase('Extract')
  const parts = args.parts || []
  const batches = []
  for (let i = 0; i < parts.length; i += 6) batches.push(parts.slice(i, i + 6))
  const out = await parallel(batches.map((b, k) => () => agent(
`You are the parts curator of a tournament for FamilyDB's Phosphor Interface. The panel voted on the best ELEMENT in each slot, and the winners are lifted out of their designs so later designs can be built from them. For each part below, write ${D}/parts/<slot>--<design id>.md (make the folder if it does not exist) and write nothing else.

The parts (slot, design id, name, what the judges said it is):
${b.map(x => `- ${x.slot}: ${x.id} (${x.name}): ${(x.what || []).join('; ') || 'no description'}`).join('\n')}

A design's files: ${D}/palettes/<id>.json (tokens, glow numbers, its "css" refinements) and, when it has its own markup, ${D}/variants/<id>/ (templates/, sheet.css, static/). Its slot's element is the markup and the rules that draw it. Find them with grep -n and read only those lines with sed -n: never read a whole file. Slots: ${SLOT_LIST}.

Each file has these sections, short:
## What it is: two or three lines, in the judges' words where you have them.
## Where: the files, template blocks (line ranges) and selectors that make it.
## Markup: the exact snippet, copied from the file, at most 40 lines (the block, or the macro it uses).
## CSS: the exact rules, copied, at most 80 lines.
## Needs: the tokens by role, fonts, svg and other classes it depends on.
## To lift it: what to rename or re-map so another design's colours, type and materials can carry it.
Copy; do not invent. If the element is spread too thin to lift (it is only a token or two), say so in "What it is" and give the tokens and the rule. Then return the paths you wrote.`,
    { label: `extract:${R}:${k + 1}`, phase: 'Extract', effort: 'low', model: 'sonnet',
      schema: { type: 'object', properties: { files: { type: 'array', items: { type: 'string' } } }, required: ['files'] } })))
  return { stage: 'extract', files: out.filter(Boolean).flatMap(o => o.files || []) }
}

if (STAGE === 'finish') {
  const [curated, lessons] = await parallel([
    () => agent(
  `You are the curator of the palette tournament's hall of fame. Families say how alike palettes LOOK and what idea they share, never how good they are; they keep the tournament from narrowing into one idea. Read ${H}/families.json (the families so far, with a one-line definition each, and every earlier palette's family) and look at the strips of a few members of each family (paths in ${H}/archive.json: <dir>/strips/<id>.png or round1/strips/<id>.png; search archive.json with python or jq, do not read it whole), several in one message. Then sort each NEW palette of round ${args.roundNo} into a family: ${args.newPalettes.join(', ')}.${NM ? ` Their lineage: ${MUTANTS.map((m, i) => m.kind === 'crossover' ? `${R}-mut-${i + 1} is a crossover of ${m.parent}'s structure with ${m.colourParent}'s colours` : `${R}-mut-${i + 1} is a ${{ type: 'type mutant (typographic changes only)', graphics: 'graphics mutant (pictures and icons only)', phosphor: "phosphor mutant (the original page's CRT light brought back, nothing else changed)" }[m.kind] || 'point mutant'} of ${m.parent} (${m.changes.join('; ')})`).join('; ')}. A point mutant stays in its parent's family unless its changes made a genuinely different idea: its structural change moves pixels, so for mutants the look-distance rule below (5 or more from every member means its own family) does not apply on its own; say why when you move one. A crossover joins its structure parent's family, or a new one when it reads as a new idea.` : ''} Their home cards are ${D}/cards/<id>-home.png (and strips ${D}/strips/<id>.png) and their tokens ${D}/palettes/<id>.json; how alike they look to each other and to the carried four: run cd ${D} && ./venv/bin/python diversity.py matrix ${D} (scale: about 0.5 = the same page, 1 = siblings, 2-3 = clearly different, 4+ = another direction). Reuse a family when a person would call the palette a variation of that idea; add a new family (with a one-line definition under "families") only when it is a genuinely different idea. Keep families consistent with the pictures: members of one family should mostly be within about 3.5 of each other on the look-distance, and a palette 5 or more from every member of a family is a different idea and needs its own family (a shared neutral or a shared monitor case is not enough to make one family). Add one entry per new palette id, {"family": ..., "motif": one plain line}, to ${H}/families.json, keeping everything already there; change no other file. Return the new entries.`,
      { label: `curate:${R}`, phase: 'Curate', effort: 'low', model: 'sonnet' }),
    () => agent(
  `Round ${args.roundNo} of the palette tournament for FamilyDB's Phosphor look has been judged. Append a short section to ${H}/lessons.md (and change nothing else in that file, nor any other file) headed "## Round ${args.roundNo}", with:
- one line naming the top four BY SCORE, with their mean scores (the four carried on are chosen afterwards, for score and variety, with a protected slot for the best random entrant; that choice is appended to this file then): ${args.ranking.slice(0, 4).map(r => `${r.id} ${r.name} ${r.mean}`).join('; ')}
- then at most eight bullets of NEW, concrete, reusable lessons from this round's judging, including one on FAILED REACHES (the boldest ideas that fell short this round: what exactly failed, what in each worked or is worth keeping, and how it could be tried again; use the judges' fixes and their "promise" votes; a failed reach is information about how to do it, never a rule against its direction), and one on TRAITS: which rolls and changes (each palette's "css" field and its own markup in ${D}/variants/<id>/; each random seed's structure (layout, type_system, controls, icons, graphics, motion, pacing), its "type_details" and "refinements" in ${D}/seeds.json; each mutant's changes, the crossover, and each wild design's language, twist and wild mutant's changes in ${D}/args.json) showed up in the winners and which in the losers, so good traits spread and poor ones fade. Say how the random entrants, the mutants, the type mutant, the graphics mutant and the crossover fared against the informed ones, and why; for the typographic and graphic changes, say which faces, scales, settings, icons and pictures the panel rewarded and which it did not. Also add, at most three, CANDIDATE PRINCIPLES for the Phosphor Interface standard that this round's evidence supports (a rule the winners share and the losers break). Also: what made winners win and losers lose, colours or roles that worked or failed on the page (with pixel samples or token values where the judges gave them), and any open problem. Read ${DIGEST} first, which holds what is still current (search lessons.md with grep for anything older; do not read it through): do not repeat lessons already there; say where this round overturned or refined an earlier lesson.

The judges' full output is in ${D}/stage/judges.json (each judge's lens and panel, notes, top four or order, scores with reasons, and fixes): read it all. ${args.panel === 'screen' ? `The round was judged in two panels: a SCREEN of five lenses (feedback, soul, style, systemuse: system, interaction and usability in one, and skeptic) over the whole field, from one card each, then a FINAL of all eight lenses over the finalists, ordering them; the lens names of the screen's judges start with "screen-". The ranking puts the finalists first, by the final's order, and the rest after, by the screen's scores, so a non-finalist's mean is the screen's, on its own panel.` : ''}

Then REWRITE ${DIGEST}, the digest every designer, critic and judge reads in place of lessons.md: at most 4,000 words, plain and concrete, keeping its headings: the owner's words (verbatim, as they stand in it now: never shorten or paraphrase them); the candidate principles of the Phosphor Interface standard that the evidence still supports; the pitfalls, with token values or pixel samples where known; the failed reaches worth trying again and how; what the carried designs are and what each judge wants fixed in them. Fold this round's lessons in: add what is new, change what this round overturned or refined, and drop what no longer helps a designer (lessons.md keeps it all). Change no other file.

The round's ranking: ${JSON.stringify(args.ranking)}

Return the section you appended to lessons.md, verbatim.`,
      { label: `learn:${R}`, phase: 'Learn', effort: 'low' }),
  ])
  return { stage: 'finish', curated, lessons }
}

throw new Error(`unknown stage ${STAGE}`)
