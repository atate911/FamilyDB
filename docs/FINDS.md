# Ideas, finds, suggestions and recommendations

What the app means by each word, how the family's own list and what the app finds on the web
work together, and what the family decided about it on 2026-10-11. This is the design to build
from: where it says what the code does today, the code is the authority; where it says what is
to come, this document is, until the code and the guide catch up and this note is taken out.

## The words

| Word | Means | Today in the code |
|---|---|---|
| **Idea** | Something the family put on their own list: a place, an activity, an event on a date, a project at home. Always the first thing offered. | `ideas` |
| **Find** | Something the app found on its own and keeps apart from the ideas: an event on a date, or a place to go any time. It becomes an idea when the family saves it, and goes when they say "not for us" or its date passes. Together the finds are her back pocket. | `finds`: events, and places to go any time; what became of each (saved, passed on) is kept. Searches do not keep theirs yet |
| **Scouting** | The nightly AI search that fills the back pocket, aimed at this family. | `scout`, each evening, on a weekday's theme with the family's brief, rationed to about US$2 a month |
| **Searching on request** | The AI search made while answering somebody who asked, with everything known about the question and the family. | `discover`: every planning question, events and places, with the question and the family's brief; what it finds is kept |
| **Filling in** | An AI lookup that completes the details of an idea or a find: address, hours, price, ages, indoor or outdoor, booking. Ideas and finds end up with the same facts. | `enrich` for ideas, `fill_find` for finds, a few an evening |
| **Checking** | Code testing ideas and finds against the family and a moment: firm rules, who is coming and their ages, the drive, free time, weather, opening hours. Each gets a verdict (good, possible, ruled out) and its reasons. No AI. | the suggestion engine, ideas and finds alike (`suggest/pocket.py`) |
| **Choosing** | AI judgement on what suits this family at this moment, among what checking kept, each choice with a reason. | `choose` within a suggestion; `curate` for the pocket each evening |
| **Suggestion** | What she offers when somebody asks. | the `suggest` tool and its log |
| **Recommendation** | What she puts forward without being asked, in a place in the interface. | her picks on Now, the digest's one new find, and New ideas on What could we do? |
| **Picks** | What choosing chose, inside a suggestion or a recommendation. | also used for the tiles on Now; that use becomes "recommendations" |

The line between a suggestion and a recommendation is who started it. "Discovery" is no longer
used for the whole idea: it is either scouting (nightly, on its own) or searching on request
(when asked).

## The rules that hold throughout

- **The family's list comes first.** A find is offered where the ideas do not cover a moment, or
  in the one place kept for something new; it never pushes a good idea out of a suggestion or a
  recommendation unless choosing picked it, with its reason.
- **For everybody, not only the kids.** An idea or a find is for the whole family, for the
  grown-ups (date night, a concert, a bar, a tasting), for one person, or for a kid. Scouting
  looks for all of them, and who each is for is kept with it, as an idea's is. Where a kid reads
  (her own Now, her own chat, a shared chat she is in) nothing for grown-ups only is shown; a
  grown-up's Now may hold a grown-ups' evening beside a family outing.
- **Code checks, the AI judges and words.** Checking is code, as for ideas; the AI searches,
  fills in, chooses and says it. Every hand-back is a strict tool that code checks.
- **One back pocket.** Whatever any search finds, at night or on request, is kept as a find, so
  nothing paid for is thrown away after an hour.

## A night

After the evening's lookups:

1. **Scout.** Code writes a brief and one AI turn searches with it. The brief carries who the
   family is (the grown-ups and the kids' ages; what each likes, from what they rated highly,
   saved and told the assistant; their firm limits: drive, cost, diet, indoors or out), the home
   area and the neighbourhoods they go to, what is already on their list and in the pocket so it
   looks for new things, and the night's theme. Themes turn through the week so nights do not
   repeat: for example food and drink, outdoors, shows and music, classes and clubs, grown-ups'
   evenings, the weeks ahead. It hands back up to a few finds, each with its link, its dates or
   "any time", its address, who it is for, and one line of why it suits them.
2. **Sort.** Code drops what is already an idea or a find (by name or site), what a firm rule
   leaves out, and what is past.
3. **Fill in.** The most promising new finds are filled in as ideas are, a few a night, and code
   estimates the drive.
4. **Judge.** One AI call reads the pocket against the family's list and history and marks which
   finds are worth putting forward, and when ("the market Saturdays in November", "any rainy
   afternoon"), each with a reason. A find it does not rate stays in the pocket, unrecommended,
   and can still come up when somebody asks.

## A day

- **Recommendations** are placed by code, with no AI when a page is drawn:
  - **Now**: her recommendations for the next hours and for the weekend. Ideas first; one tile
    may be a find, marked new to them.
  - **The weekend digest**: the week's best find, beside what is on their list.
  - **New ideas**: one section on *What could we do?*, the finds judged worth putting forward,
    each with **Save it**, **Not for us**, and its reason. Not a new destination.
  - A dated find comes forward as its day nears. Nothing recommended is recommended again within
    a week unless its day is near.
- **Suggestions**, when somebody asks, engage everything: the engine checks the ideas and the
  pocket alike, a search on request runs with the question in their words, its framing, the
  family's brief and what the list and pocket already hold, at the everyday lookup level (not a
  dearer model), for events and places alike, and what it finds joins the pocket and the answer.
  Choosing picks from all of it, and her reply leads with what is theirs.

## Learning

Saving a find, planning it, rating it, and "not for us" are each kept with the find. They shape
the next night's brief (more of what was saved, less of what was passed on), and Status shows
what scouting cost against what came of it: finds recommended, saved, planned, and how they were
rated, beside what came of the family's own ideas.

## What the family decided (2026-10-11)

- **What leaves the house is loosened for searching.** The more specific the search, the better
  the finds, and the family sees no real privacy problem in it. A brief may carry the family's
  makeup and the kids' ages, tastes and interests from memory and ratings, firm limits including
  diet and allergies, the neighbourhoods they go to, and the question in their words. It still
  never carries another chat's words, presents or wish lists, sign-in details, or exact
  coordinates (rounded as today). It goes to the company that looks things up, which is the
  company that already answers the chat unless the family chose another.
- **Scouting is nightly, within a budget of its own.** About US$2 a month to start, to be
  watched and changed: a night is one scouting turn of a few searches, a few fills, and one
  judging call, rationed so the month's budget holds (the night's share is what is left of the
  month over the nights left). At about a cent a search on the default lookup model, scouting
  itself is roughly half of it; filling in and judging are bounded to the rest.
- **Searching on request runs when somebody asks for suggestions,** with everything known, at
  the everyday lookup level, within the daily limit. It replaces today's narrower searches, which
  ran only for a named topic or when the sources listed too little.
- **Recommendations start on Now, the weekend digest and the New ideas section.** No other
  surface until those show they are used.
- **Judging the pocket runs at the everyday level by default,** settable like the other uses, so
  the nightly cost stays small; choosing within a suggestion keeps its own level.

## To build, in order

1. Finds hold places as well as events: a find may have no date ("any time"), carries who it is
   for, why it was found, its state (new, recommended, saved, planned, not for us) and when it
   was last put forward. The `finds` table needs a migration for this.
2. Searches on request keep what they find as finds, and run with the full brief.
3. Checking covers finds: dates against free time and the hours asked, the venue geocoded for
   the drive, who it is for and ages, firm rules against its words, weather when it is outdoors.
4. Scouting runs nightly with the brief and the theme, under its budget; the weekly search goes.
5. Filling in covers finds; the nightly judging call (a new kind of call, answering the five
   questions of `docs/AI_CALLS.md`) marks what to recommend and when.
6. Recommendations: Now's tiles from ideas and judged finds, the digest's find, the New ideas
   section with **Save it** and **Not for us**.
7. Learning and Status: what came of finds beside ideas, and the brief shaped by it.

Each step is its own change with its tests, its line in the guide, and the evals run before and
after where a prompt changes.
