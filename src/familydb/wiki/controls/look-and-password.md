# Look and your password

Two pages belong to each person alone: **Look**, where you choose how the page looks for you, and **Your password**, where you choose the password you sign in with. Everybody signed in as themselves has both, a kid included. Neither is a family setting, and neither is something the assistant can change.

## Look

Open **Look** from your account menu, or from the menu on a phone. It has two parts: **Day and night**, then a grid of looks, each drawn as a small sample page. Pick one of each and press **Use this look**.

**A look changes colour and nothing else.** The layout, the words, what each page holds and what each button does stay the same. Red means late or broken in every look, and the assistant's own dark screen keeps its own colours in all of them, so it is recognisable whatever the page wears. Each look is checked against minimum contrast levels by day and by night before it is added.

### Day and night

| Choice | What it does |
|---|---|
| **Match my device** | Day when the phone or computer is set to day, night when it is set to night. This is where everybody starts. |
| **Always day** | The light version, whatever the device says. |
| **Always night** | The dark version, whatever the device says. |

Two looks have no day. Phosphor and Afterglow are green-screen looks, so they are always night whatever you choose, and their samples say "Night only".

### The looks

| Look | What it is | Day and night |
|---|---|---|
| **Kitchen Table** | The default. Cream paper by day, charcoal at night, deep green for what you act on, each person in their own colour. | Both |
| **Phosphor** | The page as first drawn: charcoal with a breath of green, lit like an old green screen. | Night only |
| **Afterglow** | Kitchen Table as charcoal glass with faint scanlines, and the assistant the one thing that glows. | Night only |
| **Midnight** | A blue-black page, a darker panel and soft-white ink. | Both |
| **Home Computer** | An early-80s family machine: a putty case, a brown-black keyboard and one orange key for "this one". | Both |
| **Ink** | Almost no colour: a white page, black ink and a black panel. | Both |
| **Enamel** | Old enamel signs: warm gray plaster, a deep petrol panel and earthy colours. | Both |
| **Rail yellow** | Station signage: a deep rail-blue panel, a crisp light page and one signal yellow for what you act on next. | Both |
| **Fjord** | A pale northern sky over deep slate water, with fjord blue for what you act on. | Both |

### Where your choice is kept

- **Signed in as yourself:** it is kept with your name, so it follows you to every phone and computer you sign in on. Everybody else keeps their own. The browser's own bar and scrollbars follow it too.
- **Before anybody signs in:** the sign-in page wears the look this browser last held. Signing in sets that browser's look from your saved choice, or clears it if you have not chosen one. Signing out does not clear it.
- **While the family still shares one password:** nobody in particular is signed in, so there is nothing to keep it with. The choice stays in this browser, for a year, and each screen can have its own. The page says which of the two applies.
- **Anything unrecognised** falls back to Kitchen Table. There is no household default: each person picks.

## Your password

Open **Your password** from your account menu, which shows it only when you are signed in as yourself. While the family shares one password, an admin reaches it from the Family page or setup step 2. [Sign-in and security](/wiki/controls/settings/sign-in) covers the settings an admin can change, and [Recovery](/wiki/operations/recovery) covers a password somebody has lost.

### Choosing one

The form asks for:

1. **The password you use now**, unless you signed in with a starting password. A wrong one is refused, and too many wrong tries make you wait a quarter of an hour.
2. **A new password**, of 12 to 200 characters. A short sentence is easy to remember and hard to guess, like *pancakes on sunday mornings*.
3. **The same again**, which must match.

Saving it replaces the old one at once. You stay signed in on this browser. **Every other phone and computer signed in as you is signed out** on its next click, because each sign-in carries a mark of the password it was opened with.

### A starting password

An admin makes a [starting password](/wiki/reference/glossary#starting-password) for you on the Family page. It is made up, shown once, and works only to get you in.

1. Sign in with your name and the starting password.
2. You land on a page headed **Choose your own password**. Nothing else on the page opens until you have, and the form does not ask for the starting one again.
3. Save a password of your own. The starting one stops working, and you go to Home (an admin with setup unfinished lands on Setup).

Only an admin signed in as themselves can make one, and not for themselves: an admin chooses their own. [Family](/wiki/controls/family) says how.

### Being signed out elsewhere

A phone or computer is signed out, and asks for a password on its next click, when:

- you choose a new password, or an admin makes you a new starting one;
- an admin takes your password away or switches you off;
- an admin uses **Sign everyone out**;
- it goes unused for longer than the days a sign-in lasts, 30 unless an admin changed it.

The next sign-in with a new starting password sends you back to choosing your own.

### While the family still shares one password

Until an admin has a password of their own, everybody signs in with the [shared password](/wiki/reference/glossary#shared-password), and this page is for an admin to choose theirs. It asks which admin you are when there is more than one, and does not ask for a current password.

**Choosing it ends the shared password for everyone.** It stops opening anything and everybody signed in with it is signed out. From then on each person signs in as themselves, with a starting password from you. Do this first, then make the starting passwords on the Family page.

### If you forget it

- **A kid:** ask a parent. The page names them.
- **Anybody else:** ask an admin to make a new starting password on the Family page.
- **The only admin:** use the command on the server, in [Recovery](/wiki/operations/recovery).

Developer docs: `src/familydb/web/look.py` and `web/looks.py` (the looks and the `fdb_look` cookie), `web/static/themes.css`, `docs/STYLE.md`, "Looks"; `src/familydb/web/family.py` (`you`, `choose`) and `familydb/family.py` (`choose_look`, `choose_password`, `claim`, `give_starting_password`).
