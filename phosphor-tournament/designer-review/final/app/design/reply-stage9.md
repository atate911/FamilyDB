Stage 9 is done: the settings pages, the setup pages and where themes are chosen are all drawn from `app-reference/`, and the look is as stage 8 left it, with no phosphor added. All 57 pages render light and dark, desktop and phone: 228 screenshots, no warnings, and no inline style or script. Three reviewers looked at every new screenshot, and I fixed what they found and rendered again.

**Settings**
- **`settings.html`** now matches the real `/settings`: a row per page, each with the real lines on how it stands. Every row opens its own page.
- **Nine section pages**: `settings-general`, `-model`, `-spending`, `-messages`, `-lookups`, `-personality`, `-connections`, `-security` and `-history`.
  - Every group, box and help line is from `fields.py`, and boxes changed here say so.
  - Fine-tuning groups fold away and say how many of their boxes were changed.
  - Dropdowns show "Default (…)". The model and chat lists end in "Another…", which opens a box to type in using CSS alone.
  - Each form has one Save that stays at the bottom of the screen while you scroll.
  - Everything else the real pages have is drawn too: the company cards, key steps, the nine automatic messages with "Sent lately", Vera's lines with "Reads as", Telegram and Google Calendar, see a key, sign everyone out, and the change history.

**Setting up**
- **The overview, `setup.html`**, plus one page per step (`setup-you`, `-password`, `-model`, `-home`, `-telegram`, `-family`, `-calendar`), `setup-done` and `setup-told` (the model step after a key was refused).
- **The pages tell one story:** Sam setting up a new install. The steps run along the top, and Back and Next sit at the foot.
- **An extra page, `setup-telegram-link.html`**, shows the Telegram step once the bot is connected and is waiting for your phone. The Family step also shows people who wrote to the bot waiting to be let in, which stage 8 left out.

**Choosing a theme**
- **For the family**, it's under Settings › General › "How it looks".
  - Each theme is a card with a small preview of Home, by day and by night.
  - The one in use is marked, and Light / Dark / Match this device sits below.
  - Kitchen Table, Rail yellow, Enamel, Midnight and Ink are the five themes on show.
- **For each person**, it's on their own page, now called "You" (it was "Your password"). They can keep the family's theme or pick their own, and choose their own light or dark.
- **Kids get the same**, on `you-kid.html`. It only changes their own screen.
- **No scripts:** it's all plain radio buttons and Save, and the page reloads in the new theme. I also made the stylesheet switch between light and dark from an attribute on the page, so the server only has to set it.

The stage 9 section is added to CHANGES.md, and the new components and the theme notes for the engineer are in STANDARD.md.

**Unfinished:**
- **Other states of some steps** aren't drawn: Telegram while connecting or refused, and Google's sign-in and calendar choice.
- **Other states of some settings pages** aren't drawn: Personality after you've rewritten her, Connections once connected, and a key shown on Sign-in and security.
- **Personality shows only some of Vera's lines.** The real page has about 60 in eight groups.
- **The themes themselves aren't designed**, as STAGE9.md asked.
- **Two mismatches from earlier stages are left alone:** the sidebar's "Settings · 1 to check" and the home page's setup card don't match the real settings overview, where nothing needs a look in this sample.

One slip: early on, a shell command wrote `/setup-dump.txt` at the filesystem root, outside the folder. It's a copy of the setup templates and nothing else. Deleting it needed your approval, so it's still there; you can remove it with `rm /setup-dump.txt`.

STAGE10.md wasn't touched. This reply is also saved as `reply-stage9.md`.
