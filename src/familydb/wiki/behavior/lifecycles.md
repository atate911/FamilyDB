# Lifecycles

This page follows five things from start to finish (a message, a voice note, a photo, a reminder and a kid's wish) and says where each step can fail and what the family or an admin then sees. The rule behind all five is that something is stored before the next step runs, so a restart rarely loses anything. The last section says what each restart does.

The quoted lines are the assistant's wording as shipped, which the family can reword on [Personality](/wiki/controls/settings/personality). Where a kid reads, a line about how the bot works is replaced by a plain one ("Ask me again in a little while!"). The Telegram side is in [The Telegram loop](/wiki/behavior/telegram-loop), and each job's schedule is in [Jobs](/wiki/behavior/jobs).

## A message, from arrival to reply

1. **It arrives.** A Telegram update carries an id, and one already stored is ignored. On the page the message needs words, at most 4,000 characters, a sender on the family list and no turn already running in that chat. Otherwise the page says so in place and stores nothing ("Still thinking about the last message. Give it a moment.").
2. **The sender is checked.** Someone not on the [family list](/wiki/reference/glossary#family-list) gets one line with their Telegram id and is recorded as a knock (never the text). Nothing is stored and no model is asked.
3. **It is stored** with the status `received`, before anything else happens to it.
4. **On Telegram, text waits a moment.** By default for 4 seconds, held from the retry job. The newest message from that person in that chat then answers, with earlier ones still waiting folded into it: one turn, one reply. Voice notes, photos and the page are not paused.
5. **It is claimed.** Turns in one chat run one at a time, and the message takes a [lease](/wiki/reference/glossary#lease): five minutes, renewed every 30 seconds while the turn runs. If another worker holds it, this one stops quietly.
6. **Checks that ask no model.** A message already answered or given up is dropped. One from someone since switched off is given up with no reply. A kid past their daily message count ([Spending](/wiki/controls/settings/spending); off by default) or dollar share is told so by code. With no model key it is given up with "I can't answer yet".
7. **The prompt is built.** The cached front is the character, the instructions, the family list and the idea list. Then come the chat's recent messages (by default up to 20 from the last 6 hours, about 1,500 tokens) and the current turn, never cached: when the message arrived, who reads the reply in a shared chat, a shared location under three hours old, a kid's age, [memories](/wiki/model/memory) chosen by code, and any reminder waiting to ride along.
8. **The limit is checked before each call.** The call's estimated cost is held against the day's [limit](/wiki/reference/glossary#spending-limit) and given back when it is recorded. Past it, the message is given up and told the limit. If the turn had already saved something, code reports what, with no further call.
9. **The tool loop runs.** The model answers or asks for tools, code runs and logs each one, and the model is asked again, up to 8 calls by default. If the first call fails in a way worth moving for and a second model company has a key, that company is asked instead. After any tool has run there is no switch, because it would repeat a write.
10. **The reply is stored,** with the message marked processed and what the turn did, in one transaction. A reminder held for this chat rides along.
11. **It is sent, then marked delivered.** On the page the reply is visible once stored, and sending only marks it delivered.
12. **If the send fails,** the reply stays stored. The retry job sends every unsent reply each time it runs, with no model call. A send whose answer was lost can arrive twice, and a reply sent in parts that fails partway is sent again in full.

### What a failure looks like

| What went wrong | What the family sees | What happens next |
|---|---|---|
| The model company is busy or unreachable, or something unexpected broke | "Saved your message, but I couldn't process it right now. I'll retry later." | The retry job tries every 5 minutes, 3 times by default, silently. After the last, nothing more is said on Telegram; the message stays under "Messages that did not go through" on [Status](/wiki/controls/status), and the page says it is out of tries |
| A refusal retrying will not fix (a key, credit, a refused request) | "Saved your message, but I can't reach the model at the moment. An admin needs to check the logs." | Given up. Status usually names the cause |
| The day's limit, or no key | The limit line, or "I can't answer yet" | Given up |
| Out of steps | "I couldn't finish that within the steps I'm allowed" | Given up, and told even on a retry |

A retry resolves "tomorrow" from when the message arrived and is told which writes the first try already made, so it does not repeat them. A process not connected to Telegram does not retry a Telegram message. What to do about each row is in [Troubleshooting](/wiki/operations/troubleshooting).

## A voice note

Voice notes come only from Telegram. The page's dictation is the browser's own and sends words, not a recording.

1. **It arrives and the sender is checked.** The bot builds a way to fetch the recording but does not download it, so a stranger's note costs nothing. In a group a note is ignored only when "answer only when mentioned" is on and it is not addressed to the bot.
2. **It is stored as a mark** such as "(voice note, 0:42, not heard)", then claimed and checked as in the first sequence. A kid's note counts as one of their messages.
3. **It is checked for hearing.** Voice notes must be on, a company that can hear must have a key (OpenAI or Gemini; Claude cannot hear), and the note must be within the longest setting (5 minutes by default) and 20 MB. The recording is then fetched, with a 60 second timeout.
4. **It is heard.** The limit is checked and recorded as for any call, under "listening to voice notes". The family's names and the home area go along so they are spelled the family's way.
5. **The words replace the mark,** after "(voice note) ", with any caption after them. From here it is an ordinary message, and retries and an idea's original thought read the words.

A failure in steps 3 or 4 is given up with a line asking for it again or typed: "I don't listen to voice notes here", "I can't hear voice notes yet", "That voice note is longer than the 5 minutes I listen to", "Sorry, I couldn't make out that voice note", or the limit line. The recording is never kept, so none is retried. Settings are on [AI model](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## A photo

1. **It arrives** as a photo or an image file (JPEG, PNG or WebP). In a group it is handled only when addressed to the bot, whatever the mention setting. An album is collected for 1.5 seconds and becomes one message with the first caption. The sender is checked before anything is downloaded.
2. **It is stored as a mark:** "(photo, not looked at)".
3. **It is checked.** With photos off, a caption is answered anyway, marked "(with a photo, not seen)", and a photo with no caption gets "I don't look at photos here". Each picture is fetched at the largest size within 1,600 pixels on its long side and must be at most 3.9 MB.
4. **Each photo is looked at in a call of its own,** by the lookup model, with the limit checked each time. It writes down what the picture is and every name, date, time, place and price in it, guessing nothing. Only the first four of an album are looked at.
5. **The words replace the mark,** after "(photo) " (or "(photo 2 of 3) " in an album), with the caption after them. A photo that failed in an album is marked "not seen", and the message goes on while at least one was read.

If none was read, or the limit was reached partway, the message is given up with "That picture is too large for me to look at", "Sorry, I couldn't look at that photo" or the limit line. Pictures are never kept, so none is retried.

## A reminder

No model is involved at any point in a reminder.

1. **It is created** with a time in the future, by the assistant in chat or by the To do page's form. A time in the past, or one the clocks skip, is refused to whoever asked. The reminder goes back to the chat it was asked in, or to Chat for one asked on the page. The task and its reminder are saved in one transaction.
2. **The minute job finds it due.** Every minute, in one transaction, it takes due reminders of open things to do (up to 100 at a time), chooses where each goes (someone's own chat rather than a group, when [Connections](/wiki/controls/settings/connections#in-a-telegram-group) allows it), stores the message with its buttons and attaches it to the reminder. A task that repeats on a schedule gets its next reminder in the same transaction. One more than ten minutes late says when it was due.
3. **It is handed over.** If someone is talking in that chat (a turn running, or a message in the last 5 minutes), it is held up to 2 minutes so the next reply carries it. Otherwise it is sent at once, and a held one nobody replies to is sent by the minute job.
4. **It is sent** like any reply. On Telegram it carries **Done**, **In an hour** and **Tomorrow**. A failed send is the retry job's, and the minute job never queues it twice.
5. **A tap does the work.** It must come from someone on the family list, and a kid may tap only their own things to do. Done marks it done. The other two set a new reminder an hour or 24 hours after the tap, replacing the old one. The tap is stored, the message gains a note saying who did what, and the buttons go. A change is refused while a reminder is being sent, and the tap says it didn't go through.
6. **Done on a repeating task records this time round** and keeps it going. One counted from its schedule already has its next reminder. One counted from when last done gets its next that day plus the interval, at the first reminder's hour. Done on any other task cancels its reminders, queued ones included.

Reminders go only while `familydb run` is running. The rules for repeating are on [Plans and things to do](/wiki/controls/plans-and-tasks).

## A kid's wish

1. **The kid asks** in the box on the page, or on Telegram. It is an ordinary message, so the first sequence applies, including the kid's count and dollar share.
2. **The model is told who is asking:** their age, male or female if an admin set it, never the birthday, and their wish topics only where nobody else reads the reply. Code decides all of that.
3. **The model sorts it and calls a tool.** `add_wish` answers added, duplicate, locked (with the date they may ask again), too many today or list full. `turn_away` keeps a house rule, a complaint about a sibling or an inappropriate request for the parents. The rules are on [Wish lists](/wiki/controls/wish-lists).
4. **The kid is answered at once,** briefly and at their age.
5. **Parents are told in two cases.** An inappropriate request goes straight after the turn to every parent or admin with a Telegram id, and so does a kid's **Ask a parent** press on the page. Each message carries **Yes!**, **Not this time** and **Later**. Everything else waits on the page, and a parent with no Telegram id sees the to decide badge there.
6. **A parent answers** on the page or with a tap. A tap works only for a parent, and Later only shows a pop-up and leaves the buttons. The others run `update_wish` as the person who tapped, with no model call, and the buttons go from that message. Another parent's copy then says it is already dealt with.
7. **The kid is told** in their own conversation on the page, in the assistant's words with any note the parent wrote. A no adds the day they may ask again.

## What survives a restart

| In the middle of | What happens |
|---|---|
| A message, before it is stored | Nothing is kept. The sender sees no answer and sends it again |
| A message, waiting out the pause | The hold lapses after the pause plus 5 minutes, and the retry job answers each waiting message in turn, not together |
| A message, in the turn | The lease lapses within 5 minutes and the retry job answers it, told which writes already happened. A model call in flight is not recorded, so the day's estimate misses it |
| A reply, stored but not sent | The retry job sends it. If it was sent but not marked, it goes twice; the model is not asked again |
| A voice note or photo, before it is read | The retry job gives it up and says it could not be read, since the recording is gone. Sending it again works |
| A voice note or photo, after it is read | Retried like any message, from its words |
| A reminder, due during downtime | The next minute job sends it, marked late. A repeating one resumes at its next time after now, with no flood |
| A reminder, queued but not sent | The retry job sends it. A hold lives in memory only, so a held reminder is simply sent |
| A wish, queued for the parents | The retry job sends it |
| A button tap, lost | Pressing again works while the thing is still open |

Developer docs: `docs/DESIGN.md` ("Message pipeline", "Tasks, reminders and free-form capture"), `docs/WISHES.md`, `docs/AI_CALLS.md`, and `src/familydb/pipeline.py`, `delivery.py`, `task_service.py`, `buttons.py`, `wish_service.py` and `jobs/reminders.py`.
