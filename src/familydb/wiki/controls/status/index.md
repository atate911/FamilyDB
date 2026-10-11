# Status

Status tells a parent or an admin whether the assistant can answer, what it has cost, and what an admin has to fix. Open it first when something seems wrong. It calls no model and makes no network call, and nothing on it updates by itself, so press **Check again** to read it afresh.

Two more pages belong to it: [Models and prices](/wiki/controls/status/models-and-prices), the daily check of what each model company offers and charges, and [Recent activity](/wiki/controls/status/activity), the full history of one message or lookup, for admins.

## Who sees what

With people signed in as themselves, a kid is refused the page. A parent sees all of it except Recent activity and the buttons and links that change a setting; the **Look them up now** button is theirs too. An admin sees everything. Under a shared password, or none, nobody is told apart and everyone who gets in sees everything. The table is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions).

## The pill and the verdict

The pill is the small state in the sidebar and the phone's top bar for parents and admins, and it links here. The banner at the top of Status is worked out from the same signals. The first row that is true wins.

| Pill | When |
|---|---|
| **Can't answer yet** | A step the assistant cannot work without is not done: an admin on the family list, or a model with a key. |
| **Resting** | The daily limit is set and today's estimated spend has reached it. It lasts until midnight in the family's time zone. |
| **Can't answer** | Something stops the family being answered: the model company that answers the chat is out of credit or refusing its key, and no other company with a key may stand in for it. |
| **Writing back** | A reply is being written in your own chat. |
| **Ready** | None of the above. |

The banner says "can't answer right now" for both kinds of Can't answer, with why where one trouble stops her ("can't answer right now: OpenAI refused its key."), "is resting until midnight" for Resting, and "is ready" otherwise; it never says Writing back. A line under it says what to do first (to an admin, where on the settings; to a parent, that an admin can put it right), then what was spent today, what the last 30 days cost, which parts need a look and which are not connected yet. Not connected is a choice, not a fault. While she cannot answer, the same why shows under the box on every page and above the conversation in Chat, with **What to do** opening this page, and on the pill when you point at it. Kids see none of it.

The pill goes by whether the chat can be answered, not by the Needs a look list alone: a company the chat does not use, or one another company with a key may stand in for, is listed under Needs a look and makes the Status tile amber, but the pill stays Ready. A limit row counts only while today's spend is at the limit, so raising the limit lets her answer at once; a limit row from an earlier day never counts, and the first call let through forgets every limit row.

## Needs a look

This lists what only an admin can fix, while it lasts. Each row says since when, how often, and whether admins were told on Telegram. If **Tell admins on Telegram** is on and an admin has a Telegram id, FamilyDB tells them within a minute, and again after 12 hours at the soonest while the trouble goes on. A row leaves when the thing works again, or after seven days without being seen again. Three rows can stop answers (a company's only when it answers the chat and no other company may stand in; the limit's only while today's spend is at it):

| Row | It means | Goes away when | Do this |
|---|---|---|---|
| A company is **out of credit** | The model company said the account has no credit. | The company answers a call. | Add credit with the company. |
| A company **refused its key** | The key is wrong, revoked or expired. | The company answers a call. | Paste a good key under [Keys](/wiki/controls/settings/ai-model#keys). |
| The day's **spending limit was used up** | A call was refused for the limit. | A call is let through, for example after you raise the limit or once the next day begins. | Raise the limit on [Spending](/wiki/controls/settings/spending#the-daily-limit). |

The other rows (Google Calendar, a model company refusing part of a request or refusing requests, models and prices) are listed with what each means on [Messages](/wiki/controls/settings/messages#when-something-needs-fixing). The model and price rows are explained on [Models and prices](/wiki/controls/status/models-and-prices#needs-a-look-rows-about-models).

## The cost figures

Every figure is **an estimate worked out from each call's size and a price table, not your bill.** Set a spending limit with the model company as well. How the estimate is made, and what to turn down, is on [Cost](/wiki/operations/cost).

- **Spent today** is what recorded calls have cost since midnight in the family's time zone, against the daily limit, with a line for a usual day. Admins get **Change the limit**.
- **Last 30 days** shows the cost, the usual day (the average over the days in those 30 that had any calls) and "Questions answered".
- **Where the money went** gives calls and dollars by kind of call, and how much of what was sent came back from the [prompt cache](/wiki/reference/glossary#prompt-cache), which costs less. It also says how many of the messages answered found the start of the request still cached. The cache lasts an hour, so a family that writes a few times a day mostly misses it and pays the whole start of every request; then a shorter start, such as the brief [persona](/wiki/model/vera), saves more than the cache does.

## What came of her suggestions

What the family planned from what she suggested over the last 90 days, read from what is already kept, with no model call. A plan counts for a suggestion when that suggestion offered its idea, or a find of the same name, in the 3 days before the plan was made, whoever asked.

- The first line says how many suggestions there were, how many led to a plan, and how many had picks from the [stronger call](/wiki/behavior/suggestions#choosing-what-to-suggest).
- The table says where each plan stood in its suggestion (picked by the stronger call, offered as good or possible, checked but not shown, found outside the list, or ruled out) and how the family rated it afterwards.
- **Planned though she had ruled it out** names what the family did anyway, with the reason she gave. A reason that keeps coming up is a rule that does not suit this family: a [firm memory](/wiki/model/memory) can change it for them.

**What she found** follows: for each place things come from (the calendars, Ticketmaster, her scouting each evening, and the searches made when somebody asks), how many were found, put forward, saved, planned and passed on as "not for us", and how the outings made of them were rated; then what scouting, filling in and judging cost in the period. Together they say whether scouting earns its budget ([What is on near home](/wiki/controls/settings/happening)).

`familydb debug suggestions [--days N]` prints the same on the [command line](/wiki/operations/command-line).

## How each part is doing

Every row has a tag in words, never color alone, and an admin gets a button beside a row that needs something.

| Row | Looks wrong when | Do this |
|---|---|---|
| **The assistant** (by its name) | **Can't answer** names the needed steps not done, or what stops it and what to do ("Anthropic refused its key. Check Anthropic's key on Settings, AI model, or choose another company there."). **Resting** says the limit is spent. | **Open setup**, or **Put it right** for an admin. See [Setup](/wiki/controls/setup). |
| **Spending** | **Near the limit** from 75% of it, **Limit reached** at 100%, **No limit** when it is 0, which means nothing stops a runaway day. | **Set a limit**, or raise it on [Spending](/wiki/controls/settings/spending). |
| **Sign-in** | **Needs a look** while everybody still shares one password or it is still the one FamilyDB started with. It is fine once an admin signs in as themselves, or when no password is set at all. | The Password step of [Setup](/wiki/controls/setup). |
| **Backup** | **Optional** when no second company with a key can answer. It costs money only when used. | **Add a backup key** on [AI model](/wiki/controls/settings/ai-model#keys). |
| **Telegram** | **Needs a look** when a token is saved but Telegram refused it, it is still connecting, or nobody is linked. **Not connected** with no token. | The Telegram step of Setup. Reminders still appear in the chat without it. |
| **Google Calendar** | **Needs a look** when a calendar is named but its key file is missing. **Not connected**: plans stay inside FamilyDB. | The Calendar step of Setup. |
| **Looking things up** | **Off**: new ideas get no hours, prices or drive times. | **Turn it on** on [Lookups](/wiki/controls/settings/lookups). |

The **Backup** row (the second company, not your database backup) is what each company's **May stand in** on [AI model](/wiki/controls/settings/ai-model#companies) sets up. **Connected to** repeats the facts behind these rows: the calendar and its address, the home position, whether lookups can run, where the weekend ideas go, and how the web page is protected.

## Waiting and Worth a look

**Waiting** counts ideas by lookup state and says when they are looked up, by default together in the evening. Below that are the next five ideas due and **Messages that did not go through**: the five most recent messages that failed, with their text, the error, and a note: "N tries, will try again" while retries remain, or "given up on after N tries; the words above were not answered, so send them again" once none do. A message stays listed until a retry answers it, so a given-up one is the person's cue to send the words again. Parents see that text, from any chat; Recent activity is admin-only. The Troubleshooting settings page lists the same messages and tags a given-up one **Given up**; the retry numbers are on [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered).

**Worth a look** lists the six most recent calls in the last 30 days that ended oddly, and the six most recent lookups that failed.

| Item | It means | Do this |
|---|---|---|
| A call ended with **max_tokens** | The answer was cut short at the output limit. | Raise **Longest answer (tokens)** on [Spending](/wiki/controls/settings/spending#what-one-message-may-use). |
| A call ended with **refusal** | The model declined to answer. | Find that time under Recent activity and open it. |
| A **lookup that failed** | The lookup was given up on. The note says why. | Open the idea and press **Look it up again**. |

## When something is wrong

Read the pill and the banner, then **Needs a look**, then any amber or red row under **How each part is doing**. For one message that went wrong, open it under Recent activity. For a message that never got a reply, see [Troubleshooting](/wiki/operations/troubleshooting#a-message-got-no-reply). What FamilyDB sends without being asked is listed on [Messages](/wiki/controls/settings/messages), not here.
