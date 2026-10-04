# FamilyDB final design: design-system review

Lens: are the seven pages really one system? I read `style.css` (887 lines), `STANDARD.md`, and checked all 20 HTML pages against the stylesheet with a script. I looked at every overview and opened the full-length Plans, Wishes, My to-dos (kid) and Add an idea pages.

## Verdict

**7/10.** The system is real, not accidental. All colours are tokens on `:root` with a full dark remap, every component is documented with a class API, the 20 pages contain no `style=""` at all, and only two classes used in the HTML (`todo--ro`, `span-all`) are missing from the stylesheet. But the system is keyed to the mockup family's names and to this one month's calendar, and several modifiers are being reused for meanings they weren't named for. Those are the places that will break first when real data and the other pages arrive.

**Optimise before building?** Yes. The fixes are cheap now and expensive once they've been copied into 20+ Jinja macros, and two of them (person colours keyed to names, the `.span2` clash) break with the first real family or the first two-day plan.

## Protect

1. **Token layer and dark mode** (`style.css` §2): one set of names redefined under `prefers-color-scheme: dark`. The dark overview shows all seven pages turning over with no one-off overrides.
2. **Banner: one component, four tones, two sizes** (Status hero, Settings "1 thing needs a look", Plans "Google Calendar: not connected", Ideas "Looking things up is off"), with a written tone rule that the pages follow.
3. **Health vocabulary**: the same tags (Working · Could be better · Needs a look · Off) on Status "How each part is doing", the Settings rows, and the Settings "Reading this list" key, all fed by one `health(area)` macro.
4. **Date tile `.dt`**: identical on Home "Next up", Plans "Coming up", the idea page's "On the calendar" card and the kid's Home, with `--now` for the next plan.
5. **To-do row with the 4 px red late rule**: the same anatomy on To do (full) and Home (`--compact`), and the late rule always comes with "6 days late" in words.
6. **One composer** (`.composer`): the same component on the Home Ask card (dark green, sun Send), Chat, the kid's chat and the sign-in sample, with closed states drawn on the states sheet.

## Fix, ranked

**1. Person colours are keyed to the mockup family's names** (every page: `.av--sam`, `.msg--maya`, `.ev--theo`, `.dots i.d-maya`, tokens `--sam…--theo`)
- Problem: the standard says a real install gives each person "the next colour from a fixed set of eight", but the stylesheet only has five named sets, and the classes are named after people. A family with an "Ana" has no class. The calendar's phone dots only have a colour for Maya (`d-maya`), so the other people's dots are grey (Plans phone: the Oaks Park dot). Nothing in the system builds for real data.
- Fix: define `--p1…--p8` (each with `-soft`, `-ink` and a dark variant) and a slot class `.p1…p8` that sets local `--p`, `--p-soft` and `--p-ink`. Then `.av`, `.msg`, `.ev` and `.dots i` read those variables. Keep Everyone as `.p0`. Store the slot on the person record.
- Severity: blocker. Effort: S.

**2. `.span2` means two different things** (Status/sign-in layout vs Plans calendar events)
- Problem: `.span2 { grid-column: 1 / -1 }` (line 665) comes after `.c1…c7` (line 633) and has the same specificity. Only `.c6.span2` is protected, so a two-day plan starting Mon–Fri stretches across the whole week. There's also no class for a plan that crosses a week boundary or runs 3+ days. The Cannon Beach weekend only works because it starts on a Saturday.
- Fix: rename the layout helper to `.span-all` (already used once in states-actions, but undefined). Give events `.len2…len7` that set `grid-column-end: span N`, and split events that cross a week into one bar per week, with an "↳ continues" label.
- Severity: blocker. Effort: S.

**3. State-tag modifiers are reused for unrelated meanings** (Wishes, kid Home, Plans "Coming up", Home "Next up")
- Problem: `.tag--off` is defined as "Off/Optional/No backup", but it also draws "Thinking about it", "Not decided yet", "Leave by 12:30 pm" and the idea kinds on Plans (Activity, Day trip, Show, Trip). On the kid's Home and My wishes, "Thinking about it" and "Not decided yet" are the same grey pill. "To decide" uses `--look`, the same as Status's "Needs a look", and "Not this time" uses `--been` ("Went Thu 1 Oct"). Kinds now have three treatments: tile + word on Ideas, a grey tag on Plans, and the overline on the idea page. Plans also uses kind words ("Day trip", "Show", "Trip") that the Ideas page doesn't ("Outing", "Event").
- Fix: split tone from meaning. Keep the tone classes private, and give each domain its own named modifiers in the macro: `tag(wish_answer)` → `--yes`/`--thinking`/`--no`/`--undecided`, each visually distinct; `tag(plan)` for When/Went; and a separate `.chip--info` for facts like "Leave by". Draw kinds one way everywhere (icon + word, not a state pill), from one list of kinds.
- Severity: major. Effort: M.

**4. Control heights aren't tokens, and several are under the 44 px target** (`.btn` 46, `.btn--sm` 40, `.starter` 40, `.seg a` 40, `.textbtn` 32, `.card--setup .steps a` 32, `.rank > .linkbtn` 32 on phone, `.composer__send` 58/50)
- Problem: there are six control heights, and the standard says "every target is 44 px or more". The kid's "Take it off my list" (Wishes, kid) and "Delete this idea" are 14 px underlined `.textbtn`s, 32 px tall. These are destructive actions, in the smallest target, for kids.
- Fix: add `--control-sm: 44px; --control-md: 48px; --control-lg: 58px` and use only these. Raise `.textbtn`, the setup-step links, `.starter`, `.seg a` and `.btn--sm` to 44 px. Put destructive actions in a real `.btn--quiet` (or a new `--danger`).
- Severity: major. Effort: S.

**5. "Selected" is drawn five different ways** (sidebar nav, `.seg`, `.convo` desktop vs phone, `.choice`, tab bar, `.person-tile`)
- Problem: the current page in the nav is card + 3 px green inset bar. A segment is card + shadow. The current conversation is card + border on desktop but solid ink on phone. A picked choice is solid ink. The current tab is green-soft. A picked person tile is an ink outline. Kids learn "this one is on" from five different looks, and each new page (setup, family) will invent a sixth.
- Fix: define two selected styles and name them: `--sel-strong` (ink fill, white text: choices, conversation pills, person picker) for "picked value", and `--sel-place` (card + green bar or green-soft: nav, tabs, segments) for "where you are". Put both in one rule each.
- Severity: major. Effort: M.

**6. The kid's to-do row has no CSS** (My to-dos and kid Home: `.todo.todo--ro`)
- Problem: `todo--ro` is in the standard and the HTML but not in the stylesheet. The row falls back to the parent row with a neutral `.tile` (a 40 px rounded square) placed in the 44 px tick column, and keeps the grey 4 px left rule, which shows as a stray stripe in `desktop/todo-kid.jpg`. It looks like an idea card that has a tick inside.
- Fix: define `.todo--ro`: no left rule unless late; a plain 32 px ring (the tick's ring, not a button) or a list dot in the lead column; and a "Was due…" late treatment for kids.
- Severity: major. Effort: S.

**7. Six near-identical text-action components** (`.more`, `.linkbtn`, `.textbtn`, `.todo__edit`, `.crumb`, `.locked`)
- Problem: each is inline-flex + 700 weight + 15 px + gap 4/6 px + a min-height, with small random differences (14 vs 15 px, 32 vs 44 px). "Change" on Wishes, "Edit" on To do, "All plans ›" on Home and "List view ›" on Plans all look slightly different. New pages will add a seventh.
- Fix: one `.action-link` (44 px, 15 px, 700, icon gap `--s2`), with `--back` (leading chevron), `--forward` (trailing chevron) and `--locked` (ink-3, lock icon). Delete the other five.
- Severity: minor. Effort: S.

**8. Accent signals are overloaded: the left bar, dashed lines and the warn colour**
- Problem: the left accent bar is built three ways (`border-left: 4px` on `.todo--late` and `.ev`; inset shadow 4 px on `.srow--look` and `.rank--decide`; inset 3 px on the nav). Dashed lines mean "not looked up" (`.idea--unknown`), "surprise", "past plan", "pending message", "failed message" (red dashed), "setup step", and are also a plain divider (`.card__foot`, `.soon`, `.idea__foot`, `.decide`). The calendar tints weekend cells with `--warn-soft`, the same colour that means "set this up / needs a look", right under the yellow "not connected" banner on Plans.
- Fix: one `.accent` mixin (inset 4 px, `--accent` colour) for every bar. Dashed means only "not happened / not confirmed yet" (pending, past-to-rate, not looked up), and dividers go solid `--line`. Tint weekends with `--paper-2` (or a new neutral `--weekend`), not a status colour.
- Severity: minor. Effort: M.

**9. Off-scale values for spacing and type** (row titles, figures, headings)
- Problem: `6px` is used about 20 times as a gap (it's a token in all but name), along with `10px`, `14px`, `5px` and `7px` paddings. Row titles are 17 px (`.item__title`, `.todo__title`, `.convo b`), 18 px (`.rank__title`, `.srow__text b`, `.person-tile b`) and 20 px (`.idea h3`). Numbers come in 22/28/30/32/36/44 px (`.dt`, `.month-nav h2`, `.figure dd`, `.money`). A new list page has no rule for its title size.
- Fix: add `--s1h: 6px` (or snap to 4/8), plus `--t-title: 18px` for every row title. Add `--t-figure: 30px` and `--t-month: 28px`, and use them for the stray sizes.
- Severity: minor. Effort: M.

**10. Stylesheet hygiene: a patch block and some rules the stylesheet breaks itself**
- Problem: lines 412–419 are a grab-bag added after Chat (`.av > .icon` repeats line 210; `.tag__more` is defined twice; `.techie` in two places; `h2.card__head` adds a second card-head anatomy; `.adder--wish` does nothing). There are hard-coded `#FFFFFF` values (`.av`) and light-only shadows (`.seg a[aria-current]`, `.tabbar`) that don't change in dark mode, despite "never write a hex value outside `:root`". The tab-bar badge is 12 px and shows "3" with no word, against the 14 px floor and "badges always carry a word". Some classes aren't used yet (`ev--sam`, `ev--alex`, `msg--theo`, `plan-day`, `mini-ideas--one`).
- Fix: fold the patch block into its components. Tokenise `--on-person` and `--shadow-sel`/`--shadow-bar` with dark values. Give the tab badge 14 px plus an `.sr` word (or use the dot). Add a stylelint rule for hex values outside `:root` and a check for classes used but not defined, next to the CI check for `style=`.
- Severity: minor. Effort: S.

## Missing

- **Destructive actions and confirmation**: there's no `.btn--danger` and no confirm-page pattern. Memory's "forget this", deleting an idea, cancelling a to-do and removing a family member all need one.
- **Setup wizard parts**: a stepper or progress indicator, a step page with Back/Next, and a "done" state. Today `.steps` exists only as a Home card.
- **Settings detail controls**: on/off switch, money input with a `$` prefix, radio list with descriptions (choosing the AI model), a masked key field with "Test" and its result, and a time picker for reminders. Only `.check`, `.choice` and plain inputs exist.
- **Error and system pages** in the signed-out `.solo` shell: 404, server error, CSRF/session expired, "Vera's server is offline". Only the grown-ups page exists.
- **Plans list view, multi-day and all-day events**, and a plan that crosses a week or month boundary in the grid.
- **Long-list mechanics**: pagination or "Show more" for Ideas, To do (Done/All) and Memory. Only chat has "Earlier messages".
- **A data table pattern** beyond Status's `.jobs` (Memory entries, "What has changed" history, Family members), with its phone stacking rule.
- **Person colours 6–8 and their dark pairs**, with contrast checked (see Fix 1).

## One sentence

Key the person colours to eight numbered slots instead of the mockup family's names, because every avatar, bubble and calendar bar depends on them and the system can't render a real family until that changes.
