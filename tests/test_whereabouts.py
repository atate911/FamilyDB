"""Where the family is: a shared location, a named place, and travel measured from there."""

from datetime import timedelta
from types import SimpleNamespace

from familydb import whereabouts
from familydb.app import App
from familydb.base.dates import utc_iso
from familydb.channels.telegram import location_from_update
from familydb.integrations.geocode import GeoPoint
from familydb.store import db, ideas, locations, members, messages, places
from familydb.suggest.engine import run
from familydb.suggest.types import SuggestInput
from tests.conftest import NOW_ISO

# Home is set in full_settings at 45.63, -122.67. Downtown Portland is about 13 km south.
DOWNTOWN = (45.519, -122.679)


class Places:
    """A geocoder that knows a few names and counts what it was asked."""

    def __init__(self, **known):
        self.known = known
        self.asked = []

    def geocode(self, query):
        self.asked.append(query)
        found = self.known.get(query)
        return GeoPoint(*found, query, "test") if found else None

    def reverse(self, lat, lon):
        self.asked.append((round(lat, 3), round(lon, 3)))
        return "Old Town, Portland" if abs(lat - DOWNTOWN[0]) < 0.01 else None


def _share(app, conn, *, live=False, user="1001"):
    return whereabouts.share(
        app,
        conn,
        channel="telegram",
        channel_user_id=user,
        chat_id="1001",
        lat=DOWNTOWN[0],
        lon=DOWNTOWN[1],
        live=live,
    )


def _cafe_downtown(conn):
    with db.transaction(conn):
        idea = ideas.insert(conn, title="Coffee downtown", kind="restaurant", now=NOW_ISO)
        place = places.insert(
            conn,
            name="Coffee downtown",
            now=NOW_ISO,
            last_checked_at=NOW_ISO,
            lat=45.520,
            lon=-122.677,
            travel_minutes=25,
            travel_km=16.0,
            hours={"sun": [{"open": "07:00", "close": "22:00"}]},
        )
        ideas.update(conn, idea.id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)
    return idea


def test_a_share_is_kept_confirmed_once_and_forgotten(full_settings, clock, conn, family):
    geocoder = Places()
    app = App(full_settings, clock, geocoder=geocoder)
    first = _share(app, conn, live=True)
    assert first is not None and "Got it (Old Town, Portland)" in first.text
    assert locations.get(conn, family["sam"].id).label == "Old Town, Portland"
    assert messages.get(conn, first.out_message_id).text == first.text  # delivered like any reply
    assert _share(app, conn, live=True) is None  # the live location moving: no second word
    assert len(geocoder.asked) == 1  # and the same place is not looked up again
    assert whereabouts.current(conn, family["sam"].id, clock.now()) is not None
    assert whereabouts.current(conn, family["sam"].id, clock.now() + timedelta(hours=4)) is None
    assert _share(app, conn, user="9999") is None  # a stranger's location is not kept
    clock.advance(timedelta(days=2))
    _share(app, conn, user="1002")  # the next share clears anything over a day old
    assert locations.get(conn, family["sam"].id) is None


def test_telegram_location_updates_are_read(settings):
    update = SimpleNamespace(
        effective_message=SimpleNamespace(
            location=SimpleNamespace(latitude=45.5, longitude=-122.6, live_period=900)
        ),
        effective_user=SimpleNamespace(id=1001),
        effective_chat=SimpleNamespace(id=-42),
    )
    shared = location_from_update(update)
    assert shared.live and shared.chat_id == "-42" and shared.lat == 45.5
    update.effective_message = SimpleNamespace(location=None, text="hi")
    assert location_from_update(update) is None


def test_open_now_after_sharing_measures_from_there(full_settings, clock, conn, family):
    ctx = _ctx(full_settings, clock, conn, family)
    cafe = _cafe_downtown(conn)
    at_home = run(ctx, SuggestInput(window="now", question="?", discover=False))
    assert at_home.travel_from == "home"
    assert "about 25 min drive (estimate)" in _reasons(at_home, cafe.id)
    _share(App(full_settings, clock, geocoder=Places()), conn)
    out = run(ctx, SuggestInput(window="now", question="?", discover=False))
    assert out.travel_from == "Sam's location (Old Town, Portland), 0 min ago"
    assert "under 5 min from Old Town, Portland (estimate)" in _reasons(out, cafe.id)
    # Not for a question about the weekend: where Sam is now says nothing about Saturday.
    later = run(ctx, SuggestInput(window="this_weekend", question="?", discover=False))
    assert later.travel_from == "home"


def test_a_named_place_is_looked_up_near_home(full_settings, clock, conn, family):
    geocoder = Places(**{"Main St": (40.0, -75.0), "Main St, Vancouver, WA": (45.63, -122.66)})
    ctx = _ctx(full_settings, clock, conn, family, geocoder=geocoder)
    out = run(ctx, SuggestInput(window="now", near="Main St", question="?", discover=False))
    # The first match was on the other side of the country; the local one was asked for next.
    assert geocoder.asked == ["Main St", "Main St, Vancouver, WA"]
    assert out.travel_from == "Main St"
    lost = run(ctx, SuggestInput(window="now", near="Atlantis", question="?", discover=False))
    assert lost.travel_from == "home"
    assert "could not place 'Atlantis', so travel is from home" in lost.skipped_checks


def test_here_without_a_share_says_so(full_settings, clock, conn, family):
    ctx = _ctx(full_settings, clock, conn, family)
    out = run(ctx, SuggestInput(window="now", near="near me", question="?", discover=False))
    assert out.travel_from == "home"
    assert any("no location shared" in note for note in out.skipped_checks)


def test_discovery_searches_near_where_the_phone_is(full_settings, clock, conn, family):
    from familydb.suggest.context import build_context
    from familydb.suggest.discover import render_discover_request
    from familydb.suggest.origin import resolve
    from familydb.suggest.types import Constraints

    ctx = _ctx(full_settings, clock, conn, family)
    _share(App(full_settings, clock, geocoder=Places()), conn)
    context = build_context(ctx, (clock.today(), clock.today()))
    context.origin, _ = resolve(ctx, "", "now")
    asked = render_discover_request(context, Constraints(), full_settings)
    assert "They are near: Old Town, Portland (45.519, -122.679)." in asked


def _ctx(settings, clock, conn, family, geocoder=None):
    from familydb.tools import ToolContext

    return ToolContext(
        conn=conn,
        settings=settings,
        clock=clock,
        member=family["sam"],
        geocoder=geocoder or Places(),
    )


def _reasons(result, idea_id):
    return next(c.reasons for c in result.candidates if c.idea_id == idea_id)


def test_a_position_is_deleted_after_a_day_even_if_nobody_shares_again(
    full_settings, clock, conn, family
) -> None:
    from familydb.jobs.scheduler import job_specs

    app = App(full_settings, clock, geocoder=Places())
    _share(app, conn)
    clock.advance(timedelta(hours=23))
    assert whereabouts.forget_old(app) == 0  # still within its day
    clock.advance(timedelta(hours=2))
    assert whereabouts.forget_old(app) == 1
    assert locations.get(conn, family["sam"].id) is None
    # and the scheduler runs it on its own, without anyone sharing
    assert any(spec.func is whereabouts.forget_old for spec in job_specs(app))


# -- a forgotten place name goes from what still held it

NAME = "Old Town, Portland"


def _where_the_name_went(conn, when):
    """A kept turn, a tool result and a logged suggestion that carry the place name, as a turn
    made while the location was fresh would have left them."""
    from familydb.store import ai_texts, calls, suggestions

    stamp = utc_iso(when)
    line = f"Sam's location, from their phone 4 min ago: {NAME} (45.5190, -122.6790)."
    with db.transaction(conn):
        text = ai_texts.record(
            conn,
            call_id=None,
            message_id=None,
            turn="t1",
            iteration=1,
            kind="chat",
            about=None,
            provider="anthropic",
            model="m",
            error=None,
            system=None,
            tools=None,
            request=f"[user]\n{line}",
            reply=f"Near {NAME}, then.",
            now=when,
        )
        tool = calls.log_tool_call(
            conn,
            message_id=None,
            iteration=1,
            tool_use_id="x",
            tool_name="suggest",
            input={"near": "here"},
            output=f'{{"travel_from":"Sam\'s location ({NAME}), 4 min ago"}}',
            is_error=False,
            duration_ms=1,
            now=stamp,
        )
        suggestion = suggestions.insert(
            conn,
            asked_by=None,
            window_start=None,
            window_end=None,
            candidates=[{"reasons": [f"under 5 min from {NAME} (estimate)"]}],
            web_finds=[],
            now=stamp,
        ).id
    return text, tool, suggestion


def _everything_kept(conn, text, tool, suggestion):
    return (
        *conn.execute("SELECT request, reply FROM ai_texts WHERE id = ?", (text,)).fetchone(),
        conn.execute("SELECT output FROM tool_calls WHERE id = ?", (tool,)).fetchone()[0],
        conn.execute("SELECT candidates FROM suggestions WHERE id = ?", (suggestion,)).fetchone()[
            0
        ],
    )


def test_a_forgotten_place_name_is_taken_out_of_the_reply_and_the_kept_texts(
    full_settings, clock, conn, family
):
    from familydb.store import place_names

    app = App(full_settings, clock, geocoder=Places())
    reply = _share(app, conn)
    assert NAME in reply.text
    kept = _where_the_name_went(conn, clock.now())
    clock.advance(timedelta(hours=23))
    assert whereabouts.forget_old(app) == 0  # its day is not over: the name is still in use
    assert NAME in messages.get(conn, reply.out_message_id).text
    assert all(NAME in words for words in _everything_kept(conn, *kept))
    clock.advance(timedelta(hours=2))
    assert whereabouts.forget_old(app) == 1
    said = messages.get(conn, reply.out_message_id).text
    assert NAME not in said and said == reply.text.replace(f" ({NAME})", "")
    for words in _everything_kept(conn, *kept):
        assert NAME not in words and place_names.GONE in words
    assert conn.execute("SELECT count(*) FROM place_names").fetchone()[0] == 0
    assert whereabouts.forget_old(app) == 0  # once


def test_a_name_somebody_else_s_location_still_carries_stays_for_now(
    full_settings, clock, conn, family
):
    app = App(full_settings, clock, geocoder=Places())
    sam = _share(app, conn)
    clock.advance(timedelta(hours=23))
    _share(app, conn, user="1002")  # the same place, an hour before Sam's is forgotten
    clock.advance(timedelta(hours=2))
    assert whereabouts.forget_old(app) == 1  # Sam's location goes
    assert NAME in messages.get(conn, sam.out_message_id).text  # Alex's still carries the name
    clock.advance(timedelta(hours=23))
    assert whereabouts.forget_old(app) == 1
    assert NAME not in messages.get(conn, sam.out_message_id).text


def test_a_moving_live_location_names_each_new_place_once_and_forgets_them_all(
    full_settings, clock, conn, family
):
    app = App(full_settings, clock, geocoder=Places())
    _share(app, conn, live=True)
    _share(app, conn, live=True)  # the same place: no second note
    assert conn.execute("SELECT count(*) FROM place_names").fetchone()[0] == 1
    app.geocoder.reverse = lambda lat, lon: "Pearl District, Portland"
    whereabouts.note(app, conn, family["sam"].id, 45.53, -122.68)  # the page's position
    assert conn.execute("SELECT count(*) FROM place_names").fetchone()[0] == 2
    clock.advance(timedelta(days=2))
    whereabouts.forget_old(app)
    assert conn.execute("SELECT count(*) FROM place_names").fetchone()[0] == 0


def test_taking_somebody_off_takes_the_names_of_their_places_out_too(
    full_settings, clock, conn, family
):
    app = App(full_settings, clock, geocoder=Places())
    reply = _share(app, conn)
    kept = _where_the_name_went(conn, clock.now())
    with db.transaction(conn):
        members.erase(conn, family["sam"].id)
    assert NAME not in messages.get(conn, reply.out_message_id).text
    assert all(NAME not in words for words in _everything_kept(conn, *kept))
    assert conn.execute("SELECT count(*) FROM place_names").fetchone()[0] == 0
