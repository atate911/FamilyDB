# Known limits

FamilyDB does the following today. Where a row has a workaround, use it.

## Privacy and kids

### Chat tools are not checked against a role

In chat, the assistant can call every tool for a kid. Only `look_up_now`, changing a thing to do that is not their own, adding a wish and turning a wish away check who is asking; adding or changing an idea, a calendar event, a memory, an outcome and a thing to do do not. What holds the line is the assistant's judgment and the kid's daily limits, not a permission check; see [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) and [What a sign-in guards](/wiki/security/model#what-a-sign-in-guards).

### Telegram commands show presents

`/today` and `/week` list calendar entries and plans as they are, including a plan made from a present, with its title. The web page leaves such plans out for the people the present is kept from, so a kid or the grown-up it is for who types `/today` can see what the page hides. If that matters, wait until the day to make a plan from a present; see [Presents](/wiki/model/ideas-and-places#presents).

### The to-rate list shows presents

The count and list of plans waiting for a rating include a plan made from a present. Only parents and admins see them, so a kid never does, but the grown-up the present is for can. Nothing hides the plan between its day and its rating.

### A forgotten place can still show in kept texts

When a shared position is forgotten, FamilyDB drops its place name from the confirmation and from the kept model texts, tool calls and suggestions. Coordinates inside kept model texts stay until those texts expire, and so do words of the assistant or the family that name the place. See [Shared location](/wiki/model/location#the-place-name-goes-with-the-position).

## Messages and Status

### Status says will try again after the last try

After a message has used all its tries, the Status row can still read "will try again". Compare the row's number of tries with **Retries before giving up** (`retry_max_attempts`) on [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered); when they match, no more tries are coming.

### A reminder made on the page does not reach Telegram

A reminder made with the page's forms or in its Chat is delivered to the web page only, where it shows on To do. To get it on Telegram, ask for it in Telegram; see [How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered).

### Plans made on the page get no follow-up

A plan made with the page's forms belongs to no chat, so the day-after question and the evening-before check have nowhere to go. Make the plan in Telegram if you want either.

### A skipped evening-before check is not retried

If the calendar cannot be read at the check time, FamilyDB sends no heads-up for that plan, and the next run looks at the following day. A restart after the check time runs the check once. See [Messages](/wiki/controls/settings/messages#follow-ups-and-notes).

### The day's limit keeps the pill red after midnight

When the daily limit is reached, the next day's calls do not clear that alert. The pill can read "Can't answer", and Status keeps a Needs a look row, for up to 7 days after the limit was last reached, even while messages are answered. The row leaves by itself; see [Status](/wiki/controls/status#the-pill-and-the-verdict).

### An unshared calendar raises no alert

If the family calendar is not shared with the service account, or the Calendar API is switched off in Google Cloud, Google answers with an error that the assistant reports in chat. No Needs a look row appears and no admin is told on Telegram. Check the sharing under [Google Calendar](/wiki/controls/settings/connections#google-calendar).

## Server

### An upgrade does not rewrite the service file

`maintain.sh upgrade` leaves the systemd service file as it was. After a release that changes the unit, copy the new one from `deploy/` by hand; see [The server](/wiki/operations/host#the-service).

### The web page can fail to start while the assistant runs

If the web page cannot start (the port is taken, or no password is set), FamilyDB logs the reason and keeps answering on Telegram. Read the log with `maintain.sh logs`; see [Logs](/wiki/operations/diagnostics#logs).
