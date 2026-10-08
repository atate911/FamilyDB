# What leaves the house

Messages go to the model company you chose, and almost nothing else leaves the server. The list below is the one place that says what leaves, to whom, when, and how to stop it.

- Messages go to the model company you chose, with the recent conversation and what the assistant knows about the family. A company you add yourself, such as OpenRouter, gets them only once you choose it or let it stand in.
- Voice notes and photos go to the company that hears or looks at them. FamilyDB never keeps the recording or the picture.
- Telegram sees everything said on Telegram, and Google sees the plans on your calendar.
- Weather, map and price services get a place name or coordinates, never a message.
- If you turn on dictation, the sound goes from the browser to its maker, never through FamilyDB.

What each company does with what it receives is governed by its own terms, not by FamilyDB. The page itself loads nothing from other sites. What is stored on the server is on [What is stored and for how long](/wiki/security/data-and-privacy).

## What leaves, to whom, and how to stop it

Where a row says "the company", the second company can receive the same content when the first is busy, out of credit or refusing. It needs a saved key and **Ask another company when the first cannot** on, which is the default.

| What leaves | To whom | When | How to stop it |
|---|---|---|---|
| Your message, and by default up to 20 earlier messages from the last 6 hours, each cut to 1,500 characters | The company that answers (`provider`) | Every message it answers | Not without stopping the assistant. [Choose the company](/wiki/controls/settings/ai-model#who-answers) or [shorten the history](/wiki/controls/settings/spending#what-one-message-may-use) |
| The same, when an added company (OpenRouter, or one with its own address) is chosen, or allowed to stand in | That company, and for OpenRouter the company it routes to | Every message it answers, and only then | [Choose another company](/wiki/controls/settings/ai-model#other-companies), or take it away |
| Names and roles, the home area, the time zone, the family's own words and the persona, the idea list without presents, remembered facts, and what a tool returns | The same company | With each message | The same. [Turn off the second company](/wiki/controls/settings/ai-model#a-second-company) so only one company ever sees it |
| Calendar entries a tool returns: titles, times and places, plus the descriptions of all-day ones | The same company | When the assistant reads the calendar | Disconnect the calendar (see Google below) |
| The weekend ideas question and the same context | The chat company, at the weekend ideas level | Once a week | Empty [`digest_chat_id`](/wiki/controls/settings/messages#weekend-ideas) |
| An idea's title, kind, place, description, link, who it is for, the home area, and details saved before | The lookup company (`worker_provider`) | When an idea is looked up, by default each evening | [`web_tools_enabled`](/wiki/controls/settings/lookups#looking-ideas-up), on after an install |
| The same lookup's web searches | The company's hosted web search, which is given the home city, region and time zone as the search location where it takes one | During a lookup | The same setting |
| A search for what is on: dates, a topic, the home area and who it is for | The lookup company | When a suggestion asks for it | The same setting |
| A shared position and its place name | The chat company, and the lookup company when a search starts from it | Only after somebody shares a position. See [Shared location](/wiki/model/location) | Nobody has to share; there is no setting |
| The same coordinates, to be named | OpenStreetMap's Nominatim | When a share is not within 200 metres of the last named place | The same |
| A voice recording, with the family's names and home area as hints | The company that hears (OpenAI or Gemini), or the second company | Each family voice note | [`voice_notes`](/wiki/controls/settings/ai-model#voice-notes-and-photos) |
| A photo, with the same hints | The lookup company, or the second company | Each family photo | [`photos`](/wiki/controls/settings/ai-model#voice-notes-and-photos) |
| Model names, prices and a refusal's error text, never the family's messages. A disputed price is checked on the web | The lookup company, at the level `judgement_level` names, or the second company | When a change needs weighing | [`judgements`](/wiki/controls/settings/ai-model#asking-a-stronger-model-to-weigh-a-change), off unless you turn it on |
| A list-models request with each key, and requests for LiteLLM's and OpenRouter's price lists that carry nothing of the family | Each model company, GitHub, OpenRouter | Daily at 05:17 | [`model_watch`](/wiki/controls/settings/ai-model#keeping-up-with-the-companies) |
| Every chat on that channel, voice notes and photos, shared positions and button taps | Telegram | As the family uses it | [Remove the Telegram bot token](/wiki/controls/settings/connections#telegram) |
| Plan titles, times, places and notes; the calendar is read for what is on | Google | When a plan is made, changed or looked up | No button: delete `data/google_key.json` on the server and unshare the calendar in Google |
| The home area, idea locations, place addresses and places named in a question, to find coordinates | Nominatim, then Open-Meteo's geocoder for a short name. A `GEOCODER_CONTACT` you set goes in the request header | When one is typed or saved | No setting |
| Home coordinates and dates | Open-Meteo | When a forecast is needed | No setting. With no home position there is no forecast |
| The sound of dictation | The browser's maker (Apple for Safari, Google for Chrome; other browsers vary, and Firefox has no mic), never through FamilyDB | When somebody presses the mic | [`web_dictation`](/wiki/controls/settings/general#this-page) |

## What a kid's message adds

A kid's message goes to the model company like anybody's. The assistant is told every person's name and role, and in a kid's own turn their age and whether they are recorded as a girl or a boy, never the birthday. A kid's wish topics are sent only where nobody else reads the reply. The reply a kid reads says what happened and never how the assistant works. See [Kids](/wiki/model/family-and-roles#kids).

A present is left out of the idea list the assistant carries for everyone, but a present with a place or link is still sent to the lookup company with who it is for. See [Presents](/wiki/model/ideas-and-places#presents).

Developer docs: docs/DESIGN.md, "Decisions"; docs/AI_CALLS.md, "What does it see?".
