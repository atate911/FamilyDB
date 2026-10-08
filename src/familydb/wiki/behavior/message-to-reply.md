# From message to reply

A message is stored the moment it arrives, answered while FamilyDB holds a claim on it, and its reply is stored before it is sent, so a restart or a failed send loses nothing. The one cost is that a reply can arrive twice. The steps follow in order, then what each failure looks like and what a restart does. [The Telegram loop](/wiki/behavior/telegram-loop) covers the Telegram side, and [The scheduled jobs](/wiki/behavior/jobs) covers the jobs.

## A message, from arrival to reply

1. It arrives. A Telegram update carries an id, and one already stored is ignored. On the web page the message needs words, at most 4,000 characters, a sender on the family list and no turn already running in that chat. Otherwise the page says so in place and stores nothing.
2. On Telegram the sender is checked. Someone not on the [family list](/wiki/reference/glossary#family-list) gets one line with their Telegram id and is recorded as a [knock](/wiki/reference/glossary#knock) (never the text). Nothing is stored and no model is asked ([Who may message the bot](/wiki/model/family-and-roles#who-may-message-the-bot)).
3. It is stored as `received`, before anything else happens.
4. On Telegram, text waits for the gather pause. The pause is 4 seconds by default (`gather_seconds`). The retry job leaves the message alone for the pause plus 5 minutes. The newest message from that person in that chat then answers, with earlier ones still waiting folded into it: one turn, one reply. Voice notes, photos and the web page do not wait.
5. It is claimed. Turns in one chat run one at a time, and the message takes a [lease](/wiki/reference/glossary#lease): a claim on the message that runs out if the program stops, so nothing is answered twice. The lease lasts 5 minutes and is renewed every 30 seconds while the turn runs. If another worker holds it, this one stops quietly.
6. Checks that ask no model, before anything is heard. A message already answered or given up is dropped. One from someone since switched off is given up with no reply. A kid past their daily message count (off by default) is told so by code ([Spending](/wiki/controls/settings/spending#the-daily-limit)).
7. A voice note or photo is read. See [Voice notes and photos](/wiki/behavior/message-to-reply#voice-notes-and-photos). The words replace the mark and the message goes on as ordinary text.
8. More checks that ask no model. With no model key the message is given up and the sender is told. A kid whose daily share of the spending limit is used up is told so.
9. The prompt is built. The cached front is the character, the instructions, the family list and the idea list. Then come the chat's recent messages (by default up to 20 from the last 6 hours) and the current turn, never cached: when the message arrived, who reads the reply in a shared chat, a recent [shared location](/wiki/model/location), [memories](/wiki/model/memory) chosen by code, and any reminder waiting to ride along.
10. The limit is checked before each call. FamilyDB reserves the call's estimated cost against the day's [spending limit](/wiki/reference/glossary#spending-limit). Past the limit, the message is given up, and the first try (not a retry) tells the sender. If the turn had already saved something, code reports what, with no further call.
11. The tool loop runs. The model answers or asks for tools, code runs and logs each one, and the model is asked again, up to 8 calls by default. If the first call fails because the model company is busy, unreachable, out of credit, refusing the key or missing the model, and a second company has a key, that company is asked instead ([A second company](/wiki/boundaries/model-companies#a-second-company)). After a tool has run there is no switch, because starting again would repeat its writes.
12. The reply is stored, with the message marked processed, in one transaction. A reminder waiting for this chat rides along ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)).
13. It is sent, then marked delivered. On the web page the reply is visible once stored, and sending only marks it delivered. If a send fails, the reply stays stored and the retry job sends every unsent reply each time it runs, with no model call. Telegram cannot tell FamilyDB whether a send arrived, so a reply is sometimes sent twice, and so are the early parts of a long reply that failed partway.

## Voice notes and photos

A voice note or photo is stored first as a mark such as `(voice note, 0:42, not heard)`, and a stranger's is never downloaded. Under the message's lease, FamilyDB checks that the feature is on and that a company able to hear or see has a key, fetches the file, and has it heard or looked at in a call of its own, with the spending limit checked first. The words replace the mark and the message goes on as an ordinary one.

If hearing or looking fails, the message is given up with a line asking for it again or typed. The recording and picture are never kept, so none is retried. The size limits and the group rules are in [The Telegram loop](/wiki/behavior/telegram-loop#the-updates-it-handles), and the companies and settings are on [Model companies](/wiki/boundaries/model-companies#voice-notes-and-photos).

## A change made on the page

A parent opens an idea, changes its title and presses Save.

1. The browser posts to the web page. FamilyDB asks who is signed in and whether their role may change things, then checks the form's Origin and CSRF token.
2. The page makes the tool call as that person, with the revision of the idea the form was drawn from.
3. The tool compares the revision inside its own transaction, so somebody else's newer edit is not overwritten, and writes the change.
4. The page shows the result and redirects. No model was asked, and neither the pipeline nor the gateway was involved.

## What a failure looks like

A message *failed* when its turn did not finish. The retry job tries it again until it has used its retries. A message is *given up* when nothing more will be tried: trying again cannot fix the cause, or the sender no longer qualifies ([Failed and given up](/wiki/reference/glossary#failed-and-given-up)).

| What went wrong | What the family sees | What happens next |
|---|---|---|
| The model company is busy or unreachable, or something unexpected broke | A reply saying the message was saved and will be retried | The retry job tries every 5 minutes, without telling the family again. After the last retry, nothing more is said on Telegram |
| A refusal that retrying will not fix (a key, credit, a refused request) | A reply saying the model cannot be reached and an admin should check the logs | Given up. Status names the cause where FamilyDB can tell |
| The day's limit, or no key | A line naming the limit, or saying no model is set up | Given up. Told on the first try, silent on a retry |
| Out of steps | A reply saying the assistant could not finish within the steps it is allowed | Given up, and told even on a retry |

[A message got no reply](/wiki/operations/troubleshooting#a-message-got-no-reply) quotes each reply and gives the fix.

A message gets its first try plus up to 3 retries (the default, set by **Retries before giving up** on [Messages](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)). After the last retry, Telegram hears nothing more and the chat page says the last message was not answered. Status lists it under **Messages that did not go through** as given up on after its tries, with its words to send again; the retry job does not try it again.

Status lists only failed messages, the newest 10. A message cut off by a restart, or still in the gather pause, is not yet failed, so it appears only on the chat page and [Recent activity](/wiki/controls/status/activity) until the retry job takes it.

With Telegram disconnected, the retry job skips Telegram messages without counting an attempt, and the log says `not retrying message N: no sender for telegram here`. `familydb db retry-failed --reset` (run as in [The command line](/wiki/operations/command-line#how-to-run-it)) gives failed messages with no tries left new tries. A message given up on purpose, such as one from a person taken off or a kid over the day's limit, stays given up.

## What survives a restart

| In the middle of | What happens |
|---|---|
| A message, before it is stored | Nothing is kept. The sender sees no answer and sends it again |
| A message, waiting out the gather pause | The retry job leaves it alone for the pause plus 5 minutes, then answers each waiting message in turn, not together |
| A message, in the turn | The lease lapses about 5 minutes after its last renewal, then the next retry job (up to 5 more minutes by default) answers it, told which writes already happened. A model call in flight is never recorded; its reserve counts toward the limit for up to 30 minutes, then is forgotten |
| A reply, stored but not sent | The retry job sends it. If it was sent but not marked, it goes twice; the model is not asked again |
| A voice note or photo, before it is read | The retry job gives it up and says it could not be read, since the recording is gone. Sending it again works. After it is read, it is retried like any message |
| A reminder, due during downtime | The next reminders job sends it, marked late. A repeating one resumes at its next time after now, with no flood |
| A reminder or a wish for the parents, queued but not sent | The retry job sends it. A reminder waiting for a conversation is in memory only, so it is simply sent |

Developer docs: src/familydb/pipeline.py, src/familydb/delivery.py, src/familydb/channels/web.py, src/familydb/web/edits.py; docs/DESIGN.md, "Message pipeline"; docs/AI_CALLS.md, "The one idea".
