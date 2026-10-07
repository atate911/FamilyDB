# Layers and flow

FamilyDB is built in layers, and a message crosses them in one fixed order. This page names the layers, shows how a chat message and a form on the page each travel through them, and says why each rule that keeps a layer replaceable exists. [How it is built](/wiki/overview/how-its-built) covers the threads and the process; [Lifecycles](/wiki/behavior/lifecycles) has the full step list for a message, a voice note, a photo and a reminder.

## The layers

```
 Telegram     Web chat     Console            Browser           Timer
     \           |           /                   |                |
      v          v          v                    v                v
  +---------- channels ----------+          the web page         jobs
  | take messages in, send out   |          (reads, forms)  (reminders, lookups,
  +--------------+---------------+               |           digest, retries)
                 v                               |                |
            pipeline  (dedupe, store, lease,     |                |
                 |     build the turn, reply)    |                |
                 v                               |                |
            gateway  (limit, kind, record) <-----+----------------+
                 |                               |                |
                 v                               |                |
            agent loop --> model company         |                |
                 |                               |                |
                 v                               v                v
            tools  (registry, ToolContext) <-----+----------------+
                 |
                 v
            engines --> Google Calendar, weather, geocoder
            (suggest, free time, tasks, wishes)
                 |
                 v
            store  (SQLite, one repository per table)
```

Read it top to bottom. A **channel** is an adapter for one way of talking: Telegram, the page's chat, or the console (`familydb chat` and `familydb repl`). The **pipeline** handles one inbound message from arrival to stored reply. The **gateway** is the one door to a model, and the **agent loop** is the cycle of asking the model, running the tools it names and asking again. **Tools** are small checked functions the model may call, and **engines** are the code behind them that weighs an idea against the calendar, forecast and opening hours. The **store** is the database, behind one module per table.

Two things sit alongside. The **web page** reads the store and changes it only through tools (below). The **jobs** run on the timer, mostly without any model call; the weekend digest and retries go through the pipeline, and lookups go through the gateway as separate [worker turns](/wiki/reference/glossary#worker-turn).

## Rules that keep a layer replaceable

- **A message is stored before anything else happens, and a reply is stored before it is sent.** A crash or a failed send then loses nothing: the retry job finishes the work, and a resend never reruns the model or touches the calendar. The price is that a reply may arrive twice, because Telegram cannot say whether a lost answer was a lost send.
- **A message under way holds a [lease](/wiki/reference/glossary#lease).** A restart strands nothing, because the claim lapses and the retry job takes the message over, and two workers do not answer one message.
- **Every model call goes through the [gateway](/wiki/reference/glossary#gateway).** The daily spending limit is checked and every call is recorded in one place, so every feature is limited and counted the same way. A test fails if anything else starts a turn.
- **The loop knows no model company.** Each company's request shape, cache markers and error codes live in one module under `agent/providers/`, and no other module imports a company's SDK, so adding or swapping a company touches one folder.
- **Tools reach the outside only through the context they are handed.** Calendar, weather and geocoder arrive in `ToolContext`, not built inside a tool, so tests run on fakes and every route out of the house is in one place.
- **A form on the page is a tool call, not a second write path.** The page can then do nothing the assistant cannot, and a change gets the same validation, permission check and log entry whoever makes it. The family list is the deliberate exception: it is not a tool, so the model can never change who may message it or sign in.
- **The tool list stays the same between turns, and nothing that varies sits in the cached front of a request.** A varying list or a date in the prefix would make the model company's cache miss on every message, which costs money. Dispatch also refuses a tool that was not declared for the turn, because a fetched web page can talk a model into naming any tool.
- **The chat model gets no web access.** Only worker turns do, with their own prompt, a few tools and a cap on searches. What a fetched page says, which may be written to mislead, is kept out of the chat's own request, and results come back only through strict tools.
- **A page view makes no model call.** Browsing costs nothing; only a message sent does.

## One chat message

A parent writes "we should try the ramen place" in the family Telegram group.

1. The Telegram thread receives the update. With the default pause of four seconds (`gather_seconds`), the channel stores the message at once and waits, so a burst of messages gets one reply. Otherwise it goes straight on.
2. The pipeline checks it has not seen the update id, finds the sender on the family list (a stranger is turned away and nothing else runs), takes a lease and builds the turn: today's date, who is asking, who reads the reply, any shared location and the memories that bear on the message.
3. The gateway builds the request: the cached front (persona, instructions, family, idea list, tools), then the recent conversation, then that uncached turn. The cached front is what the [prompt cache](/wiki/reference/glossary#prompt-cache) can reuse. It checks the limit before each call.
4. The loop calls the model. The model asks for `add_idea`; the registry validates the input, runs the handler as that parent (it writes inside its own transaction), and logs the call. The loop calls the model again and gets a short reply.
5. The pipeline stores the reply and marks the message processed. Delivery then sends the reply through Telegram and marks it delivered only after the send worked.

## One form on the page

A parent opens an idea, changes its title and presses Save.

1. The browser posts to the page. A waitress thread passes it to Flask, which first asks who is signed in and whether their role may change things.
2. The view checks the form's Origin and CSRF token, then builds a `ToolContext` for the signed-in person, with the revision of the idea the form was drawn from.
3. The view calls `update_idea` through the registry. The tool compares the revision inside its own transaction, so someone else's newer edit is not overwritten, and writes the change.
4. The page flashes the result and redirects. No model was asked, and neither the pipeline nor the gateway was involved.

Developer docs: `src/familydb/pipeline.py` (`handle_incoming`, `_run`), `agent/gateway.py` (`KINDS`, `ask`), `agent/loop.py` (`run_turn`), `tools/registry.py` (`ToolContext`, `ToolRegistry.dispatch`), `delivery.py` (`lease`, `deliver`), `web/edits.py` (`run`); `docs/DESIGN.md`, "Architecture" and "Message pipeline"; `docs/AI_CALLS.md`, "The one idea"; `CLAUDE.md`, "Rules that keep it working".
