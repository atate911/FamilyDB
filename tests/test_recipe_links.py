"""A pasted recipe link (docs/RECIPES.md): read by this server from the page's recipe block within
minutes, for nothing, and the chat told; a page with none waits for the evening's lookup, which
pays a reader for that page alone; an address this server would not read goes to no model."""

from __future__ import annotations

import json
from pathlib import Path

from familydb.app import App
from familydb.integrations.recipe_page import PageError
from familydb.jobs.enrich import run_enrichment
from familydb.jobs.recipes import run_recipe_links
from familydb.store import db, ideas, messages
from familydb.store import recipes as store
from familydb.tools import ToolContext, build_registry
from tests import fakes

PAGES = Path(__file__).parent / "pages"
LINK = "https://www.seriouseats.com/sheet-pan-chicken-fajitas"
REGISTRY = build_registry()


class Pages:
    """A stand-in for the web: each address answers with a saved page, or refuses."""

    def __init__(self, **answers):
        self.answers = answers
        self.read_from: list[str] = []

    def read(self, url: str) -> str:
        self.read_from.append(url)
        answer = self.answers.get(url)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise PageError("the site could not be reached")
        return (PAGES / answer).read_text()


def _pasted(conn, settings, clock, family, url=LINK, title="Sheet pan chicken fajitas"):
    with db.transaction(conn):
        said = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id=f"u-{url}",
            chat_id="42",
            member_id=family["sam"].id,
            text=url,
            now="2026-09-20T20:00:00Z",
        )
    ctx = ToolContext(
        conn=conn, settings=settings, clock=clock, member=family["sam"], message_id=said.id
    )
    made = REGISTRY.dispatch("add_idea", {"title": title, "kind": "recipe", "url": url}, ctx)
    return json.loads(made.content)


def test_a_link_is_read_by_code_and_the_chat_is_told(settings, clock, conn, family):
    app = App(settings, clock)
    told: list[tuple[str, str]] = []
    app.senders["telegram"] = lambda chat, text: told.append((chat, text))
    made = _pasted(conn, settings, clock, family)
    pages = Pages(**{LINK: "recipe_graph.html"})
    assert run_recipe_links(app, pages=pages) == {"done": 1, "unread": 0, "refused": 0}
    idea = ideas.get(conn, made["id"])
    assert (
        idea.title == "Sheet-Pan Chicken Fajitas"
    )  # the page's name for a title of the link's words
    assert idea.enrichment == "done" and idea.tags == ["mexican", "sheet pan", "weeknight"]
    kept = store.get(conn, made["id"])
    assert kept.filled_by == "page" and kept.serves == 4 and kept.total_minutes == 35
    assert kept.ingredients[3].item == "lime"
    assert told and told[0][0] == "42"
    assert "35 min, serves 4, 5 ingredients, from seriouseats.com" in told[0][1]
    assert conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 0  # no model asked
    # Read once: the next run has nothing to do.
    assert run_recipe_links(app, pages=pages) == {"done": 0, "unread": 0, "refused": 0}
    assert pages.read_from == [LINK]


def test_what_the_family_said_stands_over_the_page(settings, clock, conn, family):
    app = App(settings, clock)
    ctx = ToolContext(conn=conn, settings=settings, clock=clock, member=family["sam"])
    made = json.loads(
        REGISTRY.dispatch(
            "add_idea",
            {"title": "Jo's fajitas", "kind": "recipe", "url": LINK, "recipe": {"serves": 6}},
            ctx,
        ).content
    )
    run_recipe_links(app, pages=Pages(**{LINK: "recipe_graph.html"}))
    kept = store.get(conn, made["id"])
    assert kept.serves == 6 and ideas.get(conn, made["id"]).title == "Jo's fajitas"


def test_a_page_with_no_recipe_waits_for_the_paid_reader(settings, clock, conn, family):
    blog = "https://example.com/our-trip"
    app = App(
        settings.model_copy(update={"web_tools_enabled": True, "lookups_when": "asap"}), clock
    )
    made = _pasted(conn, settings, clock, family, url=blog, title="Grandma's stew")
    assert run_recipe_links(app, pages=Pages(**{blog: "no_recipe.html"})) == {
        "done": 0,
        "unread": 1,
        "refused": 0,
    }
    kept = store.get(conn, made["id"])
    assert kept.fill_note == "no recipe on the page" and not kept.read
    assert ideas.get(conn, made["id"]).enrichment == "pending"
    api = fakes.FakeMessagesAPI(
        fakes.message(
            [
                fakes.tool_use(
                    "tu_1",
                    "save_recipe",
                    {
                        "idea_id": made["id"],
                        "name": "Grandma's beef stew",
                        "ingredients": [
                            {
                                "text": "2 lb beef chuck, cubed",
                                "item": "beef chuck",
                                "amount": "2 lb",
                            }
                        ],
                        "steps": ["Brown the beef.", "Simmer 3 hours."],
                        "total_minutes": 200,
                    },
                )
            ],
            stop_reason="tool_use",
        )
    )
    counts = run_enrichment(app, api=api)
    assert counts["done"] == 1
    kept = store.get(conn, made["id"])
    assert kept.filled_by == "lookup" and kept.ingredients[0].item == "beef chuck"
    assert kept.occasions_guessed == ["slow"]
    request = api.requests[0]["messages"][0]["content"][-1]["text"]
    assert blog in request and "no recipe on the page" in request
    # The title the family gave stands: it was not the link's words.
    assert ideas.get(conn, made["id"]).title == "Grandma's stew"


def test_an_address_this_server_will_not_read_goes_to_no_model(settings, clock, conn, family):
    inside = "http://192.168.1.10/recipe"
    app = App(
        settings.model_copy(update={"web_tools_enabled": True, "lookups_when": "asap"}), clock
    )
    made = _pasted(conn, settings, clock, family, url=inside, title="Router soup")
    pages = Pages(**{inside: PageError("not a public address")})
    assert run_recipe_links(app, pages=pages)["refused"] == 1
    assert ideas.get(conn, made["id"]).enrichment == "failed"
    api = fakes.FakeMessagesAPI()
    run_enrichment(app, api=api)
    assert api.requests == []


def test_switched_off_the_links_wait_for_the_evening(settings, clock, conn, family):
    app = App(settings.model_copy(update={"recipe_links": False}), clock)
    _pasted(conn, settings, clock, family)
    pages = Pages(**{LINK: "recipe_graph.html"})
    assert run_recipe_links(app, pages=pages) == {"done": 0, "unread": 0, "refused": 0}
    assert pages.read_from == []


def test_idle_it_reads_nothing(settings, clock, conn, family):
    pages = Pages()
    assert run_recipe_links(App(settings, clock), pages=pages) == {
        "done": 0,
        "unread": 0,
        "refused": 0,
    }
    assert pages.read_from == []


def test_reading_recipes_has_a_model_of_its_own(settings):
    from familydb.agent import uses

    assert uses.use_of("fill_recipe").key == "recipes"
    follows = uses.answering(settings, "fill_recipe")
    assert follows.model == uses.answering(settings, "enrich").model  # the lookups' until chosen
    chosen = settings.model_copy(
        update={"model_choices": {"recipes": "anthropic:claude-haiku-5-5"}}
    )
    assert uses.answering(chosen, "fill_recipe").model == "claude-haiku-5-5"
    assert uses.answering(chosen, "enrich").model != "claude-haiku-5-5"


def test_reading_recipes_off_keeps_the_link_and_pays_nothing(settings, clock, conn, family):
    blog = "https://example.com/our-trip"
    app = App(
        settings.model_copy(
            update={
                "web_tools_enabled": True,
                "lookups_when": "asap",
                "model_choices": {"recipes": "off"},
            }
        ),
        clock,
    )
    made = _pasted(conn, settings, clock, family, url=blog, title="Grandma's stew")
    run_recipe_links(app, pages=Pages(**{blog: "no_recipe.html"}))
    api = fakes.FakeMessagesAPI()
    assert run_enrichment(app, api=api)["skipped"] == 1
    assert api.requests == []
    idea = ideas.get(conn, made["id"])
    assert idea.enrichment == "skipped" and "reading recipes is off" in idea.enrichment_note
