# Stage 8: the whole app, part 1

Kitchen Table's look is unchanged: same type, colour, brand, Vera's sign, and every phosphor touch at the same strength, none added. It now covers the real app's everyday pages, with content and wording from `app-reference/`. All pages are rendered light and dark, desktop and phone: looked at, fixed, rendered again.

**The family's notes**
- **Starters** are gone from Ask Vera everywhere. The kid's empty chat rests on the app's own line.
- **The greeting** is one small line. The useful line under it is the large one. The Ask box's label, "What's on your mind?", is Home's h1.
  - Desktop: Ask, Next up and the start of To do are on the first screen.
  - Phone: Ask and the next plan.
- **The phosphor** is untouched.

**New pages**
- `plans-list.html`
- `restaurants.html`
- `memory.html`
- `you.html` and `you-first.html` (the first sign-in with a starting password)
- `password-shown.html`
- `family.html` and `member.html`
- `idea-edit.html`
- `activity.html`
- `403.html`
- `wishes-maya.html` (one kid's wishes, with the answer forms; missing until now)

**Existing pages brought to the real app**
- Real footer, "Your password", Sign out as a form, everywhere.
- **Kids:** no "What Vera knows", and only their own chat.
- **Sign in:** name and password typed; the family is never listed.
- **Home and Chat:** real placeholders and ledes, Vera's last line, the kids' conversations.
- **Ideas:** real filters and "Save a thought for later".
- **An idea:** place panel, facts, lookup row, "Record how it went", Edit / Drop it.
- **New idea:** the real fields.
- **To do:** deadline, window, reminder, repeats, Status select. Reminders appear in the chat; "needs Telegram" was wrong.
- **Wishes:** three lists per kid; no "Thinking about it".
- **Status:** connections, money by kind, recent activity, waiting, worth a look.
- **Month view and 404:** the real words.

**Unfinished** (listed in CHANGES.md)
- A parent reading a kid's chat.
- Whole-page versions of the plain parent and shared-password shells.
- The chat's other waiting lines and "used …" notes.
- Status's full model-price tables.
- Telegram knocks on Family.
- Settings and setup are stage 9.
