# Stage 8: the whole app, part 1

After many more rounds exploring other directions (calendars, boards, logbooks, a dozen palettes),
the family came back to this one: **"Ok, you sold me on the Kitchen Table (final) idea. Let's flesh
this out and prepare to make it into a real interface for the app. Go ahead and design it."**

So Kitchen Table, as it stands in this folder after stage 7, is the design. Its look is settled:
keep its type, colour, brand, Vera's sign and the phosphor touches as they are. Now it has to cover
the real app, page for page.

## The real app

`app-reference/` holds the app's real page templates (`templates/`), its current stylesheet, the
web modules that feed them (`routes.py`, `views.py` for the wording, `fields.py` for the settings
pages, `status.py`, `setup.py`, `family.py`, `auth.py`), `roles.py` and the current `STYLE.md`.
Read them to know what each real page shows, says and does: they are the source of truth for
content and behaviour. Your mockups so far cover the main pages; the real app has more.

## Three notes the family gave while exploring, that apply here too

1. **No starter buttons on Ask Vera.** "The boxes 'next weekend', 'remind me…', 'save an idea…'
   don't add much and take up space. Vera figures all that out on her own." Remove them everywhere
   (Home, the kid's Home, Chat, states). Keep the box, Send, and "Goes to the family chat as …".
   An empty chat can rest on a line of Vera's own words already in the app.
2. **The greeting must earn its space.** "The big 'Good morning' header looks good, but takes a lot
   of space that doesn't do any work." Keep its warmth, make it small; the useful line (what's
   coming and what's late, with its links) stays prominent. On desktop, Ask Vera, Next up and the
   start of To do should sit on the first screen; on the phone, Ask Vera and the next plan.
3. **The phosphor echo is loved:** "enough green CRT to echo the history of the design." Keep every
   phosphor touch at its current strength. Don't add more.

## This stage: the missing everyday pages

Design, in this system, every real page below that has no mockup yet, with real content from the
templates and `views.py` wording (keep the words; where a page's wording reads badly in the new
layout, keep the meaning and say what you changed in CHANGES.md):

- `plans-list.html`: the plans list (the real `/plans`, beside the month you have)
- `restaurants.html`: the real `/restaurants`
- `memory.html`: "What Vera knows" (`/memory`), with adding and forgetting
- `you.html`: Your password (`/you`), including the first-sign-in case where a starting password
  must be replaced, and `password-shown.html`: a starting password shown once to an admin
- `member.html`: adding or changing a family member (the real `member_form.html`), and the Family
  page itself if `grownups.html` doesn't already cover the real `family.html`
- `idea-edit.html`: changing an idea (`idea_form.html` in edit mode)
- `activity.html`: one message's or one lookup's history for an admin (`/status/activity/<key>`)
- `403.html`
- Check your existing pages against the real templates: anything the real page shows or does that
  a mockup lacks, add.

Every page light and dark, desktop and phone, rendered with `DARK="<every page>"
./_kit/render-all.sh .`; look at every shot, fix, render again. Add to CHANGES.md (stage 8) and
STANDARD.md for any new component. Reply with what you made and anything unfinished.
