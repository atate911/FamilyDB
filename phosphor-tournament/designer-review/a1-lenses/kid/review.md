# Review: FamilyDB design, as Maya (11) and Theo (9) would see it

## Verdict
**6/10.** The bones are kid-friendly: big readable type, plain words, a "write to Vera" box first on Home, and colour-and-initial avatars that let Maya and Theo spot what is theirs. But every page is drawn as Sam (a parent) sees it, so nothing shows what a kid's own screen looks like, what they can and can't do, or how surprises like "Buy Maya's birthday present" are kept from them. The kids' own things (wishes, their own chat) are small, grey or hidden, so the app still feels like it belongs to the grown-ups.
**Optimise before building?** Yes. The kid view isn't designed yet, and the shared lists as drawn would show the kids their own birthday and gift surprises.

## Protect
1. Home, "Ask Vera" panel: the first thing on the page, with a big yellow Send button and ready-made chips ("What should we do next weekend?", "Save an idea…"). A 9-year-old can start without typing a perfect question.
2. Avatars everywhere (Maya = pink "M", Theo = orange "T") on Next up, Ideas cards, To do and Chat. Colour plus initial is how a kid scans for "that's mine".
3. Plans, "How did it go?" card: three big face buttons (happy, neutral, sad). Kids will want to rate things, and the faces need no reading.
4. Chat, left column note: "Parents can read the kids' chats. Maya and Theo see a note saying so." Being honest about this is right for 8–13s. Keep it, and say it to the kid in their own chat.
5. Type and copy: Atkinson Hyperlegible body text at about 15–16 px, tap targets of 44 px or more on phone, and short plain lines ("Tick one off when it's done"). It is readable and not babyish. Keep the grown-up look; 11-year-olds hate cartoon design.
6. Ideas cards: a coloured kind tag with an icon (Activity, Show, Outing, Seasonal) and a drive time in plain words ("about 22 min"). Easy to skim, and it makes picking a weekend outing feel fun.

## Fix, ranked

**1. Surprises leak to the kids** (Home, To do card; To do page, "Buy Maya's birthday present"; Ideas, "Lego set for Theo")
- Problem: Lists that everyone can see show gift plans to the child they are for. If Maya signs in, Home and To do read "Buy Maya's birthday present", and Theo sees "Lego set for Theo" on Ideas. It spoils surprises, and parents will stop trusting the app with anything secret.
- Fix: Add a "Hide from…" choice (or a "Surprise 🤫 — hidden from Maya" lock tag) on to-dos, ideas and plans. For the hidden kid, the item is simply left out: no greyed-out row and no count that gives it away. Vera should mark gift-type items as surprises by default. For parents, show a small lock tag reading "Hidden from Maya" on the row.
- Severity: blocker. Effort: M.

**2. No kid version of Home** (Home, whole page)
- Problem: The brief says kids sign in as themselves, but Home is only drawn for Sam: "Finish setting up", "Vera today $0.00 of $2.00", and the whole family's overdue to-dos. Theo would see Alex's dentist call shown as "6 days late", which isn't his to fix, and money he can't change.
- Fix: Draw the kid Home. Keep the greeting ("Good morning, Theo.") and Ask Vera at the top. Then "Next up for you" (only plans marked for Theo or Anyone), "My to-dos" (only his, with a big tick circle), "My wish list" (his top 3 with a "+ Add a wish" button), and "New ideas" (the 4 cards). Take out setup, spend, Vera today and other people's to-dos.
- Severity: blocker. Effort: M.

**3. Wish lists are a dead end** (Home, "Wish lists" card; phone tab bar, "More")
- Problem: The card says "No wishes yet" twice, with the only how-to in small grey text ("Kids can tell Vera 'I wish for…'"). There's nothing to tap. On phone, Wishes is hidden under "More", so the one thing that is really a kid's own takes the most work to find.
- Fix: Give each kid row a button, "+ Add a wish", that goes to the Wishes page with a text box. For the signed-in kid, swap "Plans" in the phone tab bar for "My wishes" (gift icon), so it reads Home · Chat · Ideas · My wishes · To do · More. Write the empty state for the kid: "Nothing here yet. What would you love? Tell Vera or add it here." Rank with ↑/↓ buttons (they work without scripting).
- Severity: major. Effort: S.

**4. A kid can't tell what they're allowed to do** (To do, "Edit" links and "Who" select; Plans, "Add a plan"; Ideas, "Add an idea")
- Problem: Every row has Edit, and every page has a green Add button. Nothing shows which of these a kid can actually use. If a tap fails, or quietly needs a parent, the kid feels told off or confused.
- Fix: For kids, show Edit only on their own items. Where something needs a parent, show the button with a small lock and the words "Ask a parent", not a hidden button or an error. Show wish states as tags in words: "Thinking about it", "Yes! 🎉", "Not this time". Write the rules once in kid words at the top of Wishes: "You add and rank. Mum and Dad decide."
- Severity: major. Effort: M.

**5. "Writing as" lets a kid post as a parent** (Chat, "Writing as Sam / Alex / Maya / Theo" picker)
- Problem: On a shared laptop, Theo can tap "Sam" and tell Vera "Put the roller rink on Saturday". It's tempting and confusing, and a parent can't tell who really asked.
- Fix: Default the picker to whoever is signed in. Choosing a parent's name while a kid is signed in should go to the sign-in page ("Sam needs to sign in"). Choosing a kid's name from a parent session is fine. Label it "Who's typing?", not "Writing as".
- Severity: major. Effort: S.

**6. Times and dates are hard for a 9-year-old** (everywhere: "13:00", "19:00", "09:00" with slashed zeros; To do, date field "mm/dd/yyyy")
- Problem: This is a US family (Vancouver, WA; mm/dd/yyyy date field), but times are on a 24-hour clock with slashed zeros, so "19:00" reads to Theo like a code, not "7 at night". The empty "mm/dd/yyyy" date box is also hard for a kid to fill in.
- Fix: Show times as "1 pm" and "7:30 pm" (12-hour clock is the family default; keep 24-hour as a setting) and turn the slashed zero off for times (`font-variant-numeric: normal`, or a non-slashed digit face). On the quick add, show buttons first, "Today", "Tomorrow", "This weekend", "Pick a date…", with the date field behind the last one.
- Severity: major. Effort: S.

**7. Grown-up words in kid places** (sidebar, "Behind the scenes" and "Not you? Switch"; Ideas, "Not looked up yet / Look it up", status filter, "Show" button; To do, "Household" and "Whenever suits")
- Problem: Theo doesn't know what "looked up" means or why it matters. "Household" isn't a person, and the "Show" button on Ideas only makes sense if you know the filters wait for it. None of it is hard for Maya, but it's dull and makes the app feel like it's for the grown-ups.
- Fix: In the kid view, change "Not looked up yet / Look it up" to "Vera hasn't checked this yet / Ask Vera to check". Change "Household" to "Everyone", "Whenever suits" to "No rush", and "Not you? Switch" to "Not Theo? Swap person". Change the filter button to "Show ideas", and add a "For me" quick filter tab beside "All ideas" and "Restaurants".
- Severity: minor. Effort: S.

**8. "Reload if nothing shows" will look broken to a kid** (Chat, the note under the write box)
- Problem: With no scripting, Vera's reply doesn't appear on its own. A kid sees their message sit there and thinks the app is broken or Vera is ignoring them. Nobody reads the small grey "Reload if nothing shows".
- Fix: After sending, show a Vera bubble saying "Vera is thinking…" and a real button, "↻ See Vera's answer" (a link to the same page, with a meta refresh after about 5 s, which works without JS). Remove the grey hint.
- Severity: major. Effort: S.

**9. The kid's own chat feels like an afterthought** (Chat, left list "Maya's own chat · nothing yet")
- Problem: The kids' chats are small grey rows under Family, with "nothing yet". On phone the Family pill is the dark, selected one. Kids won't feel they have their own space with Vera.
- Fix: For a signed-in kid, open their own chat by default, with a header like "You and Vera" and a one-line note: "Mum and Dad can read this chat." Start the empty state with three kid prompts: "I wish for…", "What can we do this weekend?", "Remind me to pack my swim bag".
- Severity: minor. Effort: S.

**10. Red "late" labels nag the kids** (To do, red "OVERDUE · 3" header, red left bars and "6 days late")
- Problem: This is fine for parents. For a kid's own chores, a red bar and "6 days late" feels like a telling-off, and kids stop opening the page.
- Fix: For a kid's own to-dos, use amber, not red, and the wording "Was due Sun 27 Sep". When they tick one off, show a short line, "Nice one, Theo ✓", on the reloaded page.
- Severity: minor. Effort: S.

## Missing
- The kid view of every page they can use (Home, Chat, Ideas, Plans, To do, Wishes), signed in as Maya and as Theo.
- The Wishes page: adding, ranking with ↑/↓, the parent decision states, and what the kid sees after a "Not this time".
- Kid sign-in: how a 9-year-old signs in on a shared laptop without a parent typing a password, and a clear "Sign out" for the next person.
- A friendly "This part is for grown-ups" page if a kid opens /status or /settings directly, not an error.
- What a kid sees when Vera has hit the daily spend limit ("Vera's resting until tomorrow"), and when Vera doesn't understand.
- Surprise items: the parent-side lock and hidden states (see Fix 1).
- Empty states written for kids: no plans this month, no ideas for me, no to-dos ("All done! 🎉").
- Phone Plans: the month grid shows only coloured bars, so it needs a tap-a-day or "this week" list that tells a kid what is on Saturday.

## One sentence
Design the screens Maya and Theo actually see when they sign in: their own Home with their wishes, chat and to-dos up front, surprises hidden, and every off-limits action marked "Ask a parent" instead of left to guess.
