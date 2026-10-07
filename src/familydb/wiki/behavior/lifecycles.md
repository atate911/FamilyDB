# Lifecycles

This page follows five things from start to finish (a message, a voice note, a photo, a reminder and a kid's wish), and says where each step can fail and what the family or an admin then sees. The rule behind all five is that something is stored before the next step runs, so a restart rarely loses anything. The last section says what each restart does.

The quoted lines are the assistant's wording as shipped. The family can reword them on [Personality](/wiki/controls/settings/personality), and where a kid reads, a line about how the bot works is replaced by a plain one ("Ask me again in a little while!"). The Telegram side is in [The Telegram loop](/wiki/behavior/telegram-loop), and each job's schedule is in [Jobs](/wiki/behavior/jobs).

## A message, from arrival to reply

1. **It arrives.** A Telegram update carries an id, and one already stored is ignored, so a restart never answers it twice. On the page, the message must have words, be at most 4,000 characters, come from someone on the family list, and find no turn running in that chat. Otherwise the page says so in place and stores nothing ("Still thinking about the last message. Give it a moment."). A turn on the page runs on its own thread, so the form returns at once.
2. **The sender is checked.** Someone not on the [family list](/wiki/reference/glossary#family-list) gets one line with their Telegram id and is recorded as a knock (name, id and time, never the text). Nothing is stored and no model is asked.
3. **It is stored** with the status `received`, before anything else happens to it.
4. **On Telegram, text waits a moment.** With the default pause of 4 seconds, the message is held from the retry job, and after the pause the newest message from that person in that chat answers: earlier ones still waiting are folded into it, answered in one turn and one reply. A newer message from the same person means this one yields to it. Voice notes, photos and the page are not paused.
5. **One turn at a time, under a lease.** Turns in one chat run one after another in the process. The message is then claimed with a [lease](/wiki/reference/glossary#lease): five minutes, renewed every 30 seconds while the turn runs. If another worker holds it, this one stops quietly.
6. **Checks that ask no model.** In order: a message already answered or given up is dropped; one from someone since switched off is given up with no reply; a kid at their daily message count ([Spending](/wiki/controls/settings/spending); off by default) is given up and told so by code; with no key for any model company the message is given up with "I can't answer yet"; a kid whose dollar share of the day is used up is told to come back tomorrow.
7. **The prompt is built.** The cached front holds the persona's character, the product's instructions, the family list and the idea list. After it come the chat's recent messages (by default up to 20 from the last 6 hours, within about 1,500 tokens) and the current turn, which is never cached: the time the message arrived, who reads the reply in a shared chat, a shared location under three hours old, a kid's age and wish topics, [memories](/wiki/model/memory) chosen by code, and any reminder or note waiting to ride along. Every tool is declared on every turn.
8. **The spending limit is checked before each call.** The call's estimated cost is held against the day's [limit](/wiki/reference/glossary#spending-limit) and given back when the call is recorded. Past the limit, the message is given up and told the limit. If the turn had already saved something, code reports what, with no further call.
9. **The tool loop runs.** The model answers or asks for tools, code runs them and logs each one against the message, and the model is asked again, up to 8 calls by default. A turn that only remembered something can end with the reply that call carried. If the first call fails in a way worth moving for (busy, unreachable, a key or credit trouble) and a second model company has a key, that company is asked instead. After any tool has run there is no switch, because it would repeat a write. Out of steps, the message is given up and told so, naming what was saved if anything was.
10. **The reply is stored**, with the message marked processed and the list of what the turn did, in one transaction. Any reminder or note held for this chat rides along, so one message carries both.
11. **It is sent, then marked delivered.** On Telegram the answer replies to the person's message while "typing…" shows. On the page the reply is visible the moment it is stored, and sending only marks it delivered.
12. **If the send fails,** the reply stays stored and the retry job sends every unsent reply each time it runs, with no model call. A send Telegram accepted whose answer was lost can arrive twice. A reply sent in several parts that fails partway is sent again in full.

### What a failure looks like

| What went wrong | What the family sees | What happens next |
|---|---|---|
| The model company is busy, unreachable or something unexpected broke | "Saved your message, but I couldn't process it right now. I'll retry later." | The retry job tries every 5 minutes, 3 times by default. Retries are silent, so the answer simply arrives when one works. After the last, nothing more is said on Telegram; the message stays under "Messages that did not go through" on [Status](/wiki/controls/status), and the page says it is out of tries |
| The company refused for a reason retrying will not fix | "Saved your message, but I can't reach the model at the moment. An admin needs to check the logs." | Given up. Status usually names the cause |
| The day's limit, or no key | The limit line, or "I can't answer yet" | Given up, not retried |
| Out of steps | "I couldn't finish that within the steps I'm allowed" | Given up, and told even on a retry |
| The model refused the request | "Sorry, I couldn't process that message." | Stored as the reply; nothing to retry |

A retry is its own kind of call. It resolves "tomorrow" from when the message arrived, leaves out the bot's earlier notices about it, and is told which writes the first try already made so it does not repeat them. A process not connected to Telegram does not retry a Telegram message. What to do about each row is in [Troubleshooting](/wiki/operations/troubleshooting).

## A voice note

Voice notes come only from Telegram. The page has dictation, which is the browser's own and sends words, not a recording.

1. **It arrives.** In a group, it is ignored only when "answer only when mentioned" is on and the note is not addressed to the bot. The bot builds a way to fetch the recording but does not download it.
2. **The sender is checked,** as for a message. A stranger's note is never downloaded.
3. **It is stored as a mark** such as "(voice note, 0:42, not heard)". Voice notes are not paused, but they take the same one-turn-at-a-time rule, the lease and the kid's count as a message.
4. **It is checked.** Voice notes must be on, a company that can hear must have a key (OpenAI or Gemini; Claude cannot hear), and the note must be within the longest setting (5 minutes by default) and 20 MB. Then the recording is fetched, with a 60 second timeout.
5. **It is heard.** The limit is checked and the cost held, as for any call. The chosen company is asked, then another that can hear if the fallback is on. The call is recorded as "listening to voice notes" and counts toward the day. The names of the family, the assistant and the home area go along so they are spelled the family's way.
6. **The words replace the mark,** after "(voice note) ", with any caption after them. From here it is an ordinary message: history, retries and an idea's original thought all read the words.
7. The message continues at the prompt in the first sequence.

Each failure in steps 4 and 5 is given up with a line asking for it again or typed: "I don't listen to voice notes here", "I can't hear voice notes yet", "That voice note is longer than the 5 minutes I listen to", "Sorry, I couldn't make out that voice note", or the limit line. The recording is never kept, so none is retried. Settings are on [AI model](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## A photo

1. **It arrives** as a photo, or an image file (JPEG, PNG or WebP). In a group it is handled only when addressed to the bot, whatever the mention setting. An album is collected for 1.5 seconds and becomes one message, with the first caption.
2. **The sender is checked,** and a stranger's photo is never downloaded.
3. **It is stored as a mark:** "(photo, not looked at)", or "(3 photos, not looked at)".
4. **It is checked.** With photos off, a caption is answered anyway, marked "(with a photo, not seen)", and a photo with no caption gets "I don't look at photos here". A company with a key must be able to look. Each picture is fetched at the largest size within 1,600 pixels on its long side and must be at most 3.9 MB.
5. **Each photo is looked at in a call of its own,** by the lookup model, with the limit checked each time. It writes down what the picture is and every name, date, time, place and price in it, guessing nothing. Only the first four of an album are looked at, and the rest are noted as not looked at.
6. **The words replace the mark,** after "(photo) " (or "(photo 2 of 3) " for an album), with the caption after them. A photo that failed in an album is marked "not seen", and the message goes on as long as one was read. If none was, or the limit was reached partway, it is given up with a line.
7. The message continues at the prompt in the first sequence.

Pictures are never kept. A photo given up is not retried: the lines are "That picture is too large for me to look at", "Sorry, I couldn't look at that photo" and the limit line.

## A reminder

1. **It is created** with `add_task` and a `remind_at` time in the future, by the assistant in chat or by the To do page's form, with no model call on the page. A time in the past, or one the clocks skip, is refused to whoever asked. The reminder goes back to the chat it was asked in, and the page's Chat for one asked on the page. The task and its reminder are saved in one transaction, so a retried request never adds it twice.
2. **It waits.** No model is involved at any point in a reminder.
3. **The minute job finds it due.** Every minute, in one transaction, it picks up due reminders of open things to do (up to 100 at a time). For each it chooses where to send it (a reminder for someone's own thing to do goes to their own chat instead of a group, when [Connections](/wiki/controls/settings/connections#in-a-telegram-group) allows it), stores the message with its buttons, and attaches it to the reminder. A repeating task gets its next reminder in the same transaction. One more than ten minutes late says when it was due.
4. **It is handed over.** If someone is talking in that chat (a turn running, or a message in the last 5 minutes), the reminder is held up to 2 minutes so the next reply carries it. Otherwise it is sent at once. A held one nobody replies to is sent by the minute job.
5. **It is sent** like any reply. On Telegram it carries **Done**, **In an hour** and **Tomorrow**. On the page it appears in Chat. A failed send is the retry job's, and the minute job never queues it twice.
6. **A tap does the work, with no model.** It must come from someone on the family list, and a kid may tap only their own things to do. Done marks it done. The other two set a new reminder an hour or 24 hours after the tap, replacing the old one. The tap is stored as a message, the reminder gains a note saying who did what, and the buttons go. A change is refused while a reminder is being sent, and the tap says it didn't go through.
7. **Done on a repeating task records this time round** and keeps it going. One counted from its schedule already has its next reminder, and one counted from when last done gets its next at that day plus the interval, at the first reminder's hour. Done on a task that does not repeat cancels its reminders, queued ones included. A snooze on a repeating task moves only this time round.

Reminders go only while `familydb run` is running. The schedule is in [Jobs](/wiki/behavior/jobs), and the rules for repeating are on [Plans and things to do](/wiki/controls/plans-and-tasks).

## A kid's wish

1. **The kid asks** in the box on the page, or on Telegram. It is an ordinary message, so every step of the first sequence applies, including the kid's count and dollar share.
2. **The model is told who is asking:** their age, whether the kid is male or female if an admin set it, never the birthday, their wish topics only where nobody else reads the reply, and sometimes a note to nudge their wording. Code decides all of that.
3. **The model sorts it** and calls a tool. `add_wish` answers added, duplicate, locked (with the date they may ask again), too many today, or list full. `turn_away` keeps a house rule, a complaint about a sibling or an inappropriate request for the parents. Something the family could do together becomes an idea or a thing to do. The rules and limits are on [Wish lists](/wiki/controls/wish-lists).
4. **The kid is answered at once,** briefly and at their age.
5. **Parents are told in two cases.** An inappropriate request is sent straight after the turn to every parent or admin with a Telegram id. A kid's **Ask a parent** press (offered once per ask, on the page) sends the same. Each message carries **Yes!**, **Not this time** and **Later**. Everything else waits on the page under Kids' lists. A parent with no Telegram id gets nothing on Telegram, so the page's to decide badge is where they see it.
6. **A parent answers** on the page or with a tap. A tap works only for a parent, and Later only shows a pop-up and leaves the buttons. Yes! and Not this time run `update_wish` as the person who tapped, with no model call. The tap is stored, a note says who did what, and the buttons go from that message. Another parent's copy then says it is already dealt with.
7. **The kid is told** in their own conversation on the page, in the assistant's words with any note the parent wrote. A no adds the day they may ask again, from the lockout ladder on [Wish lists](/wiki/controls/wish-lists).

## What survives a restart

| In the middle of | What is left | What happens |
|---|---|---|
| A message, before it is stored | Nothing | Telegram offers the update again, and the page shows no message |
| A message, waiting out the pause | The stored message, held | The hold lapses after the pause plus 5 minutes, and the retry job answers each waiting message in turn, not together |
| A message, in the turn | The stored message, its lease, any writes the tools made | The lease lapses within 5 minutes and the retry job answers it, told which writes already happened. A model call in flight is not recorded, so the day's estimate misses it |
| A reply, stored but not sent | The stored reply | The retry job sends it. If it was sent but not marked, it goes twice, and the model is not asked again |
| A voice note or photo, before it is read | The mark | The retry job gives it up and says it could not be read, since the recording is gone. Asking again, or typing it, works |
| A voice note or photo, after it is read | The words | Retried like any message |
| A reminder, due during downtime | The reminder | The first minute job after start sends it, marked late. A repeating one resumes at its next time after now, with no flood |
| A reminder, queued but not sent | The stored message | The retry job sends it. A held reminder's hold lives in memory only, so it is simply sent |
| A wish, before the tool ran | The stored message | A retry, as above |
| A wish, queued for the parents | The stored message with its buttons | The retry job sends it |
| A button tap, lost | Nothing, or the stored tap | Pressing the button again works while the thing is still open |

Developer docs: `docs/DESIGN.md` ("Message pipeline", "Tasks, reminders and free-form capture"), `docs/WISHES.md`, `docs/AI_CALLS.md`, and `src/familydb/pipeline.py`, `delivery.py`, `task_service.py`, `buttons.py`, `wish_service.py` and `jobs/reminders.py`.
