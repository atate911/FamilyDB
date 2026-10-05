# Handoff: building Kitchen Table into FamilyDB

This is for the engineers who will build the Kitchen Table design into `src/familydb/web/`. Everything here was checked against the app's own code in `app-reference/` (templates, `views.py`, `routes.py`, `settings.py`, `setup.py`, `status.py`, `fields.py`, `family.py`, `auth.py`, `chat.py`, `edits.py`, `roles.py`). Where this folder and the app disagree on **what a page says or does**, the app wins. Where they disagree on **how it looks**, this folder wins.

**What's in this folder**

| Here | Goes to | What it is |
|---|---|---|
| `style.css` | `static/style.css` | the one stylesheet: base, shell, components, pages, phone, forced colours |
| `themes.css` | `static/themes.css` (the built file, fitted) | every look: Kitchen Table's roles worked out for every look, Kitchen Table (`[data-theme="kitchen"]`), Phosphor, the six built looks, two additions (see §8) |
| `fonts/*.woff2` (8 files) | `static/fonts/` | Atkinson Hyperlegible 400/700, Fraunces SOFT 600, Fraunces figures (2 subsets × 2 weights), JetBrains Mono 400 |
| `brand/` | `static/brand/` | favicon (SVG, 32, 16), apple-touch-icon, 512 icon, mark sources |
| `icons.svg` | `static/icons.svg` | the icon sprite (`#i-name`), replacing the Lucide one |
| `_kit/looks-check.py` | additions to `tests/test_look.py` | the built floors plus Kitchen Table's layout pairs and the effects, for every look; palette sheets |
| `STYLE-draft.md` | `docs/STYLE.md` | the design notes, as they will stand once built |
| `STANDARD.md` | (reference) | every component, token, rule and check, with class names |
| `CHANGES.md` | (reference) | why each thing is the way it is, stage by stage |
| `*.html` (63 pages), `looks-test/*.html`, `palette/*.html` | (reference) | the mockups; Home and a kid's Home in Rail yellow, Midnight and Phosphor; a palette sheet per look |
| `shots/` | (reference) | every page at 1280 and 390 px, light and dark; `shots/looks/` for the built looks on Kitchen Table's layout and the palette sheets |

The mockups are static: no scripts, no inline styles, every icon inline (only because `file://` blocks an external `<use>`). They are generated, so the markup of one component is the same on every page.

---

## 1. Page map

### Every mockup → its real template, route and view

R = the mockup replaces the template's markup. S = a state of a template another mockup also draws. N = new. D = a design sheet, not a page.

| Mockup | Real template | Route → view (context builders) | |
|---|---|---|---|
| `home.html` | `home.html` | `/` → `routes.home` (`agenda.read`, `task_store.list_all`, `chat.glance`, `wish_glance`, `status.setup_steps`; `views.entry_row`, `task_brief`, `idea_row`) | R |
| `home-kid.html` | `home.html` | the same, for a kid (`visitor().may(...)`) | S |
| `home-parent.html` | `home.html` | the same, for a parent who isn't an admin (Alex): Status under "Behind the scenes", no Settings or Family, no setup card | S |
| `chat.html` | `chat.html` + `_ask.html` | `/chat` → `chat.show` (`chat.page`, `views.chat_line`, `chat.standing`, `chat.box`) | R |
| `chat-kid.html` | `chat.html` | the same, her own chat (`my_chat`) | S |
| `ideas.html` | `ideas.html` | `/ideas` → `routes.ideas` (`idea_store.search`, `views.idea_row`, `places_radar`, `away_from_home`) | R |
| `restaurants.html` | `restaurants.html` | `/restaurants` → `routes.restaurants` (`views.restaurant_card`) | R |
| `idea.html` | `idea.html` | `/idea/<id>` → `routes.idea` (`idea_row`, `place_panel`, `outcome_row`, `plan_row`) | R |
| `idea-new.html` | `idea_form.html` | `/ideas/new` → `routes.new_idea` (`_idea_form`) → POST `edits.add_idea` | R |
| `idea-edit.html` | `idea_form.html` | `/idea/<id>/edit` → `routes.edit_idea` → POST `edits.edit_idea` | S |
| `plans.html` | **`plans_month.html`** | `/plans/month` → `routes.plans_month` (`views.month_weeks`) | R (the names swap: the mockup "plans" is the month) |
| `plans-list.html` | **`plans.html`** | `/plans` → `routes.plans` (`agenda.read`, `entry_row`) | R |
| `todo.html` | `tasks.html` | `/tasks` → `routes.tasks` (`task_store.list_all`, `views.task_row`, `REPEATS`) | R |
| `todo-kid.html` | `tasks.html` | the same, a kid's own (`_own_only`) | S |
| `todo-edit.html` | **`task_form.html`** (new) | `GET /task/<id>/edit` → `routes.edit_task` (new) → POST `edits.edit_task` (as today) | N: the to-do's own Edit page replaces the fold on the row (decided, §1 item 18) |
| `wishes.html` | `wishes.html` | `/wishes` → `routes.wishes` (`_kids`, `_lists`, `views.WISH_LISTS`, `wish_row`) | R |
| `wishes-maya.html` | `wishes.html` | `/wishes?who=<id>` | S |
| `wishes-kid.html` | `wishes.html` | the same, a kid | S |
| `memory.html` | `memory.html` | `/memory` → `routes.memory` (`views.memory_page`) | R |
| `status.html` | `status.html` | `/status` → `routes.status` (`status.status()`) | R |
| `activity.html` | `activity.html` | `/status/activity/<key>` → `activity.show` (not in `app-reference/`) | R |
| `family.html` | `family.html` | `/family` → `family.show` | R |
| `member.html` | `member_form.html` | `/family/<id>` → `family.edit` | R |
| `password-shown.html` | `member_form.html` (`made`) | after POST `family.sign_in_for` | S |
| `you.html` | `you.html` + `own_password_form.html` | `/you` → `family.you` (`own_form`) | R ("Your password", as in the app) |
| `look.html` | `look.html` (built) | `/look` → `look.show`, POST `look.save` (`web/looks.py`) | R: the built Look page in Kitchen Table |
| `look-kid.html` | `look.html` | the same for a kid, just after she chose Fjord (the whole page worn in Fjord) | S |
| `you-kid.html` | `you.html` | the same, a kid | S |
| `you-first.html` | `you.html` (`own.temporary`) | `/you` after a starting-password sign-in | S |
| `signin.html` | `login.html` | `/login` → `auth.login` | R |
| `403.html` | `403.html` | `auth._within_reach` → `REFUSALS[perm]` | R |
| `grownups.html` | `403.html` | the same with `REFUSALS["manage"]` for a kid | S |
| `admin-only.html` | `403.html` | the same friendly page for a parent who isn't an admin, opening Settings, setup or the family list: the app's own `REFUSALS["manage"]` words ("For an admin"), "Sam is the admin in this family", and Home and Status (decided, §9) | S |
| `404.html` | `404.html` | `abort(404)` | R |
| `more.html`, `more-kid.html`, `more-parent.html` | `base.html`'s `details.menu` | none today | N: `GET /more` → `more.html`, the phone account page (an admin's, a kid's, a parent's) |
| `settings.html` | `settings.html` | `/settings` → `settings.show` (`overview()`) | R |
| `settings-<name>.html` (9) | `settings_section.html` + `settings/<name>.html` | `/settings/<name>` → `settings.section` / `settings.personality` (`page()`, `PAGES[name]`) | R |
| `setup.html` | `setup.html` | `/setup` → `setup.overview` | R |
| `setup-<step>.html` (7) | `setup_step.html` + `setup/<step>.html` | `/setup/<step>` → `setup.step` (`PAGES[step]`) | R |
| `setup-telegram-link.html` | `setup/telegram.html`, stage `link` | the same | S |
| `setup-told.html` | `setup/model.html` + `setup_told.html` | the model step after a refused key | S |
| `setup-done.html` | `setup_done.html` | `/setup/done` → `setup.done` | R |
| `states.html`, `states-actions.html`, `states-content.html`, `motion.html`, `type.html` | none | none | D |

**Replaced, merged, new.** Every page template is replaced in place; none is merged away. The partials become macros (section 2):
- `_ask.html` becomes a `composer()` macro.
- `setup_told.html` becomes `told()`.
- `_company_cards.html` and `_key_steps.html` stay includes, with new markup.
- `own_password_form.html` and `password_form.html` stay.

New templates:
- `more.html` (the phone account page);
- `task_form.html`, the to-do's Edit page.

Nothing is deleted.

**Real states not drawn** (build them from the components):
- a parent reading a kid's chat;
- `family.html` with knocks (drawn on `setup-family.html`);
- the Telegram setup stages `connecting`, `refused`, `nobody` and `linked`;
- Google's consent and calendar choice;
- Personality's drift and Restore;
- a revealed key;
- the shared-password shell.

### What the mockups show that the app can't produce today

Each item names the smallest server change. Paths are under `src/familydb/`.

1. **A person's colour slot** (`.p0`–`.p8` on avatars, bubbles, calendar events, owners). Members have no slot.
   - Change: migration `members.slot INTEGER`. `family.add` assigns the lowest free 1–8, and existing rows are backfilled in id order.
   - Expose it in `family._person`, and add `views.slot_of(name, people)`, which gives 0 for Everyone or nobody.
   - Lists that carry only names (`idea.participants`, `task.owner`, chat lines) get a name→slot map, built once per request from `member_store.list_all`.
2. **Looks and light/dark** (`data-theme`, `data-mode` on `<html>`): **built** (`web/looks.py`, the `fdb_look` cookie, `/look`). Kitchen Table adds one look and 66 token roles (§8). **A person's look now follows them** (the family's decision): `members.look` in migration `0037`, written through `familydb/family.py` (§8.5).
3. **The health pill** ("Vera is ready", "Vera is writing back", "Vera is resting until midnight", "Vera can't answer right now", and "Can't answer yet" during setup).
   - Change: add `status.pill(app, conn, chat_id) -> (state, words)`. It is built from:
     - `status.light`;
     - `chat.standing` ("thinking" → busy);
     - `spent_today` against `daily_spend_limit` (rest);
     - `ready_to_answer` (down during setup).
   - The context processor passes it to grown-ups only. Kids never get it.
4. **Nav badges** ("3 late", "1 to decide", "2 to rate", "1 to check").
   - "3 late": a context-processor count of open tasks due before today (`_own_only` for kids).
   - "1 to decide": `len(wish_glance(...).waiting)`.
   - "2 to rate": a new query, "plans in the last 14 days whose idea has no outcome dated after them". The follow-up job already selects these.
   - "1 to check": move `settings.overview`'s look flags into `settings.needs_look(app, conn)`.
   - The phone avatar's dot means any of these is non-zero.
5. **Home's greeting and its useful line**:
   - "Good morning, Sam · Saturday 3 October";
   - "Roller rink tomorrow, and three to-dos are late", with links.
   - Change: `views.greeting(hour, name)` and `views.home_line(coming, late_count)`, which returns the parts and their links. `late_count` must count every open task, not only the four shown.
6. **The next plan's drive time** ("27 min drive, south"). `views.away_from_home` exists but only Ideas uses it.
   - Change: in `home()` and `plans()`, load the idea's place for entries with an `idea_id` and add `away`.
7. **Who a plan is for.** Agenda entries carry no people.
   - Change: `entry_row(entry, today, people=idea.participants)` → `who: [{name, slot}]`. Google-only entries get Everyone.
   - A kid's "Next up for you" filters to entries that name her, or that name nobody.
8. **Month calendar placement** (`.c1`–`.c7`, `.lane1`–`.lane3`, `.len2`).
   - Change: `views.month_weeks` adds `lane` and `len` per event; the column is the loop index.
9. **"Hidden from Maya"** on a present: a present is hidden from **exactly the people it names**, and the label names them (the family's decision). Today gifts are hidden from every kid and nobody is named.
   - **The smallest data change:** one column, `ideas.hidden_from TEXT` (a JSON list of member ids; NULL for anything that isn't a present), in migration `0037`.
     - When a gift idea is saved and no one is chosen, it is filled from `gifts_for` (the people it's for), which the app already knows.
     - Backfill: every existing gift gets its `gifts_for`.
     - A to-do for a present ("Buy Maya's birthday present") hides through the idea it belongs to. A to-do with no idea is never hidden.
   - **`visible_to(viewer)`** changes from "not a kid" to `viewer.id not in hidden_from`, for every role. So a present for Theo now shows on Maya's pages, tagged "Hidden from Theo", so she knows to keep it quiet (`home-kid.html`). A present for Alex is hidden from Alex, a grown-up, which couldn't happen before. Counts are still taken after the filter.
   - **The label** is `"Hidden from " + names joined with "and"`, everywhere a present shows: the tag in a narrow tile, "Surprise · hidden from Maya" in a row.
   - **The idea form**, for a gift, gains "Hidden from": a checkbox per person, ticked for whoever it's for, so a present can also be kept from a chatty sibling.
   - **`docs/DESIGN.md` §16**, the family decision that "presents are hidden from the kids", becomes: *"A present is hidden from the people it's for (and anyone else chosen on it), and everyone who can see it is told whom it's hidden from."* §16 isn't in this folder: replace the line there that hides gifts from every kid with this one.
10. **"Set by Alex"** on a kid's to-do (the family's decision: yes). Tasks don't record who made them.
    - Change: `tasks.created_by_member_id INTEGER NULL REFERENCES members(id)` in migration `0037`.
    - It is set from now on: by `edits.add_task` (the person signed in) and by the chat tool (whoever's message asked for it); NULL while the family shares a password.
    - Existing to-dos stay NULL and show no "Set by" line.
    - It is shown on the kid's to-dos ("Set by Alex", `todo-kid.html`): the kid's own list is where it matters, because a kid didn't set most of them.
11. **"N days late", "Was due Sun 27 Sep"**: `views.late_words(due, today)`, used by both `task_row` and `task_brief`.
12. **A kid's messages left today** ("5 messages left today"). `calls.answered_for` exists, but only Family uses it.
    - Change: compute `left` in `chat.page`, and in `home()` when `roles.daily_limited`.
13. **"Earlier messages"** (`?before=<id>`): add `before` to `message_store.last_for_chat` and to `chat.show`.
14. **Faces on "How did it go?"**: map Loved it / OK / Not great to ratings 9 / 6 / 3 in `edits.record_outcome`. Use the same query as item 4.
15. **Names on the Ideas radar's dots**: add `title` / `short` to each blip in `views.places_radar`.
16. **Status's "How each part is doing"**: `status.health(app, conn) -> [(area, state, words, action)]`. The pill (3) and the settings flags (4) read the same function, so they can't disagree.
17. **Home's "Vera today" card**: pass `spent_today` and the limit to `home()` for grown-ups. "A usual day" is the 30-day total divided by the days that had calls.
18. **The to-do's own Edit page** (decided): `GET /task/<id>/edit` renders `task_form.html` from the fields the fold has today, posting to the same `edits.edit_task`; the row's "Edit" is a link to it, and the fold goes. Why the page: a to-do has seven fields (title, notes, who, deadline, reminder, repeats, status), and on a phone a form that unfolds inside the list pushes the list off the screen and loses your place, while its own page is one short form with a way back.
19. **"Installer" leaves the family's words** (decided: the family wanted the word gone, and "the password FamilyDB started with" says the same thing without it):
    - `status.py`, the sign-in row: "Still the password the installer made up." → "Still the password FamilyDB started with."
    - `status.py`, the page-reach line: "the installer's password; choose your own on the setup page" → "the password FamilyDB started with; choose your own on the setup page"
    - `templates/setup/password.html`: "From then on the password the installer made up opens nothing…" → "From then on the password FamilyDB started with opens nothing…"
    - `templates/settings/security.html`: "Still the one the installer made up." → "Still the one FamilyDB started with."
    - Comments, docstrings and `docs/INSTALL.md` keep "installer": they are for whoever looks after the server, who is the installer.

### Migration `0037`

One migration carries the three columns the family's decisions need. All three are nullable, so nothing breaks before it is used.

```sql
ALTER TABLE members ADD COLUMN look TEXT;                                   -- "rail.dark", as the cookie writes it; NULL: Kitchen Table, following the device
ALTER TABLE tasks   ADD COLUMN created_by_member_id INTEGER REFERENCES members(id);  -- who set it; NULL before 0037 and while the family shares a password
ALTER TABLE ideas   ADD COLUMN hidden_from TEXT;                            -- JSON list of member ids, for a present; NULL otherwise
UPDATE ideas SET hidden_from = <gifts_for as JSON> WHERE <it is a gift>;    -- every present keeps hiding from whoever it is for
```

`members.slot` (item 1) can ride in the same migration if it hasn't landed by then.

No body class for roles is needed: the shell decides each nav item with `visitor().may(...)`, as it does today.

---

## 2. Components → macros

The class names in STANDARD.md §2 are the API, and each component becomes one macro. Existing macro names are kept where the job is the same.

### Changed macros (`_ui.html`)

| Today | Becomes | Parameters | Emits |
|---|---|---|---|
| `icon(name, label=none, cls='')` | `icon(name, label=none, cls='', size='')` | `size='sm'\|'lg'` by keyword | `svg.icon[.icon--sm]`. **The sprite's names change**: `bulb`, `cal`, `chev`, `chevl`, `sliders`, `pulse`, `todo`, `memory` replace `idea`, `plans`, `right`, `settings`, `status`. Add a `mic` symbol for `dictate.js` |
| `presence(cls, variant)` | `vera_screen(size='', state='')` | size `sm`/``/`lg`/`xl`; state `hello` (Home's Ask box: types in once), `busy` (she is writing back: types on a loop) or `off` (§8.10) | `svg.vs` from the geometry table in STANDARD.md §9 |
| `chip(parts, today)` | `date_tile(parts, now=false, size='')` | as `views.date_chip` | `span.dt[--now/--sm/--lg] > .dt__wd .dt__d .dt__m` (weekday first) |
| `crt(cls, hidden)` | `pane(cls='', center=false)` + caller | | `section.pane[--center]`: 403, 404, you-first, the brand rows |
| `radar(blips, rings)` | `radar(blips, rings, wide=true)` | | `svg.radar[--wide/--narrow]` inside `.instrument__pane`; Ideas only |
| `page_head(title, lede, glyph, crumbs)` + caller | `page_head(title, lede=none, crumb=none, overline=none)` + caller | crumb `(words, href)` | `a.crumb` then `div.page-head > div(h1, p.lede) + .head-actions` |
| `chat_line(line, anchor)` | `msg(line, anchor=none)` | | `div.msg.msg--vera` / `.msg--person.p{slot}[.msg--mine/--system/--failed]` > avatar or `vera_screen` + `.msg__bub > .msg__by` |
| `waiting_line(name, state, text)` | `msg_pending(name, state, text)` | | `.msg--pending[role=status]` with the visible "Check for her answer" link |
| `tick(task_id, revision, title, back)` | the same | | `form > button.tick[aria-label="Mark done: …"] > span > icon`; without `change` the row becomes `.todo--ro` |
| `kind_label(kind)` | the same | | `.kind`: the icon and the word, with no colour class |

### Changed (`_settings.html`, `_ask.html`)

| Today | Becomes | Notes |
|---|---|---|
| `box(entry)` | `setting(entry)` (keep `box` as an alias for a release) | `.setting[--bad] > .setting__head (label.field__label + .changed) + control + .field__hint/.field__error#h-KEY`. The pick-or-type box becomes `.pick > select + .pick__another` (ids and names unchanged: `a-KEY`, `KEY_another`) |
| `group(entry)` | the same name | `section.card.sgroup > h2.sgroup__h, p.sgroup__note, .sgrid`; folded `details.card.fold.sgroup > summary(h2, .changed "N changed", chev) + .fold__body` |
| `form(section, groups)` | the same name | `form.sform`, then the groups, then `save_bar()` |
| `grouped_options` | unchanged | |
| `_ask.html` (include) | `composer(viewer, state, where='home'\|'chat')` macro, in the same file | keeps the script hooks (section 4) |

### New macros

In `_ui.html`, as named in STANDARD.md §8:
- `card(title=none, icon=none, more=none, foot=none, tone='', id=none)` + caller
- `banner(tone='', size='', icon=none)` + caller
- `flash(message, undo_url=none)` (replaces base.html's `p.said` loop)
- `error_summary(errors)`
- `tag(state, words, icon=none, more=none)`
- `badge(kind, n, word)`
- `health_pill(state, words, short)`
- `avatar(person, size='')`: emits `span.av.p{{ person.slot }}`, with the house icon for slot 0
- `brand_mark(size='')` and `wordmark()`
- `tile(icon, tone='', size='')`
- `item(lead, title, meta, trail=none, href=none, mod='')`: base.html's nav `item` becomes `nav_item` to free the name
- `todo(row, viewer, compact=false, back)`: picks `--late`, `--done` or `--ro` from the viewer's role
- `rank(wish, viewer)`
- `idea_card(idea, viewer)`
- `field(name, label, kind='text', value='', hint=none, error=none, required=false, dictate=false)`
- `choices(name, options, required, kind='radio', value=none)`
- `disclose(summary, open=false)`
- `fold(title, open=false, danger=false, id=none)`
- `fieldfold(title, open=false)`
- `mini_fold(label, danger=false)`
- `seg(label, links)`
- `faces(plan)`
- `empty(title, text, action=none, center=false)`
- `locked(words)`
- `note(words)`
- `privacy(words, room=false)`
- `srow(href, lead, title, lines, trail=none)`
- `tool_call(call)`
- `shown_once(name, password)`

In `_settings.html`:
- `save_bar(label='Save', still=false)`
- `told(said, problems)` (replaces `setup_told.html` and the settings pages' `p.said`/`p.error`)
- `settings_nav(sections, current)`
- `line_setting(entry)` (Her lines)

In page templates:
- `plan(plan, cancellable)` (was `plan_line`)
- `ev(entry)` and `calendar_week(week)` (was `event`)
- `place(row)`
- `mem(row)`
- `wlist(kid, list, full)`
- `wish_card` changed
- `auto(row)` (settings/messages)
- `setup_progress(steps, current)`
- `todo_adder(people, errors)` (was `fields`)

`page()`, the shell, stays `base.html`: blocks for title, head, body class and content, plus `nav_item(label, href, section, icon, badge=none)` and `tab(...)`. STANDARD.md's "Person picker" isn't built: sign-in never lists the family.

---

## 3. The stylesheet

**`style.css` replaces `static/style.css` whole.** It is not a patch: the current file ("Phosphor", dark only, DM Sans, DM Mono, VT323) shares almost nothing with it.

**Sections** (in order):
1. Fonts
2. Tokens: the fixed layer only, see below
3. Base
4. Shell
5. Components (5.1 Card … 5.26 States, then the stage 8 and 9 components)
6. Pages
7. Phone (≤ 820 px)
8. Forced colours

Section 9 has the settings and setup parts; section 10 the Look page.

**Tokens, in two layers.**
- `style.css` holds what is the same in every look:
  - type (`--font-*`, `--t-*`);
  - space (`--s1`–`--s8`), radii (`--r-*`) and sizes;
  - the brand, which the family fixed: `--glass*`, `--phosphor*`, `--cursor*`, `--vs-halo`, `--mark-glass`, `--glass-scan`;
- `themes.css` holds every colour, one block per look, in the built app's token names. Components use only these semantic tokens, and no component names a raw colour (§8.1).

**Audited.** No literal colour remains in `style.css` outside the token block. The mark's colours moved out of the markup too. Every literal that was there, and its fix:

| Where | Was | Now |
|---|---|---|
| `.av`, `.av > .icon`, `.dots i` | `#FFFFFF` letters | `var(--p-on)`, set per slot by `.p0`–`.p8` from `--pN-on` / `--everyone-on` (Rail and Midnight use dark letters on light avatars) |
| `.ask__last` rule | `rgba(255,255,255,.16)` | `--ask-rule` |
| `.ask textarea:disabled`, `.composer__send:disabled` | `rgba(255,255,255,.12/.18)` | `--ask-fill`, `--ask-fill-2` |
| `.pane::after` scanlines | `rgba(0,0,0,.14)` | `--glass-scan` |
| `.tabbar` shadow | `rgba(60,45,20,.5)` | `--pop-up` (a look's token: Kitchen Table's is warm brown) |
| `.ask .starter*` | three white literals | deleted: the starters left the Ask card in stage 8 |
| the FamilyDB mark SVG | `fill="#0E1312" stroke="#6DFF9C"` in the markup | `.mf__bg` / `.mf__fg` classes reading `--mark-glass` / `--phosphor` |
| the look samples | 10 blocks of preview colours (stage 9) | gone: each sample carries `data-theme` (and `data-mode`) and reads that look's own tokens, as the built Look page does |
| `--sun`, `--sun-2`, `--on-sun` | named after a colour | renamed `--send`, `--send-2`, `--on-send`: the token's only job is the Send button |
| `--info`, `--info-soft`, `--info-line` | defined, never used | deleted |
| `--vera-bg-2` | defined, never used | deleted |

**What's dead in the current stylesheet:** all of it once this lands, about 290 classes. Watch for names that survive **with a new meaning**: a stray old rule or template would collide.
- `.places` was the main nav; it is now the restaurant list.
- `.tools` was the household nav; it is now the activity page's list.
- `.said` was the flash `<p>`; it is now a quoted message (`blockquote`).
- `.radar`, `.thread`, `.ask` (the `<form>` is now `.composer`), `.kind`, `.more`, `.meter`, `.tick`, `.page-head`, `.brand`, `.card`, `.tag`, `.empty`, `.foot`, `.steps` and `.wish`/`.wishes` are all rewritten.
- The body classes `in-{section}` and `to-{section}`, and the kind colours `kind-*`, go: colour is per person now.
- `.starters` stays in `style.css` for one empty-state button on the states sheet. Remove it if that isn't built.

**Fonts** (`static/fonts/`, about 125 KB). They are referenced relative to the stylesheet, so they go next to it:
- `atkinson-400.woff2`, `atkinson-700.woff2`
- `fraunces-soft-600.woff2`
- `fraunces-figures-regular.woff2`, `fraunces-figures-bold.woff2`
- `fraunces-text-figures-regular.woff2`, `fraunces-text-figures-bold.woff2`
- `jetbrains-mono-400.woff2`

DM Sans, DM Mono and VT323 go.

**Brand** (`static/brand/`): `favicon.svg`, `favicon-32.png`, `favicon-16.png`, `apple-touch-icon.png`, `icon-512.png` (the manifest's), and the `mark-16.svg` / `mark-512.svg` sources. They replace `static/favicon.svg` and `static/apple-touch-icon.png`; `scripts/icons.py` no longer draws them.

**The head of `base.html`:**
```html
{# the built head, kept: web/looks.py gives look, look_mode, look_scheme and look_colours #}
<html lang="en-GB" data-theme="{{ look.key }}"{% if look_mode != 'auto' %} data-mode="{{ look_mode }}"{% endif %}>
<meta name="color-scheme" content="{{ look_scheme }}">
{% for media, colour in look_colours %}<meta name="theme-color" content="{{ colour }}"{% if media %} media="{{ media }}"{% endif %}>{% endfor %}
<link rel="preload" href="{{ url_for('static', filename='fonts/atkinson-400.woff2') }}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{{ url_for('static', filename='fonts/fraunces-soft-600.woff2') }}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='themes.css') }}">
<link rel="icon" href="{{ url_for('static', filename='brand/favicon.svg') }}" type="image/svg+xml">
<link rel="icon" href="{{ url_for('static', filename='brand/favicon-32.png') }}" sizes="32x32" type="image/png">
<link rel="icon" href="{{ url_for('static', filename='brand/favicon-16.png') }}" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="{{ url_for('static', filename='brand/apple-touch-icon.png') }}">
```
Only Atkinson 400 and Fraunces 600 are preloaded, because every page uses them for body text and the h1. The figure and mono subsets are small and used on some pages only.

---

## 4. Rules kept

**Content security policy.** `default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'`.
- No `style=""`, no inline `<script>`, no `on*=`. Data-driven geometry uses SVG presentation attributes, which CSP allows: the spend meter's `rect width`, the radar.
- Calendar placement uses classes. Looks are token blocks chosen by attributes on `<html>` (§8), so nothing is ever computed into a style.
- Add a CI check that fails on `style="` or an inline `<script>` in `templates/`.

**Scripting off.** Every page reads, and every form works, with no script.
- The pattern is POST → redirect → GET, with a flash in the session and an `#anchor` back to what changed.
- `<details>` handles filters, options and fine-tuning, opened server-side when one holds an error or an active filter.
- Chat opens at the newest message (`column-reverse`).
- While a reply is pending, a short meta refresh backs off: 3 s, then 5, then 10, and stops at 60 s.
- The Look page is radios and a Save, as built.

**The existing scripts.** Keep the app's four and give them the hooks below. Don't write the four that STANDARD.md §8 names: their jobs are already in `ask.js`, apart from the optional `password.js`.

| Script | What it needs from the new markup |
|---|---|
| `ask.js` | `id="ask"` on `form.composer` (not on Home's `section.ask`); `data-refresh` on it; `textarea[name=text]` with `id="text"` (the mockups' `ask-text`/`msg` are placeholders, so keep `text`); the hidden `lat`/`lon` inputs; the hidden `#locate` box with `input[name=send_where]`, labelled "Share where I am with this message"; `p#where`; `id="latest"` on the last `.msg`. It reads `.msg--pending` and `.msg--vera`, no longer `li.pending` and `.said-bot`. Its starter code goes dead (`?ask=` still prefills). The kid's "Tell Vera I did it" must use `?ask=…#ask`, not the mockup's `?draft=…#msg` |
| `menu.js` | **retired.** The `details.menu` is gone: the desktop has the sidebar and its account corner (`.me`), and the phone's avatar links to `/more` |
| `wishes.js` | `ol.wishes[data-list]`, `li.wish[data-wish][data-rank]`. The handle is `.rank__n`, the move form `form.wish__move`, the actions `.wish__acts`: change the selectors, or keep the old class names alongside. Every form keeps `hidden(kid)` (csrf, once, kid). Add CSS for `.can-drag .rank__n` (44 px, `touch-action: none`) and `.wish.dragging` |
| `dictate.js` | `data-dictate` on the same boxes as today (the mockups leave it out); each such box sits directly inside its `.field`; `span.mic-slot#ask-mic` in `.composer__row` before Send; an `i-mic` symbol in the sprite; the `<script data-icons>` in the head. New CSS for `button.mic`: 44 px, `--edge` border, phosphor while `.listening` (it is live), no motion under reduced motion |

**Accessibility**: measured, and kept (STANDARD.md §7 has every pair).
- Words are AA: body text 13.9:1 by day, 15.7 at night; the quietest text, `--ink-3` on the sidebar, is 5.1.
- Controls are 3:1: field edges 3.9, the primary button against the page 6.9 / 3.5.
- Avatar letters are 5.4–7.4.
- Phosphor on glass is 14.7. The focus ring is 3 px: ink on paper, phosphor on glass, the panel's ink on the panel.
- Targets are 44 px. Type is 14 px or more (13 px only for tab labels and overlines), in rem.
- Nothing is told by colour alone: late says "6 days late", tags carry words, events carry spoken labels.
- Nothing blinks for more than five seconds. The wordmark cursor blinks four times, about four seconds, then stays lit: its `animation` had a typo (`2te`) that stopped it altogether, and that is fixed. Only Vera's sign and the pill's dot loop, and only while she is writing back (§8.10). `prefers-reduced-motion` stops everything.
- `forced-colors` gives every selected state a real border.
- No sideways scrolling at 320 px or 200 % zoom.
- `_kit/looks-check.py` measures the colour pairs for every look, on Kitchen Table's layout as well as the built pages'.
- People's colours are not checked against each other under colour blindness (the family's decision): a name or an initial is always beside a colour, so colour never has to carry it alone.

**Kids**:
- Kids never see costs, models or workings: no health pill, no Status, no money, no setup, no "used …" lines. This is a standing family decision.

**Grown-ups**: Status, and the health pill, are for every grown-up, parents as well as admins, as the app has it (`browse`). Settings, Family and setup stay an admin's (`manage`). `home-parent.html` and `more-parent.html` draw Alex, a parent.
- A kid's footer has no version number.
- Kids see only their own chat and their own to-dos.
- A page their role can't reach shows a kind refusal in the real words.

**Presents**:
- A present is hidden from exactly the people it names (by default whoever it's for): for them, no row, no count, no greyed item.
- Everybody else, a kid included, sees it tagged with their names: "Hidden from Theo", "Surprise · hidden from Maya".
- Counts are taken after filtering (`visible_to(viewer)`).

---

## 5. Words for `views.py` and the templates

Only deliberate wording changes are listed. The sample family (Sam, Alex, Maya, Theo, every idea, time, price and count) is data.

**Throughout**
- "the bot" → `{{ assistant }}` (Vera), wherever the family reads it: `ROLE_WORDS["kid"]`, `AGENDA_NOTES`, `ALERT_TITLES["calendar"]`, the Family and member pages, the empty states.
  - `fields.py`'s help for kids' wishes ("something the bot said no to") still says "the bot": change it too.
- Contractions in page text: "There is nothing" → "There's nothing", "does not" → "doesn't", "is not connected" → "isn't connected", "I am sure" → "I'm sure", "anything you would ask" → "anything you'd ask".
- British spelling: "Organize" → "Organise", "neighborhood" → "neighbourhood".
- A kid is "her" or "his" by the gender on her record, never "them": "Take her password away", "Linking her Telegram", "She signs in as Maya…".
- No arrows in buttons: setup's "← Back" / "Next →" / "Skip for now →" / "Skip this →" / "Carry on: X →" / "Start →" lose them; the icon draws the chevron.
- `<span class="optional">optional</span>` → "(optional)" / "(required)" written into the label.
- Tags in sentence case:
  - setup: "Done", "Needed", "Recommended", "Optional";
  - Family: "Admin", "Parent", "Kid", "Age 41", "Signs in", "Starting password".

**Shell**
- Skip link: "Skip to the page" → "Skip to content", and its target `#content` → `#main`.
- Nav: "{assistant}" / "Chat" → "Chat with Vera" (tab bar: "Chat"); "Memory" → "What Vera knows"; a "Behind the scenes" group: Status for every grown-up, Settings and Family for an admin (a parent sees Status alone; a kid sees no group).
- A kid's "To do" → "My to-dos".
- The menu's "Your password" stays, and **Look** sits beside it (the built menu's item): the account corner reads "Look · Your password · Sign out", the phone menu has a Look row.
- The Status light ("Status: needs a look" ▲ / "not answering" ■) → the health pill:
  - "Vera is ready" ("Ready" on the phone);
  - "Vera is writing back";
  - "Vera is resting until midnight";
  - "Vera can't answer right now";
  - during setup, "Can't answer yet".
- Phone menu page (`/more`): lede "Everything that isn't in the tab bar." A kid's: "Your other pages, and signing out."
- 404: `<title>` "Page not found"; eyebrow "404 · nothing on the radar"; "There's nothing at that address."
- 403 keeps `REFUSALS`. The readout becomes "403 · signed in Maya · role kid".
- A kid on Settings: "This part is for grown-ups" / "Settings, setting up and the family list are changed by an admin. There's nothing here you need to do: ask Sam if something here needs to change." It names the admins.

**Home and Chat**
- The h1 "What's on your mind?" loses its glowing span.
- New: "Good morning, Sam · Saturday 3 October" and the useful line (section 1, item 5).
- `STARTERS` / `WEEKEND_QUESTION` / `TODAY_QUESTION` no longer appear under the box. Keep `WEEKEND_QUESTION` for setup's "Ask …".
- Under the box:
  - Home: "Goes to the family chat as Sam."
  - Chat: "Writing as Sam".
  - Shared password: the "From" picker, with no "who is asking?" option, so nothing is picked by default.
- "Send where I am" → "Share where I am with this message".
- "Open the conversation" → "Continue with Vera".
- Next up: "All plans", "See the plan", "After that", "3 more plans this month". Empty: "Nothing planned yet."
- To do card: "All 4 to-dos". Empty: "No to-dos. Tell Vera “remind me to call the dentist on Tuesday”, or add one on To do."
- "Lately added" → "Just added to Ideas".
- "The kids' wishes" → "Wish lists".
- A kid's "Next up" → "Next up for you".
- Chat: h1 "Chat with Vera". The kids' panel note gains "…the kids see a note saying so at the top of theirs."

**Ideas and an idea**
- Capture: "A restaurant, a food cart pod, a neighbourhood, a kids' outing, a special occasion, or just a direction to explore. Write it the way you'd say it; Vera organises it and says in the chat what she saved."
- Its button: "Organise in the chat". Its hint becomes the link "Or add an idea yourself".
- "Search" → "Search ideas". New: "All ideas, newest first", "12 ideas".
- Radar: "How far each idea is from home", "Show the map" (phone), ring labels "15 min, 30 min, 1 h, 2 h, 3 h" (`PLACE_RING_LABELS`).
- Empty: "No ideas yet. When someone says “we should try…”, Vera saves it here."
- Restaurants: "Details may be out of date"; "for {who}" → "{who}"; empty "Mention a new place to Vera in the chat and it appears here."
- Idea form:
  - edit `<title>` and h1 "Edit #12" → "Change this idea", with "Idea #12" above;
  - new idea `<title>` "Add an idea";
  - labels "Title (required)", "Kind (required)", "Description (optional)", "Who it's for" ("Commas between them.");
  - "Everything else · where, when, who, cost, how long".
- An idea: "The place", "Opening hours this week", "At a glance", "Looking it up", "Plan it again" (once it's been planned).
- Flashes:
  - `TICKED` "Done: #N title." → "Ticked off: {title}." (with Undo once Undo exists);
  - `WISH_ANSWERED` → "Answer saved: Yes to “{title}”. Maya can see it now."

**To do and Plans**
- "Things to do" → "To do", plus "4 open, 3 of them late."
- "Add something to do" → "Add a to-do"; "Save task" → "Add"; "For" → "Who's it for?"; "Notes" → "Notes (optional)".
- "New reminder / snooze until" → "New reminder or snooze until"; "Cancel pending reminder" → "Cancel the pending reminder".
- The reminder note: "Reminders appear in the chat while FamilyDB is running; they aren't phone notifications. With Telegram connected, they go there too."
- "Show" becomes the tabs "Open / Done / Cancelled / All". "Search" → "Search to-dos".
- `AGENDA_NOTES["saved"]`: "Google Calendar isn't connected, so these are the plans Vera made."
- Plans ledes:
  - list: "What's on the family calendar for the next three months, and what happened lately."
  - month: "What's on the family calendar. After each plan, Vera asks how it went."
- Month nav: "Earlier / Later" → icon buttons named after the months.
- "Move it", "Cancel it", "Yes, cancel it", "New time" and "Put it on the calendar" are kept.

**Wishes, memory, family, you**
- "A note for Maya (optional)".
- New: "Planning a present? Add it as a gift idea instead: wishes aren't secret…".
- "What {assistant} remembers" → "What Vera knows"; "Must", "A guess", "Until (optional)".
- New key: "How Vera weighs these".
- `FORGOTTEN`: "won't come back".
- Family:
  - lede: "Who Vera talks to. Each person signs in as themselves, with a password of their own: open somebody to give them a starting password."
  - "Change" → "Change {name}".
  - "Asked to talk to the bot" → "Waiting to be let in".
- Member:
  - lede "Kid · 11 · on the list";
  - "Yes, Vera talks to her / No, switched off";
  - "…she hasn't used yet";
  - "I'm sure: take Maya off for good".
- Shown password: "Shown this once: send it to Maya now. She signs in as Maya with it, and chooses her own password straight away. Once you leave this page it can't be shown again; make a new one if it's lost."
- Your password: the app's title, h1 and lede, plus "How it looks is on Look, for each browser." The tips get the heading "Good to know".
- Look: the built page's words (`look.html`, `looks.MODE_WORDS`, the looks' blurbs), now that a look follows the person (§8.5):
  - the lede: "How the page looks for you. It is kept with your name, so it comes with you to every phone and computer you sign in on, and everybody else keeps their own.";
  - the flash: "Saved. You'll see … on every phone and computer you sign in on." (was "Saved. This browser wears … from now on.", which stays only while the family shares one password);
  - Match my device: "Day by day and night by night, as each phone or computer does.";
  - New: Kitchen Table's blurb, "The family's table: cream paper, deep green, and each person in their own colour."; the tag "The default"; the line by Save, "Yours alone, on every device you use."; the phone menu's row "Yours, on every phone and computer you sign in on" (a kid's: "Yours, on every phone and computer you use").
- Setup and Status: "installer" is gone from what the family reads (§1, item 19).
- Setup and settings keep `fields.py`, `settings.py` and `setup.py` word for word, apart from:
  - the arrows;
  - the tag case;
  - "/settings" gains "Only an admin can change these.";
  - the save bar's "An empty box uses the default it shows.";
  - "Another model…" / "Another Telegram chat…".
- Status:
  - lede "Is Vera working, and what is she costing? Checked when you opened this page.";
  - the verdict line ("Vera is ready, and well under budget.") is composed by a new `status.verdict()`;
  - "Spent today", "Last 30 days", "Where the money went", "Technical details: which AI answers each job".

---

## 6. Order of work

Each step is one pull request that leaves the app working. Every PR runs the tests (`tests/test_look.py` among them) and the CSP check.

1. **Kitchen Table as a look, on today's layout.** This can land now, before anything else:
   - the `[data-theme]` block of derived roles, the `[data-theme="kitchen"]` block and the two additions into `static/themes.css`;
   - the line in `looks.py`.
   - Test: `test_look.py` as changed in §7 (every look names the built set; the contrast floors hold for Kitchen Table by day and by night). The family can try Kitchen Table's colours on the Look page.
2. **Static files.** Fonts, brand, sprite and the new `style.css`, side by side with the old ones and not yet linked.
   - Test: the files serve; `python3 _kit/looks-check.py` passes for every look.
3. **The shell.**
   - `base.html`: head, sidebar, account corner, top bar, tab bar, footer, flash.
   - The `/more` page; `menu.js` retired.
   - `icon()` with `size` and the new names.
   - `avatar` with `members.slot` (migration).
   - Test: the nav per role (admin, parent, kid), `aria-current`, skip link, the footer without a version for kids, the CSP check.
4. **Home**, including:
   - `composer()` with the `ask.js` hooks;
   - `views.greeting`, `home_line`, `late_words`;
   - the health pill (`status.pill`);
   - the kid's Home.
   - Test: Home for each role; send with scripts off; no costs for a kid; no gifts for a kid.
5. **Chat**: `msg`, `msg_pending`, `#latest`, the refresh back-off, "Earlier messages".
   - Test: pending, then answered with scripts off; a kid sees only her own chat.
6. **To do and Plans**:
   - `todo`, `tick`, `todo_adder`;
   - the to-do's own Edit page (`task_form.html`, §1 item 18), replacing the fold;
   - "Set by" on a kid's to-dos (`tasks.created_by_member_id`, migration `0037`);
   - the month calendar (`month_weeks` lanes) and the list;
   - who a plan is for.
   - Test: tick with scripts off; `aria-current="date"`; "Move it" still in a `details`.
7. **Ideas, an idea, the idea form, Restaurants**: `idea_card`, `kind_label`, the radar with names; a present's "Hidden from" (`ideas.hidden_from`, migration `0037`).
   - Test: search and filters (GET); a present hidden from exactly the people it names and shown, tagged, to everyone else (a kid included); the form's errors.
8. **Wishes and What Vera knows**: `wish_card` with the `wishes.js` hooks, the three lists, answers.
   - Test: move up/down with scripts off; drag with `wishes.js`; answer a wish.
9. **Family, member, Your password, Look**:
   - starting passwords shown once;
   - you-first;
   - the Look page in Kitchen Table (`look.html`: the built form, the new markup, the samples kept as `look-sample`);
   - a person's look kept with them (`members.look`, migration `0037`, §8.5).
   - Test: the password flows; `test_look.py` on the new markup.
10. **Settings**: `setting`, `group`, `save_bar`, `told`, `settings_nav`, every section page.
    - Test: save, an emptied box returns to its default, a complaint opens its fold, only an admin sees it.
11. **Setup**: the overview, the steps, done, told.
    - Test: each step's form posts and comes back with what it said; Telegram's refresh.
12. **Status and activity, 403, 404, sign-in.** `status.health` and `status.verdict`.
    - Test: Status for every grown-up (an admin and a parent), never a kid; the refusal pages.
13. **Clean-up**: delete the old stylesheet's leftovers, the `box` alias, the Lucide sprite and the old favicons. Land `docs/STYLE.md` from `STYLE-draft.md`.

---

## 7. Tests that will change

No tests are in `app-reference/`. STYLE.md and the code name four pins that change, and the rest is inferred from the markup the templates carry: search the test suite for each quoted string.

1. **`class="panel card"`** on list items → `article.idea`, `article.place`, `li.wish`, `li.todo[.todo--late]`.
2. **`class="said"`** as the flash → `.banner.banner--ok.flash[role=status]`; on settings and setup, `.told > .banner--slim`. `.said` now marks a quoted message.
3. **`<summary>Move it</summary>`** → `details.mini-fold > summary` with the same words. The test survives if it checks the text.
4. **`class=" today"`** on the month → `day--today` plus `aria-current="date"`; `outside` goes.
5. **Body and nav classes**: `in-{section}`, `page-chat/-lost/-signin/-status`, `header.bar`, `nav.places`, `nav.tools`, `a.to-*`, `span.label`, `details.menu`, `.menu-list`, "All settings", `.menu-who`, `form.signout` → `aside.side nav ul.nav`, `.nav-group` "Behind the scenes", `.me`, `.topbar`, `.tabbar`, `/more`. Also "Memory" → "What Vera knows". The menu's Look and Your password stay, in `.me__acts` and on `/more`.
6. **The Status light**: `.to-status.lit-warn/-bad`, ▲/■, "Status: needs a look" → the health pill.
7. **Vera's glyph**: `span.presence.v0`–`v3 > .presence-glass` → `svg.vs` (`.vs--hello` on Home's Ask box, `.vs--busy`, `.vs--off`).
8. **The thread**: `ol.thread > li.said-bot/.said-them`, `.said-by`, `.said-text`, `.did` → `div.thread > .msg.msg--vera/.msg--person`, `.msg__by`, `.msg__bub`. `#latest` and `THINKING` stay.
9. **The box**:
   - `form.ask#ask` → `form.composer#ask`;
   - `.ask-bar .from` "From Sam" → `.composer__foot` / `.composer__who`;
   - `button.send` → `button.composer__send`;
   - `ul.starters` **removed**: any test on starters fails;
   - "What’s on your <span" → plain "What’s on your mind?".
10. **The tick**: `form.tick-form` with `.sr` "Done: …" → `button.tick[aria-label="Mark done: …"]`; `span.task-box` → `.todo--ro`.
11. **Page heads and titles**:
    - `.page-title`, `nav.crumbs`, `.title-row`, `.page-actions` → `a.crumb`, `.page-head`, `.head-actions`;
    - "Things to do" → "To do"; "What Vera remembers" → "What Vera knows"; "Edit #12" → "Change this idea";
    - `<title>` "Not found" → "Page not found", "New idea" → "Add an idea".
12. **Dates**: `span.chip > .chip-mon/-day/-dow` → `span.dt > .dt__wd/.dt__d/.dt__m` (weekday first).
13. **Green screens**: `.crt`, `.next-up`, "N more on the radar", `.radar .blip.bN`, `.on-radar*`, the spend `.readout`, `.lost-readout` → gone. Next up is a card; the Ideas radar has names; `PLACE_RING_LABELS` changes.
14. **Kinds**: `.kind-restaurant` etc. → `.kind` only.
15. **Status**: `.monitors`, `#attention` "Needs attention", `.spend`, `.lights` → the verdict, figures, "How each part is doing", "Connected to", "Where the money went", "Recent activity", "Waiting", "Worth a look".
16. **Settings**:
    - `ul.section-cards > .section-card` → `.slist > a.srow`;
    - `.setting-head` → `.setting__head`;
    - `.another` → `.pick__another`;
    - `.save-bar` stays.
17. **Setup**:
    - `.setup-list > li.panel.done`, `.number`, `.need-*` → `a.setup-row[--done]` with tags "Done", "Needed", "Recommended", "Optional";
    - `p.state.done` → `.state-done`;
    - the step nav loses its arrows.
18. **Family**: `ul.people > li > span.avatar.role-*` with lowercase tags → `.items.fam`, `.role--admin/--parent/--kid`, "Age 41", "Change {name}".
19. **Wishes**: `li.panel.card.wish`, `.wish-rank`, `.wish-actions` → `li.wish`, `.rank__n`, `.wish__acts` (`data-wish` / `data-rank` kept).
20. **Flash texts after a POST**: `TICKED` and `WISH_ANSWERED` change (section 5).
21. **The head**:
    - the `dm-sans.woff2` preload → Atkinson and Fraunces;
    - `favicon.svg` → `brand/favicon.svg`;
    - `color-scheme dark` and `theme-color #0b0e0d` for a first visit → `light dark` and Kitchen Table's two band colours, once Kitchen Table is the default (see 22);
    - `lang="en"` → `en-GB`.

22. **`tests/test_look.py`**, the built look tests. What Kitchen Table changes there:
    - **When Kitchen Table is added as a look** (§6 step 1):
      - `test_every_look_is_written_down_once_in_the_stylesheets` holds every block to the same set of tokens. Kitchen Table names 66 more (its people, washes, Vera's box, Send, the panel's links), and the `[data-theme]` block gives them to every look. Exclude those 66 from the comparison, as `--sect` is excluded today, or every other look fails.
      - Its regex reads `[data-theme="([a-z]+)"]`: the key `kitchen` fits it, which is why it isn't `kitchen-table`.
      - Its first check reads one block per look, so a look's addition (Enamel's and Home Computer's `--on-vera`) must go inside its own block.
      - `test_a_look_is_a_set_of_tokens_and_nothing_else` still passes: the derived block is `[data-theme]`.
      - `test_every_look_keeps_the_contrast_floors_by_day_and_by_night` passes for Kitchen Table as it is. Add Kitchen Table's layout pairs (the panel's links and current item, Vera's box and Send, words on Vera's fill, the late plate, each meaning on its wash, each person's name, letter and mark) from `_kit/looks-check.py`. No colour-blind checks: the family decided against that floor.
    - **When Kitchen Table becomes the default** (§8.2):
      - `test_the_page_is_phosphor_and_follows_the_device_until_somebody_chooses` becomes "…is Kitchen Table…": `("kitchen", None)`, `content="light dark"`, and `#EFE7D7` by day, `#121816` by night.
      - `test_phosphor_has_no_day_to_choose` stays.
      - `test_nothing_but_a_look_this_page_has_is_kept`, `test_a_cookie_that_names_no_look_is_the_default` and `test_a_form_from_another_site_does_not_change_the_look` expect `("kitchen", None)`.
      - In `test_every_look_is_written_down_once…`, Phosphor is now a block in `themes.css`, so `set(blocks) == {looks other than the default}` holds with Kitchen Table out and Phosphor in. But `assert one.has_day` must skip Phosphor, as must `"color-scheme: light dark" in blocks[...]`, and the check that the default sits in `style.css` reads `[data-theme="kitchen"]`.
      - `test_the_look_page_offers_every_look_in_its_own_colours` still passes: the samples keep `class="look-sample" data-theme="…"`.
    - **When a look follows the person** (§8.5):
      - `test_choosing_a_look_keeps_it_in_this_browser` becomes "…keeps it for this person": the POST stores `rail.dark` on the member and still sets the cookie; the flash is "Saved. You'll see Rail yellow on every phone and computer you sign in on."
      - New: signing in on a second client brings the look (the first client chooses Ink; a fresh client signs in as the same person and gets `data-theme="ink"` and the cookie).
      - New: two people on one client keep their own (Sam's Ink, then Maya signs in and gets her own, or Kitchen Table).
      - New: while the family shares one password, the look is the cookie's only, and nothing is written to a member.
      - New: a stored value that names no look is the default, as a bad cookie is.
      - `test_the_look_is_for_anybody_signed_in_and_nobody_else` stays: kids choose their own.
    - **The web AST test** (the one that names what each web module may call) gains one line: `web/looks.py` may call `familydb.family.choose_look`. That is its only call into the rules; it never reaches `store.members` itself.
    - **Status for parents**: a test that a parent gets `/status` (200) and the pill, and a kid gets the refusal and no pill.

Unaffected: `test_browsing_asks_nothing_of_a_model`. "Every name in BEHAVIOUR appears exactly once" is unaffected too: the look is a member's column and a cookie, not a setting.

---

## 8. Looks (themes), as the app built them

The family's engineers have already built theme support into the current app (`app-reference/built-looks/`, the two commits in `COMMITS.txt`). That mechanism is the app's, and this design fits it.

### 8.0 What was built

- **Every colour is a token.**
  - The built `style.css` writes Phosphor's tokens at the top, as `:root, [data-theme="phosphor"]`.
  - It uses the names every palette sheet uses: `--paper`, `--card`, `--ink`, `--band`, `--here`, `--primary`, `--today`, `--red`, `--amber`, `--ok`, `--vera`…
  - The page's older names (`--bg`, `--surface`, `--green`) are read from them.
- **A look is one block in `static/themes.css`**:
  - `[data-theme="rail"] { color-scheme: light dark; --paper: light-dark(day, night); … }`;
  - each colour is written once, with its day and its night;
  - the page follows the device, or `data-mode="light|dark"` on `<html>` holds it (`[data-theme][data-mode="light"] { color-scheme: light }`).
- **Seven looks are listed in `web/looks.py`**: Phosphor (the default, dark only), Midnight, Home Computer, Ink, Enamel, Rail yellow and Fjord. Each has its name, blurb, whether it has a day, and the band's two colours for `theme-color`.
- **The choice is a cookie per browser**, `fdb_look` ("rail.dark"). (Now also kept with the person: §8.5.)
  - It is set on the Look page (`/look`, in the menu, for anybody signed in, kids included).
  - It is not in the database. Anything that isn't a known look is the default.
- **`base.html`** writes `data-theme`, and `data-mode` only when held; `<meta name="color-scheme">` from `looks.scheme()`; `theme-color` from `looks.theme_colours()`; and links `themes.css` after `style.css`.
- **`tests/test_look.py`** holds:
  - the cookie and the form (CSRF, origin, known looks only);
  - every look naming the same tokens, and no fewer than Phosphor names;
  - `themes.css` holding only tokens;
  - each look's band matching `looks.py`;
  - the contrast floors, by day and by night.
- **Not yet built** (the built STYLE.md says so): a colour for each family member, and a household default.

### 8.1 Token names: Kitchen Table now uses the built ones

Every token Kitchen Table's layout reads is now named as the built set names it. `style.css` here was renamed to match. Nothing moved: every page re-rendered pixel for pixel the same, except the pages whose content changed in this stage (the Look page, General, Your password, the menu).

**Same role, built name adopted** (stage-10 name → built name):

| Stage 10 | Built | Stage 10 | Built |
|---|---|---|---|
| `--side` | `--band` | `--today-bg` | `--today` |
| `--side-ink` | `--on-band` | `--alert` | `--red` |
| `--side-ink-2` | `--on-band-2` | `--warn` | `--amber` |
| `--side-hi` | `--band-hi` | `--primary-2` | `--primary-hover` |
| `--side-line` | `--band-line` | `--shadow-lift` | `--pop` |
| `--side-mark` | `--here-icon` (and the current item is `--here` / `--on-here`) | `--shadow-up` | `--pop-up` |
| the wordmark's `--cursor` (fixed) | `--cursor` (a look's token) | | |

These names were already the same: `--paper`, `--paper-2`, `--card`, `--field`, `--ink`, `--ink-2`, `--ink-3`, `--line`, `--line-2`, `--edge`, `--link`, `--primary`, `--on-primary`, `--focus`, `--on-today`, `--vera`, `--vera-bg`, `--ok`, `--ask-bg` and `--shadow`.

**Roles Kitchen Table needs that the built set lacks: add these 66** (the `[data-theme]` block in `themes.css` gives every look a value for each, so no look has to name them):

| Add | Job in Kitchen Table's layout | Every look gets, unless it names its own |
|---|---|---|
| `--band-link` | links in the panel (the account corner) | `var(--on-band)` |
| `--ok-soft`, `--ok-line`, `--amber-soft`, `--amber-line`, `--red-soft`, `--red-line` | each meaning's wash and rule (tags, banners, the setup card, late rules) | 10 % / 35 % of the colour on `--card` (the built tags' own 10 % tint) |
| `--on-red` | words on a late plate | `var(--on-bright)` |
| `--on-vera`, `--vera-soft`, `--vera-line` | words on her green fills; her pill and bubbles; her bubble's rim | `var(--on-bright)`; 10 % / 35 % of `--vera` on `--card` |
| `--ask-ink`, `--ask-ink-2`, `--ask-rim`, `--ask-edge` | words, rim and box edge of her Ask box | `var(--ink)`, `var(--ink-2)`, a `--line` rim, `var(--edge)` |
| `--ask-rule`, `--ask-fill`, `--ask-fill-2` | rules and dimmed fills inside it (were fixed white) | 16 / 12 / 18 % of `--ask-ink` |
| `--send`, `--send-2`, `--on-send` | Send in her box | `var(--primary)`, `var(--primary-hover)`, `var(--on-primary)` |
| `--p1`…`--p8`, each with `-soft`, `-ink`, `-mark`, `-on`, and `--everyone` with the same (45) | **a colour for each family member**, the built STYLE.md's "not yet" | Kitchen Table's eight, by day and by night, until a look gives its own |

Two built tokens that Phosphor doesn't name, `--here-icon` and `--here-pill`, get `var(--on-here)` / `var(--here)` in the same block. Phosphor-as-a-look names them itself (8.2).

**Fixed in every look**, in `style.css`'s fixed layer, as the built app keeps "the green screens, the radar, her screen and the mark" literal:
- `--glass`, `--glass-2`, `--glass-line`, `--glass-ink`, `--glass-ink-2`, `--glass-alert`, `--glass-scan`;
- `--phosphor`, `--phosphor-dim`, `--phosphor-glow`;
- `--mark-glass`, `--cursor-glow`, `--vs-halo`.

Their night is `light-dark()` too, so there are no media queries left. The built `--screen` is the same colour as `--phosphor`: keep one name, `--phosphor`, and alias `--screen: var(--phosphor)` while the old layout lives.

**Built tokens Kitchen Table's layout doesn't read.** The Kitchen Table look still gives each a value, so the old layout reads in it too, and every look keeps naming the same set:
- the parts of the site and kinds: `--lilac`, `--cyan`, `--lemon`, `--pink`, `--orange`, `--on-bright` (Kitchen Table's kinds are neutral; its values are its people's inks);
- one person: `--person`, `--on-person`;
- light and depth: `--bloom`, `--glow`, `--glow-hover`, `--wash`, `--wash-faint`, `--shade`, `--hi`, `--scan`, `--raster`, `--bar-bg`, `--band-tabs`;
- the rest: `--paper-3`, `--faint-ink`, `--lit`, `--today-rule`, `--today-wash`, `--error-ink`, `--here-pill`.

`--sect` is only for the old layout's quiet looks, so Kitchen Table leaves it out.

### 8.2 Kitchen Table as a look, and as the default

`themes.css` here is the built file fitted to Kitchen Table. Its parts:
1. **The `[data-theme]` block**: the 66 roles above, worked out for every look.
2. **`[data-theme="kitchen"] { color-scheme: light dark; … }`**: Kitchen Table, one block, every token as `light-dark(day, night)`, exactly as it would sit in the built `themes.css`.
   - The key is `kitchen`, not `kitchen-table`: the built test reads looks with `[a-z]+`, and `looks.py`'s keys are one word (`homecomputer`).
   - Its line in `looks.py`:
   ```python
   Look("kitchen", "Kitchen Table",
        "The family's table: cream paper, deep green, and each person in their own colour.",
        True, ("#EFE7D7", "#121816")),
   ```
3. **Phosphor, as a look** (dark only), copied from the built `style.css` with two tokens added (`--here-icon`, `--here-pill`).
4. **The six built looks, verbatim**, plus two additions (8.4), and the two `data-mode` rules.

**Kitchen Table becomes the default when the new layout ships** (the family's decision), for every person who hasn't chosen another look. Not before: its layout is built around a light page, and Phosphor's layout is the one being replaced.

Until the new layout ships, Kitchen Table can go in as one more look on the old layout, now: one block and one line in `looks.py`. Its built-set tokens are all named, so the old pages read in its colours.

When it becomes the default:
- `looks.DEFAULT = "kitchen"`.
- `style.css` writes Kitchen Table's built-set tokens at its top as `:root, [data-theme="kitchen"]`, with `color-scheme: light dark`. That is what the default sits under every look as, so a look that names no `--p1` shows Kitchen Table's people, as here.
- **What `style.css` must stop assuming**, all built for Phosphor being dark only:
  - the default's `color-scheme: dark`;
  - `looks.scheme()` / `theme_colours()` treating the default as having no day;
  - base.html's `<meta name="color-scheme" content="dark">` for a first visit. It becomes `light dark`, and `theme-color` gets two metas (`#EFE7D7` by day, `#121816` by night).
  - The new layout's own `style.css` (this folder's) already assumes nothing about day or night: every colour is a token, and the glass's night is `light-dark()`.
- **Phosphor moves into `themes.css`** as `[data-theme="phosphor"]`. Its block has no `light-dark()` and stays `color-scheme: dark`; the two `data-mode` rules already skip it.
- **Anyone who chose a look keeps it.** A choice made before `0037` lives only in a cookie: the first time that person signs in or opens a page after the release, a cookie that names a look is copied to their `members.look` (once, only while it is NULL). Everybody else sees Kitchen Table at once.
- **The release note's line:**
  > FamilyDB has a new look, Kitchen Table: cream paper by day, charcoal at night, and each of you in your own colour. If you chose a look before, you keep it. To change yours, open Look from the menu; it now follows you to every phone and computer you sign in on.

**The other looks under Kitchen Table's layout.** They recolour any layout, and they still read on Kitchen Table's shapes.
- **Rendered:** Home and a kid's Home in Rail yellow, Midnight and Phosphor, day and night, desktop and phone, in `shots/looks/` (pages in `looks-test/`).
- **Rendered too:** Maya's Look page (`look-kid.html`) is worn in Fjord, so it is a whole page of Kitchen Table's layout in a built look.
- **What changes, by design:**
  - The paper looks (Rail, Ink, Enamel, Fjord, Home Computer) set `--ask-bg: var(--card)`. So on Kitchen Table's Home, Vera's box becomes a card with ink words and the look's primary for Send, not dark glass. Her screen beside it stays glass. Kitchen Table keeps its dark green box. The family decided to keep it so: in a paper look her box is a plain card, and her screen beside it is still glass.
  - Rail's current page in the panel is its yellow plate (`--here`), as Rail's sheet draws it.
  - Phosphor and Midnight keep their own band and current item.
- **What would have broken, and is handled:** the panel's links (`--band-link`), Vera's pill (`--vera-soft`, worked out per look), her box's words, rules and fills, the meaning washes and the late plate. Without the `[data-theme]` block, every look would have shown Kitchen Table's cream-paper values through. With it, each works them out from its own tokens.

### 8.3 The Look page, in Kitchen Table

`look.html` here is the built `look.html` in Kitchen Table's components. `look-kid.html` is the same page for Maya, just after she chose Fjord.
- **The same form**: "Day and night" (Match my device / Always day / Always night, with the built words), every look as a card with a radio, its name, "In use", its blurb and its samples (Day and Night, or "Night only" for Phosphor), and "Use this look".
  - Kitchen Table adds "The default" tag, and a quiet line by Save: "Yours alone, on every device you use."
  - Its lede says the look is kept with your name and follows you (§8.5).
- **The samples keep the built markup** (`span.look-shot > span.look-sample[data-theme][data-mode] > .ls-band, .ls-page …`), because `test_look.py` counts them: one Phosphor sample, two for each other look.
  - They are drawn in Kitchen Table's components: a panel with the mark and the current item, a card with a title, a line, "Today" and the button, and a row of dots (three people, Vera, amber and red).
  - Each reads the look's own tokens, so a sample can't drift from its look.
- **Where it sits:**
  - the account corner reads **Look · Your password · Sign out** on every page;
  - the phone menu has a **Look** row ("Yours, on every phone and computer you sign in on"; a kid's "…you use").
  - The stage-9 pickers are gone from Settings › General and from "You", which is "Your password" again, as in the app.
- **The flash**: "Saved. You'll see Fjord on every phone and computer you sign in on." The built "Saved. This browser wears Fjord from now on." stays only while the family shares one password.

### 8.4 What each built look adds for Kitchen Table's layout

`_kit/looks-check.py` runs every look through:
- `test_look.py`'s floors;
- the pairs Kitchen Table's layout draws that the old one doesn't: the panel's links and current item, Vera's box, Send, her fills and pill, the late plate, each meaning on its wash, each person's name, letter and mark;
- the effects (8.7).
People are not checked against each other under simulated colour blindness: the family decided against that floor in stage 13, since a name or initial is always beside a colour.

Results:

| Look | Result | Needs |
|---|---|---|
| Kitchen Table | passes every floor | nothing |
| Phosphor | passes (night only) | `--here-icon`, `--here-pill` (added) |
| Afterglow (stages 12 and 14, 8.8) | passes every floor (night only, one fixed look), with its scanlines and page light composited (check D); wears Kitchen Table's people, so has the same recorded shortfalls | nothing: it is written for this layout |
| Rail yellow, Fjord, Ink, Midnight | pass | nothing: the derived roles work out from their own tokens |
| Enamel | words on Vera's green fill are 4.48:1 by day with its `--on-bright` | `--on-vera: light-dark(#FFFFFF, #161513)` (4.72:1) |
| Home Computer | the same, 4.33:1 | `--on-vera: light-dark(#FFFFFF, #171513)`. Its night red stays as built (the family's decision) |

The two additions sit after the looks in this folder's `themes.css`. **In the built file they go inside each look's own block**, because `test_look.py` reads one block per look. Palette sheets for every look: `palette/<look>.html` (`python3 _kit/looks-check.py --sheets`). Shots of Kitchen Table's, Rail's and Midnight's sheets are in `shots/looks/`.

### 8.5 A person's look follows them

The family's decision: **each person chooses their own look, and it follows them on every device.** So the choice (the look and its day/night mode) is kept with the member, not only in the browser.
- **Stored:** `members.look TEXT` (NULL: none chosen), in migration `0037` (§1). It holds exactly what the cookie holds (`"rail.dark"`, `looks.value(look, mode)`) and is read with `looks.parse()`, so a stored value that names no look is the default, as a bad cookie is.
- **Written through the rules:** the Look page's POST calls `familydb.family.choose_look(conn, member_id, value)`, the door every member change already goes through. It checks the value with `looks.choose()` and writes through `store.members.set_look`. It is for whoever is signed in, kids included, and only ever for themselves: no one sets another person's look. The web AST test gains the line that `web/looks.py` may call `familydb.family.choose_look` (§7, 22).
- **Read:** `base.html` wears the signed-in member's look. With no member (the sign-in page, a refusal before signing in) it wears the cookie's. With neither, Kitchen Table, following the device.
- **The cookie stays, for the pages before anyone signs in.** It is set:
  - from the member's look when they sign in, so signing in on a new phone brings their look with it, and the sign-in page there wears it next time;
  - again whenever they choose on the Look page.
  - Signing out leaves it, so the sign-in page keeps the last person's look.
- **While the family shares one password**, nobody in particular is signed in, so the Look page keeps the choice in this browser only, as built. Its words say "this browser" in that state only.
- **No household default** is needed now: each person picks, and it's Kitchen Table until they do.
- **The Look page's words** (`look.html`, `look-kid.html`):
  - the lede: "How the page looks for you. It is kept with your name, so it comes with you to every phone and computer you sign in on, and everybody else keeps their own.";
  - by Save: "Yours alone, on every device you use.";
  - the flash: "Saved. You'll see Fjord on every phone and computer you sign in on.";
  - "Match my device": "…as each phone or computer does."
  - The menu's Look row: "Yours, on every phone and computer you sign in on" (a kid's: "…you use").
- **Still not built: a colour for each family member** (the built STYLE.md's other "not yet"):
  - Kitchen Table's layout already draws it (`.p0`–`.p8`, avatars, bubbles, calendar events);
  - it needs a `members.slot` column (§1, item 1);
  - a look may give its own eight (`--p1`… in its block) or take Kitchen Table's.

### 8.6 Adding a look, step by step (unchanged from the built STYLE.md, plus one check)

1. Write a block in `static/themes.css`: `[data-theme="<key>"] { color-scheme: light dark; … }`.
   - It names every token the others name, each as `light-dark(day, night)`.
   - The 66 Kitchen Table roles are optional: name one only to set it apart from the derived value.
2. Add a line to `web/looks.py`: the key, name, blurb, `has_day`, and the band's two colours.
3. Run `pytest tests/test_look.py` and `python3 _kit/looks-check.py --sheets`, then open `palette/<key>.html`.
4. Open the Look page and Home in it, by day and by night. Nothing else changes: no template, no `style.css`.
5. If the look wants effects, it names its `--fx-*` values (8.7); `looks-check.py` then measures its words with them on.

### 8.7 Effect tokens: what a look may add beyond colour (stage 12)

Some feels can't be carried by colour alone: scanlines, a glow, a lit edge, a terminal face for a title. These are now part of the look contract, as **five effect tokens**. Every look defines them, and `style.css` reads them once, in its section 11 ("Effects").

| Token | What it is | Plain value (every look, from the `[data-theme]` block) | Afterglow |
|---|---|---|---|
| `--fx-page` | a light on the page itself, behind everything (`body`'s background image) | `none` | a faint green afterglow at the top left |
| `--fx-scan` | the colour of the scanlines on the band and on Vera's glass (the Ask box, the radar's pane) | `transparent` | `rgb(190 255 215 / .035)`, one line in three |
| `--fx-glow` | how much Vera's things glow beyond their plain look, 0 to 1; also how bright the small motions are (8.10), never how long | `0` | `1` |
| `--fx-title` | the face of page titles (`h1`) and the wordmark | `var(--font-head)` | `"VT323", var(--font-head)` |
| `--fx-title-adjust` | that face's `font-size-adjust`, so a pixel face stands as tall as the heading face's capitals | `none` | `cap-height .7` |

**The rules they keep**, held in `style.css` and measured by `_kit/looks-check.py`:
- **Never over the words.**
  - Scanlines are a `background-image` under the text, on the band, Vera's Ask box and the radar's pane, never on cards or fields.
  - The fixed glass panes (sign-in, first day, 404) drew their scanlines as a film over everything (`.pane::after`). They now draw them under the words too, in every look; the panes look the same.
  - Glow is a shadow outside a thing's edge.
- **Measured with the effect on.** `looks-check.py` (check D) composites the scanline over the band and over Vera's box, and the page light at its strongest over the paper. It then measures the words drawn there: the panel's words and links, Vera's words, and every text colour on the page. Afterglow's lowest over an effect is 6.94:1 (the quietest words under the page light; the floor is 4.5).
- **Off when they should be.** Under `forced-colors` and in print, every effect background goes and the sign's halo is dropped. Under `prefers-reduced-motion`: none of the effects move, so nothing changes; the motions (8.10) all stop.
- **CSS only.** No images, no scripts, nothing inline. The one font, VT323 (`fonts/vt323-400.woff2`, OFL, 18 KB), is self-hosted. It is fetched only by a look that names it.
- **Vera stays the one lit thing.** With `--fx-glow: 1`:
  - her sign gains a second, wider halo and a fully lit rim;
  - her Send glows;
  - her lines in the chat have a soft lit edge.
  - Nothing of the family's glows: links are a soft mint, their button a pale plate, today a flat chip.
  - So in a look that is all glass, she is still the brightest thing on the page.

### 8.8 Phosphor, Afterglow and Kitchen Table

The family's words: "Phosphor is a design system; Afterglow is one derivative of it." So the three names mean three things, and nothing is renamed:
- **Phosphor is the design language**: the green-screen family FamilyDB was first drawn in. It means charcoal glass, phosphor green for what is live or Vera's, scanlines, a terminal's cursor, and type and light that recall the old screens.
- **Looks drawn from it:**
  - **The Phosphor look** (`phosphor`): the built app's original palette. It stays on the Look page as it is, and recolours Kitchen Table's layout fine (`shots/looks/`, stage 11).
  - **Afterglow** (`afterglow`): a second look from the same language, made for Kitchen Table's layout, with its effects.
- **Kitchen Table is the layout, and the default look.** Both the Phosphor look and Afterglow sit on it. Vera's glass and phosphor, her screen and the mark are the Phosphor language's too, which is why they look the same in every look.

**Afterglow** is `[data-theme="afterglow"]` in `themes.css`: the earlier Afterglow round (`afterglow-ref/`) brought into the look mechanism as a palette and the five effects. It changes no template, no markup and no words.
- **One fixed look**, as the family decided: no day and no night version, the same whatever the device or the Look page's "Day and night" says.
  - Its block gives one value per token (no `light-dark()`) and `color-scheme: dark`.
  - The two `data-mode` rules skip it, as they skip Phosphor.
  - `has_day` is `False` in `looks.py`, so `looks.parse()` and `choose()` keep its mode at `auto`, as they do for Phosphor.
- **On the Look page** it shows a single sample captioned "Night only", as Phosphor does. The built page's line under "Day and night" now names both: "Phosphor and Afterglow are green screens, so they have no day: they are always night, whatever is chosen here."
- **What it looks like:**
  - charcoal glass with a breath of green for the page, lighter glass cards;
  - a darker glass band, with faint scanlines on it and on Vera's box;
  - Vera the one lit thing (8.7);
  - the family's links a soft mint, their button a pale plate.
- **Type** (decided: titles and the wordmark only):
  - Atkinson Hyperlegible stays for everything read.
  - VT323 sets the page titles (42 px Fraunces becomes VT323 at the same cap height, about 52 px) and the wordmark. The smallest title in the face is sign-in's, at about 29 px.
  - Home's question "What's on your mind?" is an `h1` but a sentence, so it keeps the heading face.
  - Card titles stay Fraunces, and money and dates keep Fraunces Figures (one figure style).
  - Why: the pixel face carries the screen's character where a few big words stand alone. Anywhere it is read in quantity (card titles, figures in a row, sentences) it slows reading. And none of the family's big numbers should look different from Kitchen Table's.
- **People.** It wears Kitchen Table's eight, and is checked on them (names, letters and marks against every ground).
- **Its line in `looks.py`:**
  ```python
  Look("afterglow", "Afterglow",
       "From the Phosphor family of green screens: Kitchen Table as charcoal glass with faint scanlines, and Vera the one thing that glows. Always night.",
       False, ("#060A08", "#060A08")),
  ```
- **Rendered:** every page, desktop and phone, in `shots/afterglow/`, from `afterglow-test/`. There is one set, because it looks the same in any mode. Its palette sheet is `palette/afterglow.html` (one column; shot: `shots/afterglow/palette-afterglow.png`).

### 8.9 What the built `themes.css`, `style.css` and `test_look.py` need for effects and Afterglow

- **`themes.css`:**
  - The five `--fx-*` tokens with their plain values go in the `[data-theme]` block of derived roles (as here). In the built file, where `test_look.py` reads one block per look and checks that every look names the same tokens, each look's own block names them instead: five lines each, all plain except Afterglow's.
  - The Kitchen Table block already names them (plain).
  - Afterglow's block goes in as it is here.
- **`style.css`:**
  - Section 11 "Effects" (about 25 lines) and the VT323 `@font-face`.
  - The `.pane` scanlines change from `::after` to a background.
  - On today's layout the effects aren't read, so Afterglow there is its colours only. It should land with the new layout (§6, step 2), not before.
- **`test_look.py`** gains:
  - **every look names the five effect tokens**;
  - **an effect token is one of its allowed forms**:
    - `--fx-page` is `none` or a gradient whose colours are `rgb(… / a)` with `a` ≤ 0.1;
    - `--fx-scan` is `transparent` or `rgb(… / a)` with `a` ≤ 0.06;
    - `--fx-glow` is a number from 0 to 1;
    - `--fx-title` ends in `var(--font-head)` and names only self-hosted faces;
    - `--fx-title-adjust` is `none` or `cap-height` with a number. So nothing else can be smuggled in (no `url()`, no images).
  - **`themes.css` holds only tokens** still holds, since the effects are custom properties.
  - **the contrast floors with the effects composited**: check D of `looks-check.py`, ported (about 20 lines);
  - **Afterglow's band matches `looks.py`** (`#060A08`), and, like Phosphor, it has no day: no `light-dark()` in its block, and `"color-scheme: light dark"` is not expected of it.
  - A CSS test for the motions (8.10): every `animation` outside a `prefers-reduced-motion: no-preference` block is listed in the `reduce` block.

### 8.10 The small things that move (every look)

The old screen's motions, kept small and brought into Kitchen Table itself, in every look. `style.css` section 12; `motion.html` shows each in place, with when it plays; `shots/motion-frames.png` shows the sign's typing frame by frame.

| Motion | When it plays | How long | Markup |
|---|---|---|---|
| **Her sign types in** | once, on Home, as the page opens (the Ask box's sign) | its lines type in from the left in about 1.5 s; its cursor blinks three times and rests lit by 4.8 s | `vera_screen(..., state='hello')` → `.vs--hello` |
| **Her sign types while she writes back** | from the moment a message is sent until her answer lands: the chat's waiting line, and Home's Ask box while the health pill reads "writing back" | loops every 2.4 s (types, holds, clears together), cursor blinking; stops when she answers | `state='busy'` → `.vs--busy`, from the same health state as the pill (`status.pill`) |
| **Afterglow** | when a page comes back after a save, a tick or an answer: the flash with its Undo | lights at once, fades over 1.2 s | `.flash` (as today) |
| **Landing** | when a link opens a page on a card, a day or a plan (`#rate`, `#d-2026-10-04`, `#levels`…) | lights and fades over 1.8 s | `:target` (nothing new) |
| **Cursors rest** | the wordmark's cursor, as any page opens | four blinks, about 4 s, then lit | as today |
| **The dot breathes** | the health pill, only while she is writing back | loops while busy | as today |

- **Left behind, decided** (§9): glyphs falling on every busy screen, the 404 powering on, the radar's sweep, the flicker, the lamp breathing while idle. They would move where nothing is happening.
- **The rules:**
  - nothing moves for more than a moment where people read;
  - nothing loops except while she is working;
  - everything is CSS (the scripts animate nothing);
  - under `prefers-reduced-motion` nothing moves at all: the new motions exist only inside `@media (prefers-reduced-motion: no-preference)`, and each old one is stopped in the `reduce` block.
- In Afterglow the afterglow and landing lights are brighter (`--fx-glow` raises them from 45 % to 80 %), and the sign's halo is wider. Each lasts exactly as long as in every other look.
- **Never a face, never words.** The sign's lines are bars: they type as bars, of fixed lengths, and spell nothing.
- **For tests:** the screenshots (`_kit/render-all.js`) now ask Playwright for `animations: "disabled"`, which shows every motion at rest. Any visual test should do the same.

---

## 9. Open questions for the family

None. The family answered the first round in stage 13, and the last five in stage 14:
- **Afterglow and Phosphor:** Phosphor is the design language, and Afterglow is one look drawn from it, under its own name; the Phosphor look stays as it is (§8.8).
- **Afterglow by day:** none. It is one fixed look (§8.8).
- **These three were left to the designer:**
  - **A parent opening Settings, setup or the family list gets the friendly page**, not the plain refusal (`admin-only.html`). Reason: it is the same kind page a kid gets, in the app's own words for an admin's part ("For an admin" / REFUSALS["manage"]), and it names who to ask ("Sam is the admin in this family"), which the plain refusal can't. It offers Home and Status, which a parent can open (§1).
  - **Afterglow's pixel face: titles and the wordmark only.** Reason: it gives the screen its character where a few big words stand alone, and would slow reading anywhere it is read in quantity (§8.8).
  - **The motions: keep the five, bring back none** (§8.10). Reason: each plays where it means something and ends on its own. Glyphs falling on every busy screen, the 404 powering on and the radar's sweep would move where nothing is happening, which a calm kitchen-table page shouldn't.
