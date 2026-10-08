# What it does on its own

FamilyDB works without being asked: reminders arrive, ideas get looked up, weekend ideas are posted, and an idle FamilyDB spends nothing. A job that finds nothing to do returns without asking a model.

| What you get | When (default) | Where you change it | Asks a model? |
|---|---|---|---|
| Reminders for things to do | At the reminder's time, checked every minute | [Plans and To do](/wiki/controls/plans-and-tasks) | No |
| Weekend ideas posted to a chat | Thursday at 18:00, only once a chat is chosen in **Weekend ideas go to** (none by default) | [Messages](/wiki/controls/settings/messages#weekend-ideas) | Yes, one question |
| A question the day after a plan: how did it go | 10:00 | [Messages](/wiki/controls/settings/messages#follow-ups-and-notes) | No |
| A heads-up the evening before a plan, only if rain threatens an outdoor plan or the place is closed | hourly 19:00 to 22:00 | [Messages](/wiki/controls/settings/messages#follow-ups-and-notes) | No |
| A nudge about a thing to do kept for a part of the week, when it comes round and the calendar is free | Checked every 15 minutes; each thing once a week, one a day per chat | [Messages](/wiki/controls/settings/messages#follow-ups-and-notes) | No |
| Ideas filled in from the web | Together at 21:00, or as each is added; only while **Look ideas up on the web** is on | [Lookups](/wiki/controls/settings/lookups) | Yes, when an idea is due |

A change to a schedule on the Settings page is picked up within 5 minutes. [The scheduled jobs](/wiki/behavior/jobs) lists every job, and [From message to reply](/wiki/behavior/message-to-reply) follows one message through.
