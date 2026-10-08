# Known limits

FamilyDB does the following today. Where a row has a workaround, use it.

## Privacy and kids

### Chat tools are not checked against a role

In chat, the assistant can call every tool for a kid. Only `look_up_now`, changing a thing to do that is not their own, adding a wish and turning a wish away check who is asking; adding or changing an idea, a calendar event, a memory, an outcome and a thing to do do not. What holds the line is the assistant's judgment and the kid's daily limits, not a permission check; see [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) and [What a sign-in guards](/wiki/security/model#what-a-sign-in-guards).

### Telegram commands show presents

`/today` and `/week` list calendar entries and plans as they are, including a plan made from a present, with its title. The web page leaves such plans out for the people the present is kept from, so a kid or the grown-up it is for who types `/today` can see what the page hides. If that matters, wait until the day to make a plan from a present; see [Presents](/wiki/model/ideas-and-places#presents).

### The to-rate list shows presents

The count and list of plans waiting for a rating include a plan made from a present. Only parents and admins see them, so a kid never does, but the grown-up the present is for can. Nothing hides the plan between its day and its rating.

### A place name outlives the coordinates

FamilyDB deletes a shared position on its own schedule, but the reply that confirmed it, which names the place, stays in the message history and the activity log. The coordinates go; the town or street name does not. See [Shared location](/wiki/model/location).

## Family and passwords

### A Telegram link clears birthday and gender

Using a one-time Telegram link clears the person's birthday and gender. Enter both again on [Family](/wiki/controls/family#add-or-change-somebody) after the link is used; until you do, a kid's age is unknown to the assistant.

### Knocks and links are cleared late

An expired link stays in the database until the next link is made or used, and an old knock until the next stranger writes. A knock older than 30 days can still be listed on Family. Neither lets anyone in; see [Link a Telegram](/wiki/controls/family#link-a-telegram).

### A Not OK wish has no buttons on the page

A request the assistant flagged as Not OK shows a parent no **Yes!** or **Not this time** buttons on the page. Answer it from the Telegram message the parents were sent; see [Answer a wish as a parent](/wiki/controls/wish-lists#answer-a-wish-as-a-parent).

## Messages and Status

### A reminder made on the page does not reach Telegram

A reminder made with the page's forms or in its Chat is delivered to the web page only, where it shows on To do. To get it on Telegram, ask for it in Telegram; see [How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered).

### Plans made on the page get no follow-up

A plan made with the page's forms belongs to no chat, so the day-after question and the evening-before check have nowhere to go. Make the plan in Telegram if you want either.

### Reset on retry-failed re-arms every message

`familydb db retry-failed --reset` gives every failed message new tries, including one that was given up on purpose. Use it only when you want all of them asked again.

### A skipped evening-before check may never be retried

If nothing can send to the plan's chat, or the calendar cannot be read, the check tries again in each hourly run until 22:00, for a plan of tomorrow or a plan of today that has not begun. A plan that has begun by the next run is not checked, so a daytime plan whose evening was missed gets no heads-up. A restart after the check hour runs the check once more. See [Messages](/wiki/controls/settings/messages#follow-ups-and-notes).

### An unshared calendar raises an alert only when one event is looked up

If the calendar is no longer shared with the service account or was deleted, the **Google Calendar is no longer showing the bot its calendar** row and the Telegram message come only when FamilyDB looks up a single plan's event: moving or canceling a plan, or bringing a plan in line with its event. Listing the calendar or syncing it fails as `Google Calendar error 404` with no alert. A read-only calendar or a switched-off Calendar API fails as `Google Calendar error 403` with none either. See [When Google says no later](/wiki/boundaries/google-calendar#when-google-says-no-later).

## Server

### The doctor does not print what it fixed

`familydb doctor --fix` puts right what it safely can, then prints a fresh report without saying what it changed. Run `familydb doctor` once more to see the result; see [Diagnostics](/wiki/operations/diagnostics#running-the-doctor).

### An upgrade does not rewrite the service file

`maintain.sh upgrade` leaves the systemd service file as it was. After a release that changes the unit, copy the new one from `deploy/` by hand; see [The server](/wiki/operations/host#the-service).

### The web page can fail to start while the assistant runs

If the web page cannot start (the port is taken, or no password is set), FamilyDB logs the reason and keeps answering on Telegram. Read the log with `maintain.sh logs`; see [Logs](/wiki/operations/diagnostics#logs).
