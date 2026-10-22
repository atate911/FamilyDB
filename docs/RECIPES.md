# Recipes and dinner ideas

Draft plan, October 2026. Nothing here is built yet; each phase names what it adds and the test
that holds it. Design in the shape of [WISHES.md](WISHES.md) and [FINDS.md](FINDS.md): what the
family asked for, what is decided, how it is built, what it costs.

## What the family asked for

Keep recipes and dinner ideas the way the app keeps outings: say one ("sheet-pan fajitas, the
kids liked them at Jo's"), or paste a link to a recipe online, and have it kept with what the
family needs to pick it later: how long it takes, who it feeds, and the situations it suits (a
family dinner, a quick weeknight, something put together before work and finished at six, a slow
Sunday). Then answer "what's for dinner?" from that, with the family's own situation weighed:
the evening's plans, the weekday, what was had lately, what they said about food.

## Decisions

| Decision | Kind | Call | Why |
|---|---|---|---|
| A recipe is an idea | Default | **Kind `recipe`, with its own facts in a `recipes` row** | An idea already has the title, who said it, tags, dedupe, undo, how it went (`outcomes`: made three times, 8/10, last Tuesday), export, search, the page and the forms. A table of its own would copy all of that. The recipe's own facts (ingredients, steps, minutes, serves, occasions, the link's page) go in one row per idea, as `places` does for a place. Any way of saying it (meal, dinner, dish, recipe) is saved as `recipe`, as presents are saved as `gift`. |
| Recipes stay out of the cached idea list | Invariant (cost) | **Never in the prefix; one read tool finds them** | The chat prefix carries every idea, one line each. A family keeps far more recipes than outings, and most messages are not about food, so recipes would be the dearest lines in every request. Instead the prefix says how many there are, and `find_recipes` ranks them in code for the message that asks. A recipe added or changed therefore never moves the cached prefix. |
| Situations are a short fixed list | Default | **`occasions` on the recipe, code reads the family's situation** | "Quick weeknight", "prep ahead", "family dinner" are what a pick turns on, so they are words code can filter on, not free text: `weeknight`, `family_dinner`, `prep_ahead`, `slow`, `date_night`, `guests`, `kids_cook`, `lunchbox`, `freezer`. Free text (how to prep ahead, the family's notes) goes in `prep_note` and the idea's description. What the family says about itself ("Wednesdays I'm home at seven") is memory, as today, chosen for a dinner message by its words (`memory.CUES`); a per-weekday rule code can hold is a later step, if asked. |
| A pasted link is read by code first | Invariant (cost) | **schema.org Recipe from the page, no model; a worker only when a page has none** | Nearly every recipe site carries a `Recipe` block in JSON-LD (name, ingredients, steps, times, yield, cuisine). Reading it is deterministic and free, so a link costs nothing most of the time. A page with no block goes to a bounded worker turn (`fill_recipe`), the same way a place is looked up. The server fetches the page with the checks the calendar reader uses (public host only, http(s), checked redirects, size cap, timeout), sending nothing of the family. |
| What is kept from a page | Family | **The ingredients, the steps, the times, the yield and the link; no picture** | A recipe kept only as a link is lost when the site goes or fills with ads: the steps are kept so the recipe's page is usable at the stove. A picture hotlinked from the site would tell that site the family's address every time the page is opened, so none is kept or drawn. To ask: whether the family wants the steps copied (a private copy for their own cooking) or the link alone. |
| Where it lives on the page | Design | **Eat becomes "What should we eat?": Cook, then Eat out** | Eating is the most frequent decision and already has its door. Tonight's pick is a dish or a restaurant; the family decides which, so the page shows both: the cook pick for the next meal, the recipes ranked for it, then the restaurants as today. Chips narrow to one side. A recipe's own page is the idea page with its recipe section. |
| "What's for dinner?" is answered by code | Default | **A ranked pick in code, through one tool and later one command** | The pick weighs facts code has (minutes until the evening's first plan, weekday or weekend, what was made lately, ratings, who it is for, the occasions asked for), as the Eat page's restaurant pick does. The model frames the question and words the reply; the ranking is logged with its reasons. The suggestion engine is for going out and stays out of it. |

## How it is built

### Storage (migration `0063_recipes.sql`)

One table, one row per recipe idea:

```
recipes (
    idea_id         INTEGER PRIMARY KEY REFERENCES ideas (id) ON DELETE CASCADE,
    name            TEXT,            -- the page's own name, when it had one
    source_url      TEXT,            -- the link as given, cleaned (base/urls.clean_url)
    source_site     TEXT,            -- its host, for "from seriouseats.com"
    ingredients     TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(ingredients)),
    steps           TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(steps)),
    active_minutes  INTEGER,         -- hands-on time
    total_minutes   INTEGER,         -- start to table
    serves          INTEGER,
    occasions       TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(occasions)),
    prep_note       TEXT,            -- "marinate the night before", "the sauce keeps a week"
    filled_at       TEXT,            -- when the page was read
    filled_by       TEXT CHECK (filled_by IN ('family', 'page', 'lookup')),
    fill_note       TEXT,            -- why a page could not be read
    updated_at      TEXT NOT NULL
)
```

- Cuisine and diet are the idea's `tags` (mexican, vegetarian), as for restaurants, so Eat's
  cuisine chips serve both sides.
- Ingredients and steps are lists of short strings, bounded in the tool (40 ingredients, 30
  steps, 300 characters a step). Searching ingredients ("something with chickpeas") is a LIKE over
  the JSON at family scale; no FTS table until one is measured as needed.
- `store/recipes.py` is the repository (`get`, `upsert`, `search`); `tests/test_store_boundary.py`
  holds statements to it. Nothing points at a member, so `members.POINTING_AT` is unchanged; the
  JSON export lists the table beside `places`.
- `store/ideas.py`: `KIND_SUGGESTIONS` gains `recipe`; `RECIPE_WORDS` folds meal, dinner, dish,
  cooking into it as `GIFT_WORDS` does; `needs_lookup` says a recipe has something to read only
  when it has a link; `RestKind` in `tools/memory.py` gains it.

### Tools (`tools/recipes.py`, and the idea tools)

- `add_idea` and `update_idea` take an optional `recipe` object (`RecipeFacts`: occasions,
  active_minutes, total_minutes, serves, ingredients, steps, prep_note). One nested schema,
  declared once, as `remember`'s `rule` is. The handler refuses it on any other kind, bounds the
  lists, and writes the `recipes` row in the idea's transaction, so dedupe, undo and the page's
  forms come for free. A recipe added by chat with only a link gets the link as `url` and
  `source_url`, and a title from what was said or the link's last part; the page's name replaces
  a title that was only the link.
- `find_recipes` (read, chat and page): `occasion`, `most_minutes`, `text` (title, tags or an
  ingredient), `for` (who is eating), `limit`. Returns the ranked few with each one's reason
  ("35 min, had it 3 weeks ago, 8/10, serves 4") and the count left out. Ranking is
  `familydb/meals.py` (domain, imports store only): facts first (minutes over the limit, an
  occasion asked for and missing, nobody it is for among those eating), then taste (made within
  its rest days lowers it; rating and times made raise it; an idea never made is "new to us").
  `describe_idea` on a recipe returns its full row, steps included, for "read me the fajitas".
- `shopping_list` is unchanged: "put the fajita ingredients on the list" is `describe_idea` then
  `shopping_list add`, two calls the model already knows. The page gets a button that does the
  same in code (phase 3).
- `save_recipe` and `skip_recipe` (worker-only hand-backs for `fill_recipe`, scoped by
  `worker_idea_id`): what the page states and nothing else; `save_recipe` fills only what the
  family left empty, as `places.filled_in` does, so what they said stands.
- `spending.DONE`, `views.DID_WORDS` and `tests/test_tool_facts.py` get the new writers.

### The chat prompt (`prompts/system.md`)

A short **Recipes** section: a dish, a meal or a recipe link is `add_idea` of kind `recipe` with
`recipe` filled from what was said (never guessed minutes); the situations it suits as
`occasions`; "what's for dinner" and "something quick" is `find_recipes`, framed from the message
(quick is `most_minutes` 30; "before work" is `prep_ahead`), its result led with in order; "we
had the fajitas, 8/10" is `find_recipes` for the number then `record_outcome`. The family context
line says "Recipes: 64 saved (find_recipes)" so the model knows they exist without seeing them.
`memory.CUES["food"]` gains recipe, meal, cook, fridge, leftovers, weeknight.

### Reading a link (`integrations/recipe_page.py`, `scouting/fill.py`, `jobs/enrich.py`)

1. The enrich job, on every run, reads recipe ideas with a link and no `filled_at` by code,
   whatever `lookups_when` says: a free read need not wait for the evening. The fetch is the
   calendar reader's (`integrations/address`, checked redirects, 2 MB, 20 s). The JSON-LD walker
   finds a `Recipe` in `@graph` or a list, reads `name`, `recipeIngredient`, `recipeInstructions`
   (strings, `HowToStep`, `HowToSection`), `prepTime`/`cookTime`/`totalTime` (ISO 8601 durations),
   `recipeYield` (first number), `recipeCuisine` and `keywords` (as tags, only when the idea has
   none). The stdlib does all of it; no new dependency.
2. A page with no block, or one that could not be read, waits for the evening lookup like a
   place: one worker turn of kind `fill_recipe` (`gateway.KINDS`: prompt `prompts/fill_recipe.md`,
   tools and hand-backs `save_recipe`/`skip_recipe`, one search, the fetch of the given link,
   the lookup model), under the day's limit and `look_up_now`. Its five questions
   ([AI_CALLS.md](AI_CALLS.md)) are answered there.
3. The chat note is the existing one ("Filled in #88 Sheet-pan fajitas: 35 min, serves 4, 11
   ingredients"), through `voice.EVENTS` `lookup_done`, under `enrichment_notes`.
4. A photo of a cookbook page already arrives as words (`gateway.look`), so "save this" with a
   photo works from day one; the words are the recipe the family gave.

### The page

- **Eat** (`web/ideas_page.py`, `eat.html`): "What should we eat?" The summary line names the
  cook pick for the next meal and the restaurant pick ("Tonight: fajitas, 35 min · or Kenji's,
  open till 9"). Two sections, Cook then Eat out; chips **Cook**, **Eat out**, **Quick**, **Prep
  ahead**, **Family dinner**, the cuisines, the people. A kid sees the recipes and the rows as
  today, no cost, no buttons. The cook pick is `meals.pick` with the evening's plans from
  `app.calendar`, no model call (`test_browsing_asks_nothing_of_a_model` holds it).
- **A recipe's page** (`/idea/N`): the recipe section after the facts: serves, active and total
  minutes, the occasions as words, the prep note, the ingredients, the steps folded, the link and
  its site, when it was read; made N times and how it went. Buttons for whoever may change
  things: **Had it tonight** (`record_outcome`), **Put ingredients on the list** (phase 3),
  **Edit by hand** (the idea form with the recipe fields).
- **Do** leaves recipes out as it leaves restaurants out; search in the box finds them.
- `shell.OWNS["eat"]` is unchanged; `docs/STYLE.md` and `docs/INTERFACE.md` section 4 record the
  new shape of Eat; the guide's "Eat and Do" page and the glossary say what a recipe is.

### Later, not in this plan

- The week's meals: a plan per evening on the week's page, made from the picks. Needs a decision
  on whether a meal goes on the shared calendar.
- A per-weekday rule in memory ("Wednesdays, 20 minutes at most") the picker holds in code.
- "What's in the fridge": ingredients on hand, and picks that use them.
- Picks on Now and in the weekend digest; a dinner pick in the hourly pick sets.

## Phases

Each is one pull request, reviewed, with its tests, docs and guide page in it.

**1. Capture and keep (no web, no new model call).** Migration, `store/recipes.py`, the
`recipe` facts on `add_idea`/`update_idea`, `find_recipes`, `meals.py`, recipes out of the
prefix with the count line, the prompt section, the memory cues, Eat's Cook section and the
recipe page and form, export, the guide. Tests: the store boundary, the tool facts, the request
for a message stable with no recipes and unchanged when one is added, a kid may add one and ask,
`test_browsing_asks_nothing_of_a_model`. Evals (`evals/cases.py`): "save this: sheet-pan
fajitas, 35 min, the kids like it" saves a recipe with its occasions; "what's for dinner, quick"
calls `find_recipes` with `most_minutes` and writes nothing; "we had the fajitas, 8/10" records
the outcome on the right idea.

**2. Links.** `integrations/recipe_page.py` with a test over saved sample pages (never a fetch
in tests), the free read in the enrich job, the `fill_recipe` kind with its prompt and
hand-backs, the chat note, the AI_CALLS row, `docs/DESIGN.md` sections 6, 7 and 9, the guide's
"What leaves the house" (the server reads a pasted link; the link goes to the lookup model only
when the page has no recipe block). Measure: `familydb debug cost` before and after, and the
share of links read by code against those that needed a worker, on Status.

**3. Cheaper paths.** "What's for dinner?" in plain words answered by code on every channel
(`commands.WORDS`, a `/dinner` Telegram command, the reply a `voice.EVENTS` `cmd_dinner` line
with three picks and their reasons; no model call). The recipe page's **Put ingredients on the
list** form through `shopping_list`. Both under the existing rules for commands and forms.

## Cost

- Prefix: `find_recipes` and the `recipe` sub-schema add about 400 cached tokens to every chat
  request; every recipe line left out of the list saves about 25. Checked with `familydb debug
  cost` in phase 1, as the cost rule asks, before the change is on by default.
- A link: nothing when the page carries a recipe block; else one lookup-level worker turn,
  about what a place costs today, bounded by the same iteration and search limits.
- "What's for dinner?": one chat call in phase 1 (the tool runs in code); none in phase 3.
- Idle: nothing. The enrich job reads the database and returns when no recipe waits.

## Rules this touches

- *Invariant (cache)*: kept. Recipes never enter the prefix; the count line changes only when
  the family adds the first recipe, as the idea list does today.
- *Invariant (cost)*: kept. The new kind of call is a line in `gateway.KINDS` with the five
  questions answered; no page view calls a model; the code read is free.
- *Invariant (security, cost)*: kept. The chat never fetches; the server's own read of a pasted
  link is the calendar reader's path, with its address checks, and a page is information, never
  instructions (the walker reads fields; the worker prompt says so).
- *Invariant (security)*: kept. The page writes through `add_idea`, `update_idea`,
  `record_outcome` and `shopping_list`, already named in `tests/test_web.py`'s list; no new
  writer.
- *The family's decisions*: one to ask (what is kept from a page, above). Who may add or ask is as
  today: a kid may add an idea and read, so a kid may add a recipe and ask what is for dinner,
  within her daily messages.
- *Migrations*: next becomes `0064`.
