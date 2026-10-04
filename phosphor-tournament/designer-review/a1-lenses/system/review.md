# FamilyDB design review: is it one system?

## Verdict
**6.5 / 10.** The base layer is real: `style.css` has a tidy colour token set (`:root`), one card, one button family, one tag, a shared kind palette (`.k-*`) used by chips, icon tiles and calendar events alike, and the seven pages share one shell. Above that layer the system is mostly accidental. The same thing is drawn in two or three ways from page to page (a to-do row, an "upcoming plan" row, a warning banner, a spend meter, "not set up"). Radii, type sizes and spacing are loose literals rather than a scale, and the stylesheet already has one visible layout bug on the phone Settings page.

**Optimise before building?** Yes. The unbuilt pages (idea page, forms, setup, errors) will copy whichever variant the designer finds first, so the duplicates need to become one component each before there are fifteen pages instead of seven.

## Protect
- The colour tokens in `style.css` `:root` (paper/card/ink ×3, vera, sun, alert/warn/ok, each with a `-soft` pair) and the per-person avatar colours (`--sam`, `--alex`, `--maya`, `--theo`) used the same way on every page.
- The kind palette (`.k` + `--kb`/`--kf`), one definition that drives the Ideas kind chips, the Home "Just added" icon tiles (`.kicon`), the Plans calendar events (`.ev`) and the phone calendar bars.
- The date tile `.dt` (Home "Next up", Home and Plans "Coming up"): a recognisable, reusable object with `hot` and `sm` variants.
- The idea card on Ideas (kind chip, status tag top right, title, "for", dashed foot with direction arrow and drive time), with its whole-card link and `:has()` focus ring.
- Settings rows that each say how things stand in one line, plus a "Needs a look" or "Could be better" tag explained in the "Reading this list" card. This is the right pattern for every list of states.
- The type pairing (Fraunces headings, Atkinson Hyperlegible body at 17px) and the 44–46px minimum targets on nav items, buttons and inputs, which suit kids and phones.

## Fix, ranked

**1. One to-do row, not two** (Home "To do" card `.todo` vs To do page `.trow`)
- Problem: The same object has two anatomies. On Home it is a borderless row: a tick, then the owner and "6 days late" on one meta line, then a pencil icon with no label. On To do it is a bordered card with a red left edge for overdue rows, separate owner/date/reminder columns, the date plus "6 days late" stacked, and an "Edit" text link. Overdue looks different in each place, Home never shows the reminder state, and the edit control is icon-only on one page and labelled on the other. A kid learns two things for one task. The add-a-to-do form and the Wishes page will each invent a third version.
- Fix: Make one `todo-item` component with a single anatomy: tick (34px), title, a meta line (`.meta`: owner, due with "N days late" in `--alert`, reminder bell or "no reminder"), and an "Edit" link with icon and text. Add a `compact` modifier for Home that drops the "Add one" link and the card border, and nothing else. Overdue gets the same treatment everywhere: a 4px `--alert` left rule plus the late text. Delete `.trow`'s fixed 130/150/150px columns and lay out the meta line with flex-wrap, which also removes the two breakpoint overrides at lines 474–477 and 523–525.
- Severity: major. Effort: M.

**2. Four banner components for one job** (`.notice` on Plans and Status, `.notice.info` on To do, `.attn` on Settings, `.verdict` on Status; also `.setup` on Home)
- Problem: There are five near-identical "message with icon, text and action" blocks, each with its own radius (14 / 14 / 18 / 22 / 18px), padding (14×18, 18×22, 22×24), border colour as a raw hex (`#EED9A2`, `#C3DACE`, `#EFC3B6`, `#BFDCC8`, `#EBD69B`) and icon treatment (bare icon, 46px red disc, 56px green disc). Severity colour also does not follow the meaning. "Telegram isn't set up" is a calm green `info` notice on To do but a yellow "Not set up" tag on Home. "Google Calendar isn't connected" on Plans is yellow. The same kind of gap gets a different colour on different pages, so the family can't learn what yellow means. Error pages and setup steps will need this component first.
- Fix: Make one `.banner` with `--tone: ok | info | warn | alert`, radius `var(--r-md)` (14px), padding 16px 20px, a 40px icon disc in the tone colour, text, and an optional `.btn-sm` action. Add an `emphasis` size (icon 56px, h2 text) only for Status's top verdict. Rule: "not set up yet" = warn, "broken or blocking" = alert, "for your information" = info, "all good" = ok. Under that rule the To do Telegram notice becomes warn. Move the five hexes into tokens (`--warn-line`, `--info-line`, `--alert-line`, `--ok-line`).
- Severity: major. Effort: M.

**3. A state vocabulary for connections and setup** (Home "Vera today", Status "Connections" and "Which AI does each job", Settings "Connections" row)
- Problem: The same state is rendered three ways. Telegram is a warn tag "Not set up" on Home, a ghost button "Set up Telegram" with no tag on Status, and part of "2 not set up" on Settings. On Status, a missing *optional* backup is a red "None" tag with an × icon in the jobs table, while a missing Claude key in Connections is a grey "Not set". Both describe the same missing backup, one red and one grey. Red should mean something is wrong.
- Fix: Define four state tags and use only these: `On / Set` (ok), `Not set up` (warn, always with an action), `Optional` (neutral `.tag`), `Broken` (alert). In the Status jobs table, "Backup if it fails: None" becomes a neutral "No backup" tag. The yellow "No backup" notice beneath already carries the warning. Every connection row puts the tag in the same slot with its action beside it, on Home, Status and Settings.
- Severity: major. Effort: S.

**4. Fix the phone Settings row grid** (Settings, phone, every row without a tag: General, AI model, Spending, Lookups, What has changed)
- Problem: Each `.srow` without a tag still renders an empty `<span></span>` (settings.html line 66). At ≤820px the grid drops to three columns, so the empty span takes column 3 and the chevron wraps onto its own line under the icon, as the phone screenshot shows. That happens on 5 of 9 rows, and it is the clearest sign that the grid is hand-tuned per breakpoint rather than built as a component.
- Fix: Drop the empty span and give the row named areas: `grid-template-areas: "ic text go" ". tag go"` on the phone, and `"ic text tag go"` on desktop, with `.tag { grid-area: tag }` and `.go { grid-area: go; align-self: center }`. Use the same row component for Status `.conn` (same icon tile, title, status line, trailing slot), which is the same pattern with different class names and a 42px/12px tile instead of 46px/14px.
- Severity: major (visible bug). Effort: S.

**5. Collapse the list-row zoo into one "item row"** (`.soon` Home, `.plist` Plans, `.wish-kid` Home, `.conn` Status, `.srow` Settings, `.mini-idea` Home, `.convo` Chat, `.health .row` Home)
- Problem: There are eight row patterns with leading visual + title + subline + trailing slot. Each has its own padding (6, 8, 10, 12, 16×20px), hover colour (`--paper`, `#fff`, `--card`) and subline size (14 vs 15 vs 15.5px). Home "Coming up" and Plans "Coming up" list the same four plans with two classes (`.soon` / `.plist`). Plans shows who's going ("Maya and Theo", "Everyone") and Home doesn't. The idea list, the memory list, the family list and the wishes page will each add another.
- Fix: Make one `.item` (grid: `lead | body | trail`, gap 14px, padding 10px 12px, radius 12px, hover `--paper`), with slots for a `.dt`, `.av`, `.kicon` or `.ic` lead. The body is title (700, 17px) plus `.meta`. The trail holds a tag, button or chevron. `.item.boxed` adds the card border for `.mini-idea`. Home and Plans "Coming up" then render the same markup and show the same fields.
- Severity: major. Effort: M.

**6. Make radius, spacing and type real scales** (`style.css` throughout)
- Problem: There is one radius token (`--r: 18px`), and around it the file uses 4, 9, 11, 12, 14, 16, 20, 22 and 24px literals. Gaps and margins use 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24 and 26px. Font sizes run to about 18 distinct values (11, 12, 13, 14, 15, 15.5, 16, 17, 18, 19, 20, 21, 22, 23, 26, 28, 30, 32, 34, 42, 44), including inline `style="font-size:20px"` (chat.html line 69) and `style="font-size:44px"` (status.html line 67). The result: the Home Ask box is 24px round, the Status verdict 22px, cards 18px, the to-do row 16px, banners 14px. Everything is "roundish" but no two are the same. There are 31 inline `style=` attributes across the pages, plus nine raw colours in the CSS (`#FFFBF1`, `#F8F4EC`, `#F1ECE2`, `#FFF6F2`, `#E8B33A`...).
- Fix: Add `--r-sm: 8px; --r-md: 12px; --r-lg: 18px; --r-pill: 999px` and map every literal to the nearest one (inputs, rows and banners go to md, cards and Ask go to lg). Add a 4px spacing scale `--s-1…--s-8` (4, 8, 12, 16, 20, 24, 32, 48) and snap 22, 26 and 14 onto it. Use 7 text sizes: 13 (caps labels), 15 (small), 17 (body), 19 (h3), 23 (h2), 32 (h1 phone / big numbers), 42 (h1). Use one `.figure` class for money and stats (`.big-money`, `.stat .v`) instead of three sizes. Lint for `style=` and hex values outside `:root`.
- Severity: major (it is what makes the next pages drift). Effort: M.

**7. One composer, one Send** (Home "Ask Vera" `.ask-box` vs Chat `.compose-row`)
- Problem: The same action, writing to Vera, has two looks. Home has a yellow `btn-sun` "Send", a 16px-radius 58px box and no "who's writing". Chat has a green `btn-primary` "Send", a 14px-radius 56px box, and a "Writing as" picker. Yellow appears nowhere else as a button, so `btn-sun` is a one-off. On the phone, Home's suggestion chips are cut off at the edge ("Remi…").
- Fix: Make one `composer` component (textarea, Send `btn-primary`, optional suggestion chips, optional "Writing as" picker, optional "Send where I am") used on Home and Chat. On the dark Ask panel, Send can be `btn-sun` if you want the warmth, but then it is the composer's on-dark variant, used there and nowhere else, not a general button. Keep radius at `--r-md`. On the phone, wrap the suggestion chips to two lines rather than scrolling them off-screen.
- Severity: minor. Effort: S.

**8. Same words for the same things** (Ideas, Plans, To do, Home)
- Problem: The whole household is "Anyone" on Ideas, "Everyone" on Plans "Coming up", and "Household" on To do and Home. All three use the same grey star avatar `.av-home`. An idea that hasn't been checked is "Not looked up yet" on Ideas and "Vera hasn't looked it up yet" on Home. Dates are written "Sun 27 Sep", "SUN 4 OCT", "Sunday 27 September" and "Tomorrow · 13:00". Kids will read "Household" and "Everyone" as different people.
- Fix: Use a single label, "Everyone", wherever `.av-home` appears. Use one string per idea status ("Not looked up yet", "Planned · Sat 17 Oct", "Went Thu 1 Oct"). Use one date helper: short "Sat 17 Oct", relative "Tomorrow 13:00" only within 6 days, and long only for the chat day separator. Put these in a content sheet next to the tokens.
- Severity: minor. Effort: S.

**9. Segmented control and filters on the phone** (To do "Open / Done / Cancelled / All", Plans "Month / List", Ideas filters)
- Problem: `.seg` has `flex-wrap: wrap`, so on a 390px phone the To do control breaks into two rows with "All" alone on the second line inside a pill-shaped track. The To do search under it is capped at 320px and stops short of the right edge, unlike every other input on the phone. On the phone, `.trow .rem` is hidden (lines 474–476 already hide it below 1180px), so the brief's "whether it has a reminder" disappears on phones and small laptops.
- Fix: Make `.seg` `flex-wrap: nowrap; overflow-x: auto`, or below 480px make the segments equal-width (`display: grid; grid-auto-flow: column; grid-auto-columns: 1fr`) at 15px text. Set `.todo-bar .search { width: 100% }` under 820px. Keep the reminder as a bell icon in the to-do meta line (fix 1) instead of hiding a column.
- Severity: minor. Effort: S.

**10. Icon tile and avatar sizes** (`.kicon` 46/14, `.srow .ic` 46/14, `.conn .ic` 42/12, `.attn .ic` 46 round, `.verdict .big` 56 round, `.av` 24/28/30/40, Chat picker avatar 28)
- Problem: These are near-duplicate leading visuals with off-by-a-few sizes. The variation isn't intentional, and new pages will pick any of them.
- Fix: Use two tile sizes (`--tile-md: 40px`, `--tile-lg: 56px`, radius `--r-md`) and three avatar sizes (24, 32, 40). Make `.ic` and `.kicon` one class whose colour comes from either `.k-*` or a tone.
- Severity: minor. Effort: S.

## Missing
- Form patterns for the add-an-idea, edit-to-do, password and setup pages: field error and help text, required markers, a disabled button, a "saved" confirmation, and grouping of long forms. The only form shown is a one-line quick add.
- Empty states as a component: only text exists ("No wishes yet", "Nothing yet"). There is no designed empty Ideas grid, empty To do filter, empty month, or a new install with no data.
- Error and outage states: Vera over the daily limit, the AI key failing, Telegram disconnected, a lookup that failed, 404 and sign-in errors. Only the "all good" Status verdict is drawn.
- The kid's view: what a kid's Home, nav and tab bar look like without Settings or Status, and the ranked wish-list item, which is a new row type with reordering that must work without JavaScript.
- Setup steps: a step/progress component. Home's dashed numbered list (`.setup li::before`) is the only hint, and it has no done or current state.
- The "More" tab on the phone: the menu that holds Wishes, What Vera knows, Status and Settings, plus where the Settings red "1" badge goes on the phone.
- Dark mode or high-contrast tokens (none are defined), and a documented focus style on dark surfaces. `.ask` switches to a sun outline, and nothing else on a dark surface is specified.
- Loading and in-progress states for no-JS form posts ("Vera is thinking…", a lookup running, "Check again" on Status).

## One sentence
Before building anything else, turn the stylesheet into a small named component set (one item row, one banner with four tones, one to-do row, one composer, one state-tag vocabulary) on top of real radius, spacing and type scales, so the next eight pages are assembled from parts rather than redrawn.
