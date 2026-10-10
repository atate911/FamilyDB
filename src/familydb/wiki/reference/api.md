# The API

Every family page is also data, for a script or a home dashboard that signs in as a person. It is the page itself, read another way, so it can do exactly what that person can do on the page and nothing more. There is no separate key: a script signs in with a person's name and password, as a browser does, and carries the session cookie.

| Address | What it does |
|---|---|
| `GET /api` | Who is signed in, the pages they may read, the forms they may use, and the token a change carries |
| `GET /api/<the page's address>` | That page as data: `/api/now` is Now, then `/api/eat`, `/api/week/2026-10-17`, `/api/place/57` and so on |
| `GET /api/find?q=words` | Search in the box: what the family has by that name |
| `POST /api/say` | Sends a message, as the box does |
| `POST /api/act` | Any of the page's forms by name: a tick, a snooze, a list, a face, a yes to a wish |

## What a page's answer holds

Each answer has four parts: `page` (which page it is), `answer` (what the page draws: its rows, chips, hints and the fields its forms carry), `box` (the box under the page, with what the last message brought back) and `row` (the destinations along the foot). No model is asked: reading a page as data costs nothing, the same as opening it.

Whatever the page does not show stays out: a Telegram id, a calendar's own event id, whom a present is kept from, a birthday, and anything that looks like a password or a key. A kid's answers are a kid's pages: her own to-dos, no presents, nothing of how it works. A page a person may not open answers `403`, an address that is not a family page answers `404`, and a script that is not signed in gets `401`, never the sign-in form.

The back office (Settings, The family, Status's forms, this guide) is pages only.

## Saying something

`POST /api/say` takes `text`, and optionally `page` (the address it was said from, such as `/eat`), `scope` (what the page puts in front, such as `About #57 Kenji's Ramen:`), and `intent` set to `save_idea` to keep it as an idea. It answers straight away, before Vera does, with the message's id in `asked` and an address in `check`, such as `/api/eat?asked=…`. Read that address a few seconds later: its `box` carries her reply, or a receipt of what she did with the change Undo takes back, exactly as the page shows them under the box. A second message while she is still answering the first is refused with `409`.

This is the one call in the API that asks a model, and it counts toward the day's spending limit and a kid's messages a day like any other message.

## Using a form

`POST /api/act` takes `act`, the name of the form, then the numbers in its address and its fields by name. `GET /api` lists the forms the signed-in person may use, with the numbers each takes. For example, ticking off a to-do sends `{"act": "finish_task", "task_id": 12, "revision": 3}`, where the revision is the one in the page's answer, so a to-do somebody changed meanwhile is not ticked unseen.

The form's own code does the work, so it is the same tool call the button makes, with the same permission and the same checks. The answer says what the page would have said (`said`), whether anything changed (`changed`), and `undo`, the change to send back as `{"act": "undo", "target": …}` to take it back.

## The token

A change carries the token from `GET /api` in an `X-CSRF-Token` header and comes from the page's own address. A request that sends an `Origin` header from anywhere else is refused, the same as a form posted from another site.

Developer docs: `docs/INTERFACE.md` section 11.
