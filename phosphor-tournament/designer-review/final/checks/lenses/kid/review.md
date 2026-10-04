# Review: FamilyDB final design, through the eyes of Maya (11) and Theo (9)

## Verdict
**7.5 / 10.** Maya can read her pages, find what is hers ("My wishes", "My to-dos", "You and Vera") and tell what she can't do, because the "Moving it? Ask a parent" lock and the kind grown-ups page say so without scolding her. But nothing on her pages looks like it belongs to her rather than to her parents' app: same cream-and-green, same serif, no picture on a wish, no fun when a wish gets a "Yes!". On phone her own things sit at the bottom of Home, and the one thing she can do with a to-do ("Tell Vera") makes her type it all out herself.

**Optimise before building?** No. The kid pages are well built, and every fix below is a small change to a component that already exists, so it can go into the first build pass.

## Protect
1. **Home (kid), Ask Vera card**: the "What can we do this weekend?" chip sends with one tap, and "I wish for…" / "Can you help me with…" open the chat with the words already typed. A 9-year-old can start a conversation without knowing what to write.
2. **Home (kid), lede**: "Roller rink tomorrow with Theo, and Sam said yes to one of your wishes!" is the best line in the app. It talks to her, it's about her, and it gives good news first.
3. **My wishes, each row**: the number, the status tag ("Thinking about it", "Yes!", "Not this time") and the parent's quoted reason ("Not on a school night. Ask again for the long weekend.") together explain a "no" fairly. Keep the quote on every decision.
4. **Grown-ups page** (`grownups`): "This part is for grown-ups… There's nothing here you need to do" with "Go to my Home" and "Ask Vera something". It's friendly, not a telling-off, and never shows an error.
5. **Chat (kid)**: "Sam and Alex can read your chat with Vera" shows at the top, "20 messages left today" in the footer, and "Share where I am (ask a grown-up first)". These are honest about privacy and limits, in her words.
6. **States, kid versions**: "You've sent all 20 of today's messages" and "Vera is resting until tomorrow… I'll be back tomorrow morning". There's no money or company names, and Vera still sounds like a person.

## Fix, ranked

**1. Her to-do looks like a box she can tick, but she can't** (My to-dos and Home (kid) › My to-dos, the `.tick-ro` tile)
- Problem: the read-only tile uses the same `#i-todo` icon (a square with a tick in it) that parents tap to tick off. Theo will press it, and nothing will happen. Or he'll read it as "already done". The explanation sits in a separate banner below the row.
- Fix: give the row a different icon (e.g. `#i-clock` or a person icon for "Set by Alex"), and put a tag in the row itself: "Not done yet" or, after she reports it, "Waiting for Alex to check". Never use a square or checkbox shape for something she can't tick.
- Severity: major. Effort: S.

**2. Saying "I did it" takes too many steps** (My to-dos › "Tell Vera" button; Home (kid) › My to-dos footer)
- Problem: "Tell Vera" opens an empty chat. She then has to remember and type "I packed my swim bag". Most 9-year-olds won't bother, and it uses up one of her 20 messages.
- Fix: put an "I did it!" button on each of her to-do rows: a POST form that tells Vera and the owner, doesn't count against her messages, and turns the row's tag into "Waiting for Alex to check". Nothing gets ticked, so the family rule still holds. If you'd rather keep chat, at least link to `chat-kid.html?draft=I+packed+my+swim+bag#msg`, the way the "I wish for…" chip does.
- Severity: major. Effort: S–M.

**3. On phone her own stuff is at the very bottom** (Home (kid), phone, card order)
- Problem: on desktop "My wishes" and "My to-dos" sit top right, but on phone they come after "Next up" and "New ideas", about four screens down. The family's ideas come before her own list.
- Fix: on phone, put "My wishes" (top 3 plus "Add a wish") straight after Ask Vera, then "My to-dos", then "Next up for you", then "New ideas". Change the source order or the grid order for the kid Home only.
- Severity: major. Effort: S.

**4. Her pages look exactly like her parents' pages** (all kid pages: header, cards, Wishes rows)
- Problem: the only sign it's hers is a small pink "M" avatar. The kid pages use the grown-ups' look: a calm cream colour, small grey 13–15 px meta text, and serif headings. That's not babyish, which is good, but at 11 it reads as "Mum's planning app I'm allowed into". Theo will find it boring.
- Fix: within the same stylesheet, use her own colour (`--maya-soft` / `--theo-soft`) as the page header band and the active nav tint on kid pages. Let each wish carry an emoji or a picked icon. When a wish is a "Yes!", show it in a bigger celebratory card at the top of My wishes. This needs CSS only, no script.
- Severity: major. Effort: M.

**5. "Yes!" news is easy to miss** (My wishes and Home (kid) › My wishes)
- Problem: "Yes!" is a tag the same size as "Not decided yet". The lede links to "one of your wishes" without saying which one, and nothing marks what changed since she last looked.
- Fix: name the wish in the lede ("Sam said yes to your sketchbook and brush pens!"). Put a "New" marker on any wish whose answer changed since her last visit. Make the "Yes!" row's left rule green, like the red rule on late to-dos.
- Severity: minor. Effort: S.

**6. No warning before her messages run out** (Chat (kid) footer, "20 messages left today")
- Problem: it's small grey text that doesn't change until she hits 0, and then she's cut off mid-conversation (the states page shows this happening while she's naming her hamster).
- Fix: at 5 or fewer, turn the count into an amber tag: "5 messages left today". At 1, say "Last message for today: make it a good one". Show the same count on the Home Ask Vera card.
- Severity: minor. Effort: S.

**7. Plans is hidden under "More" on her phone** (kid tab bar: Home, Chat, Wishes, To do, More)
- Problem: what she most wants to know is "what are we doing this weekend?", but Plans isn't a tab. "To do" gets a tab, and she usually has one item there, which she can't tick.
- Fix: for kids, use the tabs Home, Chat, Wishes, Plans, More, and put "My to-dos" in More and on Home. Or keep To do and swap it for Plans only when she has no to-dos.
- Severity: minor. Effort: S.

**8. "Kid · picked" on sign-in** (Sign-in › Pick who you are, Maya's tile)
- Problem: "Kid" as a label for yourself, next to "Admin" and "Parent", is a bit flat. "· picked" reads like a typo at 9, and the selected state relies on a thicker border.
- Fix: drop the role line for kids (just "Maya"), or say "That's me ✓" on the picked tile. Keep the thicker border.
- Severity: minor. Effort: S.

**9. Theo is never drawn** (all kid pages show Maya, 11)
- Problem: the younger, weaker reader isn't checked. His wish list and Home must also hide the "Lego set for Theo · Surprise", and all his text must work at 9.
- Fix: draw `home-kid` and `wishes-kid` as Theo with his real data, read the copy aloud at age 9, and check the "Surprise" filter on his Home, Ideas and Plans.
- Severity: minor. Effort: S.

**10. Late to-do wording for kids is specified but not shown** (STANDARD.md, words table: "Was due Sun 27 Sep" for kids)
- Problem: no kid page shows a late to-do. Without a drawn example, an engineer may reuse the parents' red "6 days late" and the red rule, which feels like being told off.
- Fix: add a late row to `todo-kid`: "Was due Sun 27 Sep", a soft amber rule, and "I did it!" (Fix 2).
- Severity: minor. Effort: S.

## Missing
- Kid's **More** page (`more-kid.html` is linked from every kid tab bar but not drawn): what's in it, and where "Sign out" is.
- Kid's **Plans** page: without "Add a plan", the "How did it go?" faces and "Move it", and with presents hidden. Showing "Next up for you" first.
- Kid's **Ideas** and **idea** pages: read-only, no gift ideas, no "Save a thought" or "Add an idea" (or, if kids may suggest, "Tell Vera your idea").
- Kid's **What Vera knows**: can Maya make Vera forget things about herself? The brief says anyone can. Draw it with her own facts first.
- A **first visit** for a kid: a one-card hello on Home ("This is your space: your wishes, your chat with Vera…") instead of the parents' setup checklist.
- An **empty wish list** and an **empty "You and Vera"** state written for a 9-year-old, with example wishes as tappable chips.
- **Forgot my password** as the kid sees it: just "Ask Sam or Alex", plus a way to ping them through Vera without signing in.
- **Dark mode** check of the kid colours (Maya pink and Theo orange bubbles and tags) at kid font sizes.

## One sentence
Give each kid a one-tap "I did it!" on their own to-dos and put their wishes at the top of their phone Home, so their first two screens are about them and something they can actually do.
