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
| `_kit/looks-check.py` | additions to `tests/test_look.py` | the built floors plus Kitchen Table's layout pairs and the colour-blind checks, for every look; palette sheets |
| `STYLE-draft.md` | `docs/STYLE.md` | the design notes, as they will stand once built |
| `STANDARD.md` | (reference) | every component, token, rule and check, with class names |
| `CHANGES.md` | (reference) | why each thing is the way it is, stage by stage |
| `*.html` (59 pages), `looks-test/*.html`, `palette/*.html` | (reference) | the mockups; Home and a kid's Home in Rail yellow, Midnight and Phosphor; a palette sheet per look |
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
| `todo-edit.html` | `tasks.html` (its inline edit fold) | none today | N: add `GET /task/<id>/edit` → `task_form.html`, or keep the edit as a fold on the row |
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
| `404.html` | `404.html` | `abort(404)` | R |
| `more.html`, `more-kid.html` | `base.html`'s `details.menu` | none today | N: `GET /more` → `more.html`, the phone account page |
| `settings.html` | `settings.html` | `/settings` → `settings.show` (`overview()`) | R |
| `settings-<name>.html` (9) | `settings_section.html` + `settings/<name>.html` | `/settings/<name>` → `settings.section` / `settings.personality` (`page()`, `PAGES[name]`) | R |
| `setup.html` | `setup.html` | `/setup` → `setup.overview` | R |
| `setup-<step>.html` (7) | `setup_step.html` + `setup/<step>.html` | `/setup/<step>` → `setup.step` (`PAGES[step]`) | R |
| `setup-telegram-link.html` | `setup/telegram.html`, stage `link` | the same | S |
| `setup-told.html` | `setup/model.html` + `setup_told.html` | the model step after a refused key | S |
| `setup-done.html` | `setup_done.html` | `/setup/done` → `setup.done` | R |
| `states.html`, `states-actions.html`, `states-content.html`, `type.html` | none | none | D |

**Replaced, merged, new.** Every page template is replaced in place; none is merged away. The partials become macros (section 2):
- `_ask.html` becomes a `composer()` macro.
- `setup_told.html` becomes `told()`.
- `_company_cards.html` and `_key_steps.html` stay includes, with new markup.
- `own_password_form.html` and `password_form.html` stay.

New templates:
- `more.html` (the phone account page);
- `task_form.html`, if to-dos get an edit page.

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
2. **Looks and light/dark** (`data-theme`, `data-mode` on `<html>`): **built** (`web/looks.py`, the `fdb_look` cookie, `/look`). Kitchen Table adds one look and 66 token roles (§8).
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
9. **"Hidden from Maya"** on a present. Gifts are hidden from every kid today, and no single person is named.
   - Change: render "Hidden from" with the kids' names from `_kids(conn)`. That is true today and needs no schema.
   - Naming exactly one person needs `ideas.hidden_from`. That is a family question (see the open questions).
10. **"Set by Alex"** on a kid's to-do. Tasks don't record who made them.
    - Change: migration `tasks.created_by_member_id`, set in `edits.add_task` and in the chat tool. Without it, drop the line.
11. **"N days late", "Was due Sun 27 Sep"**: `views.late_words(due, today)`, used by both `task_row` and `task_brief`.
12. **A kid's messages left today** ("5 messages left today"). `calls.answered_for` exists, but only Family uses it.
    - Change: compute `left` in `chat.page`, and in `home()` when `roles.daily_limited`.
13. **"Earlier messages"** (`?before=<id>`): add `before` to `message_store.last_for_chat` and to `chat.show`.
14. **Faces on "How did it go?"**: map Loved it / OK / Not great to ratings 9 / 6 / 3 in `edits.record_outcome`. Use the same query as item 4.
15. **Names on the Ideas radar's dots**: add `title` / `short` to each blip in `views.places_radar`.
16. **Status's "How each part is doing"**: `status.health(app, conn) -> [(area, state, words, action)]`. The pill (3) and the settings flags (4) read the same function, so they can't disagree.
17. **Home's "Vera today" card**: pass `spent_today` and the limit to `home()` for grown-ups. "A usual day" is the 30-day total divided by the days that had calls.

No body class for roles is needed: the shell decides each nav item with `visitor().may(...)`, as it does today.

---

## 2. Components → macros

The class names in STANDARD.md §2 are the API, and each component becomes one macro. Existing macro names are kept where the job is the same.

### Changed macros (`_ui.html`)

| Today | Becomes | Parameters | Emits |
|---|---|---|---|
| `icon(name, label=none, cls='')` | `icon(name, label=none, cls='', size='')` | `size='sm'\|'lg'` by keyword | `svg.icon[.icon--sm]`. **The sprite's names change**: `bulb`, `cal`, `chev`, `chevl`, `sliders`, `pulse`, `todo`, `memory` replace `idea`, `plans`, `right`, `settings`, `status`. Add a `mic` symbol for `dictate.js` |
| `presence(cls, variant)` | `vera_screen(size='', state='')` | size `sm`/``/`lg`/`xl`; state `busy`/`off` | `svg.vs` from the geometry table in STANDARD.md §9 |
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
- Nothing blinks for more than five seconds. The wordmark cursor blinks twice: its `animation` had a typo (`2te`) that stopped it altogether, and that is fixed. `prefers-reduced-motion` stops everything.
- `forced-colors` gives every selected state a real border.
- No sideways scrolling at 320 px or 200 % zoom.
- `_kit/looks-check.py` measures the colour pairs for every look, on Kitchen Table's layout as well as the built pages'.

**Kids**:
- Kids never see costs, models or workings: no health pill, no Status, no money, no setup, no "used …" lines.
- A kid's footer has no version number.
- Kids see only their own chat and their own to-dos.
- A page their role can't reach shows a kind refusal in the real words.

**Presents**:
- Presents stay hidden from kids: no row, no count, no greyed item.
- Grown-ups see them tagged "Surprise · hidden from …".
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
- Nav: "{assistant}" / "Chat" → "Chat with Vera" (tab bar: "Chat"); "Memory" → "What Vera knows"; a "Behind the scenes" group for Status, Settings, Family.
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
- Look: the built page's words throughout (`look.html`, `looks.MODE_WORDS`, the looks' blurbs, "Saved. This browser wears … from now on."). New: Kitchen Table's blurb, "The family's table: cream paper, deep green, and each person in their own colour."; the tag "The default"; the line by Save, "Only this browser changes: everybody else keeps their own." (a kid's: "Only this screen changes. Nobody else sees it."); the phone menu's row "How the page looks on this phone or computer".
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
   - Test: the files serve; `python3 _kit/looks-check.py` passes (Home Computer's known finding aside, §9).
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
   - the month calendar (`month_weeks` lanes) and the list;
   - who a plan is for.
   - Test: tick with scripts off; `aria-current="date"`; "Move it" still in a `details`.
7. **Ideas, an idea, the idea form, Restaurants**: `idea_card`, `kind_label`, the radar with names.
   - Test: search and filters (GET); a gift hidden from a kid; the form's errors.
8. **Wishes and What Vera knows**: `wish_card` with the `wishes.js` hooks, the three lists, answers.
   - Test: move up/down with scripts off; drag with `wishes.js`; answer a wish.
9. **Family, member, Your password, Look**:
   - starting passwords shown once;
   - you-first;
   - the Look page in Kitchen Table (`look.html`: the built form, the new markup, the samples kept as `look-sample`).
   - Test: the password flows; `test_look.py` on the new markup.
10. **Settings**: `setting`, `group`, `save_bar`, `told`, `settings_nav`, every section page.
    - Test: save, an emptied box returns to its default, a complaint opens its fold, only an admin sees it.
11. **Setup**: the overview, the steps, done, told.
    - Test: each step's form posts and comes back with what it said; Telegram's refresh.
12. **Status and activity, 403, 404, sign-in.** `status.health` and `status.verdict`.
    - Test: Status is grown-ups only (see the open questions); the refusal pages.
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
7. **Vera's glyph**: `span.presence.v0`–`v3 > .presence-glass` → `svg.vs` (`.vs--busy`, `.vs--off`).
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
      - `test_every_look_keeps_the_contrast_floors_by_day_and_by_night` passes for Kitchen Table as it is. Add Kitchen Table's layout pairs (the panel's links and current item, Vera's box and Send, words on Vera's fill, the late plate, each meaning on its wash, each person's name, letter and mark) and the colour-blind checks from `_kit/looks-check.py`.
    - **When Kitchen Table becomes the default** (§8.2):
      - `test_the_page_is_phosphor_and_follows_the_device_until_somebody_chooses` becomes "…is Kitchen Table…": `("kitchen", None)`, `content="light dark"`, and `#EFE7D7` by day, `#121816` by night.
      - `test_phosphor_has_no_day_to_choose` stays.
      - `test_nothing_but_a_look_this_page_has_is_kept`, `test_a_cookie_that_names_no_look_is_the_default` and `test_a_form_from_another_site_does_not_change_the_look` expect `("kitchen", None)`.
      - In `test_every_look_is_written_down_once…`, Phosphor is now a block in `themes.css`, so `set(blocks) == {looks other than the default}` holds with Kitchen Table out and Phosphor in. But `assert one.has_day` must skip Phosphor, as must `"color-scheme: light dark" in blocks[...]`, and the check that the default sits in `style.css` reads `[data-theme="kitchen"]`.
      - `test_the_look_page_offers_every_look_in_its_own_colours` still passes: the samples keep `class="look-sample" data-theme="…"`.

Unaffected: `test_browsing_asks_nothing_of_a_model`. "Every name in BEHAVIOUR appears exactly once" is unaffected too: the look is a cookie, not a setting.

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
- **The choice is a cookie per browser**, `fdb_look` ("rail.dark").
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

**Should Kitchen Table replace Phosphor as the default? Yes, when the new layout ships, and not before.** Kitchen Table is the design the family chose, and its layout is built around a light page. Phosphor's layout is the one being replaced.

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
- **A browser that chose Phosphor keeps it** (its cookie still says `phosphor.auto`). Every other browser changes to Kitchen Table at once, so tell the family in the release note. The Look page is one tap from the menu.

**The other looks under Kitchen Table's layout.** They recolour any layout, and they still read on Kitchen Table's shapes.
- **Rendered:** Home and a kid's Home in Rail yellow, Midnight and Phosphor, day and night, desktop and phone, in `shots/looks/` (pages in `looks-test/`).
- **Rendered too:** Maya's Look page (`look-kid.html`) is worn in Fjord, so it is a whole page of Kitchen Table's layout in a built look.
- **What changes, by design:**
  - The paper looks (Rail, Ink, Enamel, Fjord, Home Computer) set `--ask-bg: var(--card)`. So on Kitchen Table's Home, Vera's box becomes a card with ink words and the look's primary for Send, not dark glass. Her screen beside it stays glass. Kitchen Table keeps its dark green box. See §9, question 1.
  - Rail's current page in the panel is its yellow plate (`--here`), as Rail's sheet draws it.
  - Phosphor and Midnight keep their own band and current item.
- **What would have broken, and is handled:** the panel's links (`--band-link`), Vera's pill (`--vera-soft`, worked out per look), her box's words, rules and fills, the meaning washes and the late plate. Without the `[data-theme]` block, every look would have shown Kitchen Table's cream-paper values through. With it, each works them out from its own tokens.

### 8.3 The Look page, in Kitchen Table

`look.html` here is the built `look.html` in Kitchen Table's components. `look-kid.html` is the same page for Maya, just after she chose Fjord.
- **The same form**: "Day and night" (Match my device / Always day / Always night, with the built words), every look as a card with a radio, its name, "In use", its blurb and its samples (Day and Night, or "Night only" for Phosphor), and "Use this look".
  - Kitchen Table adds "The default" tag, and a quiet line by Save: "Only this browser changes: everybody else keeps their own." (a kid's: "Only this screen changes. Nobody else sees it.").
- **The samples keep the built markup** (`span.look-shot > span.look-sample[data-theme][data-mode] > .ls-band, .ls-page …`), because `test_look.py` counts them: one Phosphor sample, two for each other look.
  - They are drawn in Kitchen Table's components: a panel with the mark and the current item, a card with a title, a line, "Today" and the button, and a row of dots (three people, Vera, amber and red).
  - Each reads the look's own tokens, so a sample can't drift from its look.
- **Where it sits:**
  - the account corner reads **Look · Your password · Sign out** on every page;
  - the phone menu has a **Look** row ("How the page looks on this phone or computer"; a kid's "How your screen looks").
  - The stage-9 pickers are gone from Settings › General and from "You", which is "Your password" again, as in the app.
- **The flash** is the built one: "Saved. This browser wears Fjord from now on."

### 8.4 What each built look adds for Kitchen Table's layout

`_kit/looks-check.py` runs every look through:
- `test_look.py`'s floors;
- the pairs Kitchen Table's layout draws that the old one doesn't: the panel's links and current item, Vera's box, Send, her fills and pill, the late plate, each meaning on its wash;
- the colour-blind checks.

Results:

| Look | Result | Needs |
|---|---|---|
| Kitchen Table | passes every floor; its eight people's three colour-blind shortfalls recorded as known (§9, question 2) | nothing |
| Phosphor | passes (night only) | `--here-icon`, `--here-pill` (added) |
| Rail yellow, Fjord, Ink, Midnight | pass | nothing: the derived roles work out from their own tokens |
| Enamel | words on Vera's green fill are 4.48:1 by day with its `--on-bright` | `--on-vera: light-dark(#FFFFFF, #161513)` (4.72:1) |
| Home Computer | the same, 4.33:1 | `--on-vera: light-dark(#FFFFFF, #171513)`; and see §9, question 3 |

The two additions sit after the looks in this folder's `themes.css`. **In the built file they go inside each look's own block**, because `test_look.py` reads one block per look. Palette sheets for every look: `palette/<look>.html` (`python3 _kit/looks-check.py --sheets`). Shots of Kitchen Table's, Rail's and Midnight's sheets are in `shots/looks/`.

### 8.5 Later steps: the household default and a person's own look

The stage-9 design drew two things for a choice kept on the server. They are **not built, and not for this release**. What each would need, when the family wants it:
- **A household default look** (an admin chooses the look for every browser that hasn't chosen):
  - one setting in `store.settings.BEHAVIOUR` and `web/fields.py` (`look`, default `kitchen`, choices from `looks.LOOKS`);
  - a "How it looks" group on Settings › General, drawn with the Look page's cards;
  - `looks.parse()` falls back to it instead of `DEFAULT` when there is no cookie.
  - The cookie still wins, so a browser's own choice is never overridden.
- **A person's own look, following them across devices**:
  - a `members.look TEXT` column (NULL: none), one migration;
  - the Look page saves it as well as the cookie when a member is signed in;
  - base.html prefers the cookie, then the member's look, then the household's.
  - Kids may set their own, as they can now.
- **A colour for each family member** (the built STYLE.md's other "not yet"):
  - Kitchen Table's layout already draws it (`.p0`–`.p8`, avatars, bubbles, calendar events);
  - it needs a `members.slot` column (1, section 1);
  - a look may give its own eight (`--p1`… in its block) or take Kitchen Table's.

Keep all three behind the family's say. Each is one setting or one column and a few lines, and none changes the Look page's form.

### 8.6 Adding a look, step by step (unchanged from the built STYLE.md, plus one check)

1. Write a block in `static/themes.css`: `[data-theme="<key>"] { color-scheme: light dark; … }`.
   - It names every token the others name, each as `light-dark(day, night)`.
   - The 66 Kitchen Table roles are optional: name one only to set it apart from the derived value.
2. Add a line to `web/looks.py`: the key, name, blurb, `has_day`, and the band's two colours.
3. Run `pytest tests/test_look.py` and `python3 _kit/looks-check.py --sheets`, then open `palette/<key>.html`.
4. Open the Look page and Home in it, by day and by night. Nothing else changes: no template, no `style.css`.

---

## 9. Open questions for the family

1. **Vera's box in the paper looks.** Kitchen Table draws her Ask box as dark green glass. The built paper looks (Rail yellow, Ink, Enamel, Fjord, Home Computer) make it a plain card with ink words, so in those looks it's no longer the one dark thing on the page; her screen beside it stays glass. Keep it as the looks have it, or ask each paper look for a dark `--ask-bg` of its own?
2. **Kitchen Table's people under colour blindness.**
   - Its eight people fall under the floor in three places: slot 4's ochre and slot 7's olive look the same to a protanope, slots 2 and 5 are close for a deuteranope, and late red sits next to slot 4's ochre for a deuteranope.
   - Names and initials are always beside the colours, so nothing becomes unreadable, but the calendar's dots are harder.
   - Every look shows these eight people until it has its own, so this now matters in all of them. Retune slots 4, 5 and 7, or keep the recorded exception?
3. **Home Computer's red and orange.** At night, for tritanopes, its late red is 4.9 apart from its orange action colour (the floor is 6). This is a built look, and the built tests don't check colour blindness. Adjust its night red, or accept it?
4. **Kitchen Table as the default.** Recommended once the new layout ships: until then it can be one more look. Every browser that hasn't chosen Phosphor then changes to Kitchen Table at once. Is that what the family wants, with a line in the release note?
5. **A household default look, and a person's own look across devices** (§8.5). Neither is built. Wanted, and when?
6. **Status for parents.** The design puts Status under "Behind the scenes" with Settings and Family. The app shows Status to parents too (`browse`). Keep Status for every grown-up, or make it admin-only?
7. **"Hidden from Maya."** Presents are hidden from every kid today. Should a present name exactly whom it's hidden from (one more column), or keep "hidden from the kids"?
8. **Who sees the "for grown-ups" page.** A kid opening Settings gets the friendly page naming the admins. Should a parent who isn't an admin get the same page, or the plain "For an admin" refusal?
9. **To-dos' edit page.** The design gives a to-do its own Edit page. The app edits in a fold on the row. Add the page, or keep the fold?
10. **"Set by Alex."** Showing who set a kid's to-do needs the app to remember it, from now on. Worth it?
11. **"Installer".** Setup's "Still the password the installer made up." is the app's wording; an earlier round wanted "installer" gone. Keep it, or say "the password FamilyDB started with"?
