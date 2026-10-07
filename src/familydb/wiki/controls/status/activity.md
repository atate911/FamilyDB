# Recent activity

Recent activity on [Status](/wiki/controls/status) lists what the models were asked lately, and each line opens that message's or lookup's whole history: every model call and tool call, what each cost, and what a lookup found. It is the place to see why one answer went wrong. **Only admins see it**, because it holds the words of every chat, including a kid's.

## The list

It shows the 25 most recent items from the last 7 days, newest first. An item is a message that was answered, the weekend ideas, or a lookup. Each line shows who asked and the start of what they said (or what was looked up), when, what the calls were for, how many calls, how many tokens, how many web searches, and the estimated cost. Costs are estimates, as on the rest of Status.

## One item's history

A line opens `/status/activity/<key>`, where the key is a message number or a lookup's turn. An idea's page also links an admin to how it was looked up. The page has:

- **What was asked**, and the reply that was kept for it, or, when one was recorded, the reason there was none.
- **Model calls**: a table of when, what for, the model and its company, how the call ended, tokens sent, cached, written and sent back, searches, estimated dollars and milliseconds. "Sent" is what was not in the cache. An asterisk marks a model with no listed price, counted high.
- **Tools used**: each tool call in order, folded, with what it was given and what it answered. A failed one is tagged. Long text is cut at 4000 characters; the log keeps it whole.
- **What the lookup found**, for a lookup: the place saved or the reason nothing was, and the pages it read. A note says if the save was refused.

A key that matches nothing shows a not-found page.

## What to look for

| You see | It usually means |
|---|---|
| Several model calls for one message | The assistant used tools, one call for each step. |
| A call ending in `max_tokens` | The answer hit the output limit. Raise "Longest answer (tokens)" on [Spending](/wiki/controls/settings/spending#what-one-message-may-use). |
| A call ending in `refusal` | The model declined to answer. |
| A tool tagged Failed | The tool refused or errored; its answer says why. |

Developer docs: `familydb/web/activity.py` (module note), and `familydb/web/status.py` (`activity`).
