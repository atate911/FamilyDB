# Setup

Setup walks a new install through the seven things it needs, one short page each, and shows how far you have got. Only an admin can open it, at `/setup`. A parent or a kid who tries is shown which admins to ask.

You do not have to finish it in one sitting. Each step page says why it matters and what to do, and you can skip any step and return: the pages pick up wherever things stand. [Install and first run](/wiki/operations/install) covers what comes before it, on the server.

## How progress is read

**Nothing records that a step is done.** Each time you open a setup page, the page checks whether what the step sets up is there, and reads the result. It makes no network call and no model call. So a step goes back to not done if you undo it: remove the Telegram token and the Telegram step is open again. Skipping a step only moves you to the next page.

Each step has one of four tags on the overview:

| Tag | Means |
|---|---|
| **Done** | What the step sets up is in place. |
| **Needed** | The assistant cannot answer anyone without it. Two steps are needed: adding yourself, and connecting an AI model. |
| **Recommended** | Not required, but the install is weaker without it. |
| **Optional** | You can leave it out and nothing breaks. |

A step's own page says the same in its heading line, for example "Step 3 of 7 · about 5 minutes · needed before it can answer".

## The seven steps

| # | Page | Time | Tag | What you need | Done when |
|---|---|---|---|---|---|
| 1 | `/setup/you` | 1 min | Needed | Your first name | An admin is on the family list. |
| 2 | `/setup/password` | 1 min | Recommended | A password of at least 12 characters | An admin can sign in as themselves, or no password is set at all. |
| 3 | `/setup/model` | 5 min | Needed | An account with Anthropic, OpenAI or Google, and a key | A model can answer chat, from the key you saved or from a backup company's. |
| 4 | `/setup/home` | 1 min | Recommended | Your town | A home area is saved and has been found on the map. |
| 5 | `/setup/telegram` | 5 min | Optional | Telegram on your phone | The bot is connected and at least one person on the list has their Telegram linked. |
| 6 | `/setup/family` | 2 min | Optional | The names of the rest of the family | More than one person is on the list. |
| 7 | `/setup/calendar` | 10 min | Optional | Any Google account | A calendar id is saved and its key file is on the server. |

Each form on a step page is the same form as the one on the Settings or Family page that owns the change, and it brings you back to the step afterwards. What a step does, you can undo on that page.

### Add yourself, and your password

Step 1 adds you as an admin. Step 2 gives you a password of your own. From then on the shared password opens nothing, and everybody signs in as themselves, each with a [starting password](/wiki/reference/glossary#starting-password) you make on the Family page. If no admin is on the list yet, step 2 sends you back to step 1, because the first person with their own password has to be an admin.

### Connect an AI model

Pick a company, paste its key, and the key is checked with the company before it is kept, which costs nothing. Saving a key makes that company the one that answers. The step also shows that company's models cheapest first, and a folded "The daily limit" with the [spending limit](/wiki/reference/glossary#spending-limit). Stronger models and the rest are on the [AI model](/wiki/controls/settings/ai-model) page.

### Where home is

Your town decides the forecast, how far away things are and what is on nearby. The time zone, taken from the server, and the units are on the same form. Check the time zone: it decides what "tonight" and "this weekend" mean. See [General settings](/wiki/controls/settings/general).

### Telegram

The step shows only the part you are at:

1. **No token yet.** Six numbered instructions: install Telegram, open BotFather, send `/newbot`, give a name and a username ending in `bot`, then paste the token it sends.
2. **Token refused.** A banner says Telegram did not accept it. Copy it again from BotFather (`/mybots`, your bot, API Token).
3. **Connecting.** The page reloads itself every 4 seconds, at most 45 times, then stops and offers a link to look again.
4. **Not linked yet.** Open the bot on your phone, press Start or send any message, and your message appears on the step. Press **That's me** beside it.
5. **Linked.** You can try it. If the weekend ideas still go to the page's own chat, a button sends them to you on Telegram instead.

Two folds at the bottom add a family group chat (BotFather's `/setprivacy`, Disable, then add the bot to the group) and swap in a different bot.

#### Three ways to link a person's Telegram

| Way | Where | How it works |
|---|---|---|
| **That's me** | The Telegram step | For yourself. You message the bot, it does not know you, and your message appears on the page. One press links that Telegram to the first admin on the list. Only private chats are offered here. |
| **Let them in** | The Family step | For somebody not on the list yet. Send them the bot's `t.me` link. When they press Start they appear under "Waiting to be let in", with the name Telegram gave. Choose a role (Parent is preselected) and press **Let them in**. |
| **A link of their own** | A person's page under Family | For somebody already on the list. **Make a link for [name]** shows a link once. Whoever opens it first and presses Start is linked to that person, so send it to them alone. It works once, for 24 hours, and a new one replaces the last. The bot must be connected first. |

After a link, the assistant answers that person on Telegram. A stranger who writes to the bot is recorded and shows on these pages. See [Telegram: commands and buttons](/wiki/controls/telegram).

### The rest of the family

Add each person with a name and a role: admin, parent or kid. A kid can be added so plans can include them even if they never write to the bot. To let somebody sign in to the page, open them on the Family page and make a starting password. [Family](/wiki/controls/family) covers it.

### Google Calendar

The calendar is optional. Without it, plans stay in FamilyDB. It is the longest step, about ten minutes, and it is done once. It has three cards:

1. **Give FamilyDB its own account at Google.** In Google Cloud, make a project, turn on the Google Calendar API, make a service account (it needs no role), and make a JSON key for it.
2. **Share the family calendar with it.** In Google Calendar, share the calendar with the service account's address, the `client_email` line in the key file, with permission **Make changes to events**. Then copy the calendar's id from *Integrate calendar*.
3. **Paste both here.** Paste the key file's contents and the calendar id, and press **Connect**. FamilyDB tries them on the calendar before it keeps them, and says what is wrong if they fail. The key is saved as a file on the server, so it is not in a [safety backup](/wiki/operations/backup-and-restore) of the database.

## When setup is done, and before

- **Until the two needed steps are done**, an admin who opens Home is sent to `/setup`. Parents and kids are not sent anywhere, but the pill reads "Can't answer yet", and [Status](/wiki/controls/status) names what is missing.
- **After that**, Home carries a card, "Finish setting up", listing each unfinished step with a link, and on a phone a strip saying how many steps are left. Only admins see it. It disappears when every step is done.
- **The overview** says "Let's get FamilyDB ready" until the needed steps are done and "Nearly there" after. Its button reads Start, then "Carry on" with the next unfinished step, then "Everything is set up".
- **The last page**, `/setup/done`, says whether the assistant can answer, suggests a first question to ask, and lists what was left for later.

Everything set here can be changed later on the Settings and Family pages, or by going through setup again.

Developer docs: `src/familydb/web/setup.py` and `web/status.py` (`setup_progress`, `ready_to_answer`, `setup_steps`), the `web/templates/setup/` folder, and `docs/INSTALL.md`, "Follow the setup on the page".
