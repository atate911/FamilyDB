# Setup

Setup walks a new install through the seven things it needs, one short web page each, and shows how far you have got. Only an admin can open it, at `/setup`. Once people sign in as themselves, a parent or a kid who tries is told that an admin does it, and which admins to ask. [Install and first run](/wiki/operations/install) covers what comes before it, on the server.

You can skip any step and return; the pages pick up wherever things stand.

## How progress is read

**Nothing records that a step is done.** Each time you open a setup page, it checks whether what the step sets up is there, and reads the result. It makes no network call and no model call. So a step goes back to not done if you undo it: remove the Telegram token and the Telegram step is open again. Skipping a step only moves you to the next page.

Each step has one of four tags on the overview:

| Tag | Means |
|---|---|
| **Done** | What the step sets up is in place. |
| **Needed** | The assistant cannot answer anyone without it. Two steps are needed: adding yourself, and connecting an AI model. |
| **Recommended** | Not required, but the install is weaker without it. |
| **Optional** | You can leave it out and nothing breaks. |

## The seven steps

| # | Page | Time | Tag | What you need | Done when |
|---|---|---|---|---|---|
| 1 | `/setup/you` | 1 min | Needed | Your first name | An admin is on the family list. |
| 2 | `/setup/password` | 1 min | Recommended | A password of at least 12 characters | An admin can sign in as themselves, or no password is set at all. |
| 3 | `/setup/model` | 5 min | Needed | An account with Anthropic, OpenAI or Google, and a key | A model can answer chat: from a key saved here, one set in the server's environment, or the second company's. |
| 4 | `/setup/home` | 1 min | Recommended | Your town | A home area is saved and has been found on the map. |
| 5 | `/setup/telegram` | 5 min | Optional | Telegram on your phone | A bot token is saved and not refused, and at least one person on the list has their Telegram linked. The step page itself looks at the admin who was added first. |
| 6 | `/setup/family` | 2 min | Optional | The names of the rest of the family | More than one person is on the list. |
| 7 | `/setup/calendar` | 10 min | Optional | Any Google account | A calendar id is saved and its key file is on the server. |

Each form on a step page is the one on the Settings or Family screen that owns the change, and it brings you back to the step.

### Add yourself, and your password

Step 1 adds you as an admin. Step 2 gives you a password of your own. From then on the shared password opens nothing, and everybody signs in as themselves, each with a [starting password](/wiki/reference/glossary#starting-password) you make on Family. If no admin is on the list yet, step 2 sends you back to step 1, because the first person with their own password has to be an admin.

### Connect an AI model

Pick a model company and paste its key. The company checks the key at no cost, and a wrong key is refused. Saving a key makes that company the one that answers. The step also lists that company's models cheapest first, and shows the [spending limit](/wiki/reference/glossary#spending-limit) in a fold. A second company (the **Backup** row on Status, not your database backup), stronger models and the rest are on [AI model](/wiki/controls/settings/ai-model); how keys are kept is under [Keys](/wiki/controls/settings/ai-model#keys).

### Where home is

Your town decides the forecast and what is on nearby. The time zone, taken from the server, and the units are on the same form. Check the time zone, because it decides what "tonight" means: see [General](/wiki/controls/settings/general#where-home-is).

### Telegram

The step shows the part you are at: no token yet, token refused, connecting, connected but nobody on the list yet, not linked yet, or linked. It reloads itself every 4 seconds, at most 45 times, while it waits. Making the Telegram bot and pasting its token are on [Connections](/wiki/controls/settings/connections#telegram).

**Give the first admin a Telegram id.** Without one, nothing that needs a look reaches you on Telegram; it shows only on Status.

**That's me.** Open the Telegram bot on your phone and press Start or send any message. It does not know you, so your message appears on the step; press **That's me** beside it to link that Telegram to the admin who was added first. Only private chats are offered here. To link anybody else, see [Link a Telegram](/wiki/controls/family#link-a-telegram).

### The rest of the family

Add each person with a name and a role: admin, parent or kid. A kid can be added so plans can include them even if they never write to the bot. To let somebody sign in to the web page, open them on Family and make a starting password; [Family](/wiki/controls/family) covers it.

### Google Calendar

The calendar is optional; without it, plans stay in FamilyDB. It is the longest step, about 10 minutes, and you do it once:

- Give FamilyDB its own [service account](/wiki/reference/glossary#service-account) at Google and make a JSON key for it.
- Share the family calendar with that account, with permission **Make changes to events**.
- Paste the key file and the calendar id, and press **Connect**.

The numbered steps are on [Connections](/wiki/controls/settings/connections#google-calendar). The key is saved as a file on the server, so a [backup](/wiki/operations/backup-and-restore) of the database does not hold it.

## When setup is done, and before

- **Until the two needed steps are done**, an admin who opens Now is sent to `/setup`. So is anybody, while the family still shares one password or has none, because nobody is known to be an admin yet. A parent signed in as themselves is not sent anywhere, but the pill reads "Can't answer yet" and [Status](/wiki/controls/status) names what is missing. Kids see no pill.
- **After that**, Now carries "Finish setting up", listing each unfinished step with a link. Only admins see it, and it disappears when every step is done.
- **The overview** says "Let's get FamilyDB ready" until the needed steps are done and "Nearly there" after. Its button reads Start, then "Carry on" with the next unfinished step, then "Everything is set up".
- **The last page**, `/setup/done`, says whether the assistant can answer, suggests a first question, and lists what was left for later.

Everything set here can be changed later on Settings and Family, or by going through setup again.

### The first week

1. Send the assistant a message, on Telegram or in Chat.
2. Try `/today` on Telegram.
3. Add an idea, in chat or on Ideas.
4. Check [Status](/wiki/controls/status) after 3 days.
