# What it touches

FamilyDB runs on one machine, but it reaches out to a few outside services. This
page lists each, says what goes to it, and ends with the plain answer to the
question every family asks: what leaves the house.

## The services

**Model companies: Anthropic (Claude), OpenAI, Google (Gemini).** All three sit
behind one small protocol, so the rest of the code knows no vendor. The family
chooses a company for the chat, the weekend digest and the lookups separately, and
may name another as a spare for when the first is busy. Each company's lineup is
known by *level* (everyday, better, best), and everyday is that company's cheapest
model unless the family chooses otherwise. A model's price is estimated from a
table kept current by the daily check, and a model neither knows is counted dearer
than any listed. The page can check a key with its company before saving it.

**Telegram.** The bot talks to Telegram by long polling, which means it asks "anything
new?" and waits. It needs no inbound connection, no public address and no port
opened for it. A Telegram id on the family list is what lets someone talk to the
bot. A message from anyone not on the list is not answered and no model is asked
(a stranger's voice note is not even downloaded); an admin can let them in. Texts,
voice notes, photos and button taps all arrive this way.

**Google Calendar.** The bot is a service account the family shares its calendar with,
so it holds nobody's sign-in and no one's mail is within reach. The calendar is
read for what is on and written for confirmed plans. With none connected, the page
shows the saved plans and says so.

**The weather and the map.** The forecast comes from Open-Meteo. Where home is, and
where a phone says someone is, are named by a reverse geocoder (Nominatim, with
Open-Meteo as the fallback).

**Price lists.** Once a day the model check reads LiteLLM's and OpenRouter's public
lists and takes a price only when both agree, or when one alone moves sanely.

**The web in front.** The installer puts HTTPS in front of the page with Caddy, at
the server's own address or a domain, on 443 or a port the family names. The page
itself listens only on the machine, so the proxy is the only way in.

## What leaves the house

Everything else stays in one file on the family's machine. These are the things
that do not, each a decision the family made:

- **What the family writes to the bot** goes to the model company that answers, because that is how it is answered. The chat model is never given the web; lookups are separate worker turns.
- **A voice note's recording** goes to the vendor's speech model, is written down once, and is not kept. Only the words are stored.
- **A photo** is described by the lookup model, and only what it shows, in words, is kept.
- **A shared location** goes to the chat model and the discovery worker as a place name and coordinates, only while a phone has shared one (it is used for three hours, and deleted after a day at most), so nobody has to type where they are. "Send where I am" is off until someone ticks it.
- **Dictation** on the page uses the browser's own speech recognition: the sound goes from the browser to its maker (Apple for Safari, Google for Chrome) and never through FamilyDB. It can be turned off on the General page.
- **Telegram** carries every chat on that channel, as it would any bot's.

## In this section

**Still to come:** a page per service with how it communicates, how to set it up,
its limits, its security and what to do when it changes, and one on the host: what
the installer put on the server.

Deeper detail: `docs/DESIGN.md` sections 10, 11 and 16.
