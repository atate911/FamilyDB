"""Where the family is: a shared location, a named place, and travel measured from there."""

from datetime import timedelta
from types import SimpleNamespace

from familydb import whereabouts
from familydb.app import App
from familydb.channels.telegram import location_from_update
from familydb.integrations.geocode import GeoPoint
from familydb.store import db, ideas, locations, messages, places
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
    assert first is not None and "Got your location (Old Town, Portland)" in first.text
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
