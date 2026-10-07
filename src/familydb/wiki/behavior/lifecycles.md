# Lifecycles

This page follows five things from start to finish (a message, a voice note, a photo, a reminder and a kid's wish) and says where each step can fail and what the family or an admin then sees. Something is stored before the next step runs, so a restart rarely loses anything; the last section says what each restart does. Quoted lines are the assistant's wording as shipped, which the family can reword on [Personality](/wiki/controls/settings/personality). The Telegram side is in [The Telegram loop](/wiki/behavior/telegram-loop), and each job's schedule is in [Jobs](/wiki/behavior/jobs).

## A message, from arrival to reply

1. **It arrives.** A Telegram update carries an id, and one already stored is ignored. On the page the message needs words, at most 4,000 characters, a sender on the family list and no turn already running in that chat. Otherwise the page says so in place and stores nothing (an unknown name gets "There is nobody called X in the family.").
2. **On Telegram the sender is checked.** Someone not on the [family list](/wiki/reference/glossary#family-list) gets one line with their Telegram id and is recorded as a knock (never the text). Nothing is stored and no model is asked.
3. **It is stored** as `received`, before anything else happens.
4. **On Telegram, text waits a moment,** 4 seconds by default, held from the retry job. The newest message from that person in that chat then answers, with earlier ones still waiting folded into it: one turn, one reply. Voice notes, photos and the page are not paused.
5. **It is claimed.** Turns in one chat run one at a time, and the message takes a [lease](/wiki/reference/glossary#lease): five minutes, renewed every 30 seconds while the turn runs. If another worker holds it, this one stops quietly.
6. **Checks that ask no model.** A message already answered or given up is dropped. One from someone since switched off is given up with no reply. A kid past their daily message count ([Spending](/wiki/controls/settings/spending); off by default) or dollar share is told so by code. With no model key it is given up with "I can't answer yet".
7. **The prompt is built.** The cached front is the character, the instructions, the family list and the idea list. Then come the chat's recent messages (by default up to 20 from the last 6 hours, about 1,500 tokens) and the current turn, never cached: when the message arrived, who reads the reply in a shared chat, a recent shared location, [memories](/wiki/model/memory) chosen by code, and any reminder waiting to ride along.
8. **The limit is checked before each call.** The call's estimated cost is held against the day's [limit](/wiki/reference/glossary#spending-limit). Past it, the message is given up, and the first try (not a retry) tells the limit. If the turn had already saved something, code reports what, with no further call.
9. **The tool loop runs.** The model answers or asks for tools, code runs and logs each one, and the model is asked again, up to 8 calls by default. If the first call fails in a way worth moving for and a second model company has a key, that company is asked instead; after a tool has run there is no switch.
10. **The reply is stored,** with the message marked processed, in one transaction. A reminder held for this chat rides along.
11. **It is sent, then marked delivered.** On the page the reply is visible once stored, and sending only marks it delivered. If a send fails, the reply stays stored and the retry job sends every unsent reply each time it runs, with no model call. A send whose answer was lost can arrive twice, and so can the early parts of a long reply that failed partway.

### What a failure looks like

| What went wrong | What the family sees | What happens next |
|---|---|---|
| The model company is busy or unreachable, or something unexpected broke | "Saved your message, but I couldn't process it right now. I'll retry later." | The retry job tries every 5 minutes, 3 times by default, silently. After the last, nothing more is said on Telegram |
| A refusal retrying will not fix (a key, credit, a refused request) | "Saved your message, but I can't reach the model at the moment. An admin needs to check the logs." | Given up. Status usually names the cause |
| The day's limit, or no key | The limit line, or "I can't answer yet" | Given up. Told on the first try, silent on a retry |
| Out of steps | "I couldn't finish that within the steps I'm allowed" | Given up, and told even on a retry |

A retry resolves "tomorrow" from when the message arrived and is told which writes the first try already made. The counter rises once any voice or photo has been read, so 3 retries means 4 attempts in all. A message that runs out of retries is not marked given up. The chat page says "The last message was not answered. It is back in the chat, ready to send again", but [Status](/wiki/controls/status) keeps listing it as "3 tries, will try again", which misleads. Status lists only failed messages, the newest 10; one cut off by a restart, or in the gather hold, is `received` and shows only on the chat page and [Recent activity](/wiki/controls/status/activity), though the retry job treats it like a failed one.

With Telegram disconnected, the retry job skips Telegram messages without counting an attempt, and the log says "not retrying message N: no sender for telegram here". `familydb db retry-failed --reset` makes exhausted messages eligible again ([The command line](/wiki/controls/command-line)). Fixes for each row are in [Troubleshooting](/wiki/operations/troubleshooting).

## A voice note

Voice notes come only from Telegram.

1. **It arrives and the sender is checked.** The recording is not downloaded yet, so a stranger's note costs nothing.
2. **It is stored as a mark** such as "(voice note, 0:42, not heard)", then claimed and checked as in the first sequence.
3. **It is checked for hearing.** Voice notes must be on, a company that can hear must have a key (OpenAI or Gemini; Claude cannot hear), and the note must be within the longest setting (5 minutes by default) and 20 MB. The recording is then fetched.
4. **It is heard,** with the limit checked and the call recorded as "listening to voice notes".
5. **The words replace the mark,** after "(voice note) ", with any caption after them. From here it is an ordinary message.

A failure in steps 3 or 4 is given up with a line asking for it again or typed ("Sorry, I couldn't make out that voice note"). The recording is never kept, so none is retried. Settings are on [AI model](/wiki/controls/settings/ai-model#voice-notes-and-photos).

## A photo

1. **It arrives** as a photo or an image file (JPEG, PNG or WebP). In a group it is handled only when addressed to the bot. An album is collected for 1.5 seconds and becomes one message. The sender is checked before anything is downloaded.
2. **It is stored as a mark:** "(photo, not looked at)".
3. **It is checked.** With photos off, a caption is answered anyway, marked "(with a photo, not seen)", and a photo with no caption gets "I don't look at photos here". A photo is fetched within 1,600 pixels on its long side, an image sent as a file whole, and either must be at most 3.9 MB (a file over it is told to send it as a photo).
4. **Each photo is looked at in a call of its own,** by the lookup model, with the limit checked each time. It writes down what the picture is and the names, dates, times, places and prices in it. Only the first four of an album are looked at.
5. **The words replace the mark,** after "(photo) " (or "(photo 2 of 3) " in an album), with the caption after them. A failed photo in an album is marked "not seen"; the message goes on while one was read.

If none was read, or the limit was reached partway, the message is given up with a line such as "Sorry, I couldn't look at that photo". Pictures are never kept, so none is retried.

## A reminder

No model is involved at any point in a reminder.

1. **It is created** with a future time, by the assistant in chat or by the To do page's form. A time in the past, one the clocks skip, or one that occurs twice without an offset is refused to whoever asked. It goes back to the chat it was asked in, or to Chat for one asked on the page.
2. **The minute job finds it due.** Every minute, in one transaction, it takes due reminders of open things to do (up to 100), chooses where each goes (someone's own chat rather than a group, when [Connections](/wiki/controls/settings/connections#in-a-telegram-group) allows it), and stores the message with its buttons. A task that repeats on a schedule gets its next reminder in the same transaction. One over ten minutes late says when it was due.
3. **It is handed over.** If someone is talking in that chat (a turn running, or a message in the last 5 minutes), it is held up to 2 minutes so the next reply carries it. Otherwise it is sent at once, and a held one nobody replies to is sent by the minute job. A failed send is the retry job's.
4. **A tap does the work.** On Telegram the reminder carries **✓ Done**, **In an hour** and **Tomorrow**. A tap must come from someone on the family list, and a kid may tap only their own things to do. Done marks it done. The others set a new reminder an hour or 24 hours later, replacing the old one. The message gains a note saying who did what, and the buttons go. A change is refused while a reminder is being sent.
5. **Done on a repeating task records this time round** and keeps it going. One counted from its schedule already has its next reminder. One counted from when last done gets its next that day plus the interval, at the first reminder's hour. Done on any other task cancels its reminders.

Reminders go only while `familydb run` is running. Repeating is on [Plans and things to do](/wiki/controls/plans-and-tasks).

## A kid's wish

1. **The kid asks** in the box on the page, or on Telegram. It is an ordinary message, so the first sequence applies, including the kid's count and dollar share.
2. **The model is told the kid's age** (never the birthday) and, only where nobody else reads the reply, their wish topics.
3. **The model sorts it, calls a tool and answers at once.** `add_wish` returns added, duplicate, locked (with the date they may ask again), too many today or list full. `turn_away` keeps a house rule, a complaint about a sibling or an inappropriate request for the parents. The rules are on [Wish lists](/wiki/controls/wish-lists).
4. **Parents are told in two cases.** An inappropriate request goes straight after the turn to every parent or admin with a Telegram id, and so does a kid's **Ask a parent** press on the page. Each carries **Yes!**, **Not this time** and **Later**. Everything else waits on the page.
5. **A parent answers** on the page or with a tap. A tap works only for a parent, and Later only shows a pop-up and leaves the buttons. The others run `update_wish` as the person who tapped, with no model call, and the buttons go from that message.
6. **The kid is told** in their own conversation on the page, with any note the parent wrote. A no adds the day they may ask again.

## What survives a restart

| In the middle of | What happens |
|---|---|
| A message, before it is stored | Nothing is kept. The sender sees no answer and sends it again |
| A message, waiting out the pause | The hold lasts the pause plus 5 minutes. The next retry job after that answers each waiting message in turn, not together |
| A message, in the turn | The lease lapses about 5 minutes after its last renewal, then the next retry job (up to 5 more minutes by default) answers it, told which writes already happened. A model call in flight is never recorded; its hold counts toward the limit for up to 30 minutes, then is forgotten |
| A reply, stored but not sent | The retry job sends it. If it was sent but not marked, it goes twice; the model is not asked again |
| A voice note or photo, before it is read | The retry job gives it up and says it could not be read, since the recording is gone. Sending it again works. After it is read, it is retried like any message |
| A reminder, due during downtime | The next minute job sends it, marked late. A repeating one resumes at its next time after now, with no flood |
| A reminder or a wish for the parents, queued but not sent | The retry job sends it; holds are in memory only, so a held reminder is simply sent |

Developer docs: `docs/DESIGN.md` ("Message pipeline", "Tasks, reminders and free-form capture"), `docs/WISHES.md`, `docs/AI_CALLS.md`, and `src/familydb/pipeline.py`, `delivery.py`, `task_service.py`, `buttons.py`, `wish_service.py` and `jobs/reminders.py`.
