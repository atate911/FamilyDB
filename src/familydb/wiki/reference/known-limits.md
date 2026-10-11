# Known limits

FamilyDB does the following today. Where a row has a workaround, use it.

## Privacy and kids

### Chat tools check only some roles

In chat, a kid can add an idea, remember something and keep their own wishes and things to do; the family decided that. Code refuses a kid in chat the changes only a parent makes: editing an idea, saying how a plan went, and making, moving or cancelling a plan or calendar event. The assistant is told nothing was changed and to suggest asking a parent. The other tools still do not check who asks, so the assistant's judgment and the kids' daily limits are the brakes on those. See [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) and [What a sign-in guards](/wiki/security/model#what-a-sign-in-guards).

### A forgotten place can still show in kept texts

When a shared position is forgotten, FamilyDB drops its place name from the confirmation and from the kept model texts, tool calls and suggestions. Coordinates inside kept model texts stay until those texts expire, and so do words of the assistant or the family that name the place. See [Shared location](/wiki/model/location#the-place-name-goes-with-the-position).

## Messages and Status

### A reminder made on the page does not reach Telegram

A reminder made with the page's forms or in its Chat is delivered to the web page only, where it shows on To do. To get it on Telegram, ask for it in Telegram; see [How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered).

### Plans made on the page get no follow-up

A plan made with the page's forms belongs to no chat, so the day-after question and the evening-before check have nowhere to go. Make the plan in Telegram if you want either.

### A skipped evening-before check may never be retried

If nothing can send to the plan's chat, or the calendar cannot be read, the check tries again in each hourly run until 22:00, for a plan of tomorrow or a plan of today that has not begun. A plan that has begun by the next run is not checked, so a daytime plan whose evening was missed gets no heads-up. A restart after the check hour runs the check once more. See [Messages](/wiki/controls/settings/messages#follow-ups-and-notes).

### An unshared calendar raises an alert only when one event is looked up

If the calendar is no longer shared with the service account or was deleted, the **Google Calendar is no longer showing the bot its calendar** row and the Telegram message come only when FamilyDB looks up a single plan's event: moving or canceling a plan, or bringing a plan in line with its event. Listing the calendar or syncing it fails as `Google Calendar error 404` with no alert. A read-only calendar or a switched-off Calendar API fails as `Google Calendar error 403` with none either. See [When Google says no later](/wiki/boundaries/google-calendar#when-google-says-no-later).

## Server

### The web page can fail to start while the assistant runs

If the web page cannot start (the port is taken, or no password is set), FamilyDB logs the reason and keeps answering on Telegram. Read the log with `maintain.sh logs`; see [Logs](/wiki/operations/diagnostics#logs).
