# Adding a model company

How FamilyDB talks to a company that is not one of the three it ships with (OpenAI, Anthropic,
Google), what it takes to add one, and what is deliberately not done. `docs/AI_CALLS.md` is how a call
is framed; this is who it can go to. The decision behind it is in `docs/DESIGN.md` section 16
("Model vendor", "Keeping up with models and prices").

## The idea

A **company** is data first and code only when it has to be. `agent/providers/companies.py` holds one
`Company` for each: what it is called in a picker, a notice and the Status page, where its key and
models live, which model names are its own. The three with modules of their own are written there;
any other is a `config.CompanyDef` kept in the settings and spoken to by one adapter,
`agent/providers/chat.py`, which speaks the OpenAI chat protocol (`/chat/completions`, `/models`).
That protocol is the one most companies offer, so DeepSeek, Moonshot (Kimi), Z.ai (GLM), MiniMax,
Alibaba (Qwen), OpenRouter, Ollama or vLLM on the family's own network are each a definition and not
a release.

Nothing outside `agent/providers/` and the registry names a company any more: a label, a key's
setting, a spare's order, a model's owner are each asked of the registry.

## Adding one, by cost

1. **On the page** (AI model settings, Other companies). OpenRouter needs a key and a model; any
   other, a name, the address of its chat service, a key and a model. The key is checked with the
   company (a free `GET /models`, and for a template that names one a path only a good key opens,
   since OpenRouter's list of models is public) before it is kept; only a refusal stops the save. The
   company's own list is then read at once for what its models cost (`model_watch.check_added`), and
   the page says which are still unpriced. A saved key is never sent to an address its owner has not
   just vouched for: changing a company's address asks for the key again. This is the whole job for a
   service that follows the protocol.
2. **In `.env`**, edited by hand (the installer does not ask for these): `COMPANIES` is a JSON list of
   definitions and `COMPANY_KEYS` a JSON object of key by name (`COMPANIES='[{"slug": "kimi", "label": "Kimi",
   "base_url": "https://api.moonshot.ai/v1", "model": "..."}]'`). A stored value on the page wins, as
   for every setting.
3. **A template**, when a service is common enough that its address and switches should not be typed
   (`companies.TEMPLATES`, today OpenRouter): a `Template` of the values that are the same for
   everyone, and a link name each for its keys and models in `web/links.py`.
4. **A module of its own**, when a company's quirks outgrow the adapter (a request it cannot express as
   `extra_body`, a hosted search the app should use): see "Adding a built-in company" below.

## What a definition holds (`config.CompanyDef`)

| Field | Why it is data |
|---|---|
| `slug`, `label` | The name in the settings and on every page. A slug is lower case letters, digits and hyphens, never a built-in one. |
| `base_url` | The part before `/chat/completions`. https, unless `local`; a typed address must lead out onto the internet (`integrations/address.py`), because this server is the one that goes there with a key. A template's address is ours and is not looked up. |
| `local` | Runs on this machine or the family's network: http is allowed and no key is needed. A host that is out on the internet cannot be called local. |
| `model`, `worker_model`, `better_model`, `best_model` | Names as the company writes them. The lineup (everyday, better, best) has no company-wide answer for a company nobody listed, so the family names them; empty is the everyday model. |
| `prices` | US dollars per million tokens, typed. They win over what the daily check read, and a model with no price anywhere is counted at `prices.UNLISTED`, dearer than any listed, so the daily limit stops early. An added company's prices are matched by the exact name only: a prefix would price a dearer variant at its cheaper sibling's rate. |
| `reasoning_fields` | The message field a model's thinking comes back in. Some companies require it sent back unchanged beside a tool call or the next request fails (DeepSeek's `reasoning_content`; OpenRouter's `reasoning_details`). The first one a reply carries is kept in `ModelReply.raw` and replayed; if the company refuses it, it is left out and an admin told (`parts.py`). |
| `extra_body` | A company's own switches, merged into every request: OpenRouter's `provider` preferences, a `thinking` object. Plain JSON. **Never dropped to get an answer**: one may be the family's protection, and a request that cannot carry it fails instead (a 400 naming it is `refused`). The fields the adapter owns or that would change what a chat may do (`model`, `messages`, `tools`, `max_tokens`, `stop`, `response_format`, `plugins`, `models`, `web_search_options`...) are refused. A person may take a template's protection out of a company's fields; the page says so then, and stops promising it. |
| `stand_in` | May answer when the company chosen cannot. Off: an added company is asked nothing until an admin chooses it. |

Its key is `Settings.company_keys[slug]`, a secret like every other: stored, never rendered into a
form, never written to the change log (`store.settings.HIDDEN`), masked in `familydb config`. Taking a
company away takes its key; a company that is answering cannot be taken away.

## What the adapter does, and does not

Does: builds the request from the provider-neutral one (a system message, the conversation, tools as
plain function schemas); reads a reply's text, tool calls and finish reason; normalises usage under
each company's names for the cache (`prompt_tokens_details.cached_tokens`, DeepSeek's
`prompt_cache_hit_tokens`); reads a refusal the way the loop and the alerts expect (`_trouble`: 402,
or a 429 that says quota, is out of credit; 401, or a 403 that names a key, is a refused key; a 404
naming a model is a model gone; other 4xx is `refused`; 408, 409, 425, 429 and 5xx are retried);
lists models and, where the company's own list carries prices (OpenRouter's does), what they cost
(`priced_models`, read by the daily check). A reply in a shape it cannot read (content as a list of
parts is read; a null message, a body cut off or not JSON) is an `AgentError` to ask again, never a bare
exception. The client never follows a redirect: an address was checked and a redirect would go to one that
was not.

Does not, and says so:

- **Hosted web search.** Every company has its own, or none, and none is standard. `searches` is False;
  `providers.for_surface(..., web=True)` hands a lookup, discovery, a place search or a price check to
  the cheaper of the companies with a key that can search, but only while "ask another company when the
  first cannot" is on (off, one company sees the family's words, so a lookup waits unless a company for
  lookups is chosen, which only the built-in ones can be). `ready(..., web=True)` is False when none can,
  so the kinds that need it wait, and Status and `debug cost` say so. The chat never searched, so it can
  go to an added company.
- **Voice notes and photos.** `listener()` and `viewer()` are None, so `hearers` and `lookers` skip it.
- **Strict tool schemas and cache markers.** Companies disagree on both and the protocol has neither;
  tool inputs are validated by handler checks as everywhere, and a company that caches does so by prefix
  on its own.
- **A token count.** `count_tokens` raises, as OpenAI's does.

## What the family's words do

An added company is a company between the family and a model, and for OpenRouter a second one behind
it. So: nothing is sent until an admin chooses it for chat (`Answer with`) or lets it stand in; the
page says whose it is; the OpenRouter template asks for only companies that keep and train on nothing
(`provider.data_collection: deny`) and that take every parameter sent (`require_parameters`), a request
that cannot be served that way failing and never being served otherwise; a company out of credit or
refusing its key is told to admins as any is (`alerts.py`, `AgentError.trouble`). What leaves the house
is in the guide (`security/what-leaves-the-house`).

## Cost and the daily limit

Unchanged in kind: `spending.admit` holds an estimate before every call, from `prices.price`, and a
call is recorded in `llm_calls` under the company's slug with its tokens and `prices.cost`. The daily
check (`model_watch._read_added`, `_keep_added`) asks each added company's list (free), keeps what it
says of the models its definition names, and prices them from the company's own list when that carries
prices; nothing is told to admins and no model is swapped on its word (a list that leaves out a working
alias would raise a false alarm, and a model really gone fails on its own and is told then,
`alerts.noticed`). A call is priced by the name the company answered with, or by the model asked for when
that name is a snapshot nobody priced. A model priced nowhere is counted dear, and the page and the
doctor say so.

## Proving a company works

- `uv run pytest tests/test_provider_chat.py`: the adapter through the real loop and the real SDK
  against a fake server (httpx's mock transport), written as one conversation with each company's
  differences as data: where the thinking comes back, what the cache is called, how it says "out of
  credit", what a 400 naming the thinking does. A company that behaves differently from these gets its
  case here first.
- `familydb doctor --online`: for each added company, the key, whether its list has the models named, and
  whether each is priced. No model is asked.
- `familydb chat "hello"` after choosing it: the end-to-end call, which is paid, through the gateway like
  every other. `familydb debug prompt` shows the request it would send.

## Adding a built-in company

A company whose quirks the adapter cannot carry is a module beside `openai.py` and `gemini.py`:

1. `agent/providers/<slug>.py` with a class that satisfies `Provider` (`base.py`), `searches` set, its
   `PARTS` (`parts.py`) and its error mapping into `AgentError.trouble`.
2. A `Company` in `companies.py` and its slug in `config.BUILT_IN_COMPANIES`; its key, everyday chat and
   lookup models, better and best models as settings (`config.py`, `store/settings.py`, `web/fields.py`).
3. `build()` in `providers/__init__.py`, its lineup in `catalog.py`, its prices in `prices.py`, and
   LiteLLM's and OpenRouter's names for it in its `Company` (the daily check's lists).
4. Tests: `tests/test_companies.py` holds that every built-in company has a module and the settings it
   names, and the provider's own test file holds its request shape.

## Not done, and why

- **A hosted search for an added company.** Kimi's `$web_search` is a tool call whose arguments are
  echoed back, and charges per search; Z.ai's is a flag; OpenRouter's is `openrouter:web_search`, in
  beta. Each is a different loop, so each is a reason for a module of its own, wanted by a family that
  needs lookups on that company. Until then a lookup goes to a company that has one.
- **Voice and photos on an added company.** The protocol carries an image in a message; whether a given
  model reads one is per model, and a voice recording is not on the protocol at all.
- **The company's reported cost.** OpenRouter returns what a call cost; the daily limit counts the
  estimate from prices, as for every company, so the two can differ.
- **A per-company monthly limit and "Use for everything".** The models-page redesign
  (`docs/MODELS_PAGE.md`) would list `companies.every(settings)`; this change adds the company, not that
  page.
- **Anthropic's Messages route or OpenAI's Responses route as a second protocol** for a definition.
  `CompanyDef` has no `protocol` field yet; one would be added with its adapter, in the same migration
  of settings, when a company needs it.
