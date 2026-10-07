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

**The weather and the map.** The forecast comes from Open-Meteo. Your home town is looked up
on the map by Nominatim (OpenStreetMap), with Open-Meteo's geocoder as the fallback for short town
names, and where a phone says someone is gets its place name from Nominatim.

**Price lists.** Once a day the model check reads LiteLLM's and OpenRouter's public
lists and takes a price only when both agree, or when one alone moves sanely.

**The web in front.** The installer puts HTTPS in front of the page with Caddy, at
the server's own address or a domain, on 443 or a port the family names. The page
itself listens only on the machine, so the proxy is the only way in.

## What leaves the house

Everything else stays in one file on the family's machine; what does not is what the family writes, a voice note or photo, a shared location and a few lookups, each a decision the family made, and a spare model company can receive the same content when the first cannot answer. [Data and privacy](/wiki/security/data-and-privacy) is the one list of what leaves, to whom, when, and whether you can turn it off.

## In this section

**Still to come:** a page per service with how it communicates, how to set it up,
its limits, its security and what to do when it changes, and one on the host: what
the installer put on the server.

Deeper detail: `docs/DESIGN.md` sections 10, 11 and 16.
