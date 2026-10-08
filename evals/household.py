"""The household every case starts from: a family, some ideas with looked-up places, a calendar.

Friday 25 September 2026, 15:30 in Vancouver WA, so "now", "tonight" and "this weekend" all mean
something. Soccer practice at 17:00 today, swim lessons Saturday 09:00-11:00.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from familydb.integrations.open_meteo import DayForecast
from familydb.store import db, ideas, members, memories, outcomes, places, wishes

TZ = ZoneInfo("America/Vancouver")
NOW = datetime(2026, 9, 25, 15, 30)
NOW_ISO = "2026-09-25T22:30:00Z"
EVERY_DAY = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Sunrise and sunset in minutes after midnight, as they are at home those days: dark by 19:04.
FORECAST = [
    DayForecast(date(2026, 9, 25), 1, "mainly clear", 21.0, 11.0, 5, 0.0, 419, 1144),
    DayForecast(date(2026, 9, 26), 2, "partly cloudy", 19.0, 10.0, 10, 0.0, 420, 1142),
    DayForecast(date(2026, 9, 27), 61, "light rain", 14.0, 9.0, 80, 6.5, 422, 1141),
]


@dataclass(frozen=True)
class Household:
    ramen: int
    sushi: int
    hopscotch: int
    hike: int
    cafe: int
    # A word each idea is named by in a reply, whatever else is said of it.
    words: dict[int, str]


def _place(conn, idea_id: int, name: str, *, hours: dict, travel: int, lat: float, lon: float):
    place = places.insert(
        conn,
        name=name,
        now=NOW_ISO,
        last_checked_at=NOW_ISO,
        hours=hours,
        travel_minutes=travel,
        travel_km=round(travel * 0.8, 1),
        lat=lat,
        lon=lon,
    )
    ideas.update(conn, idea_id, {"place_id": place.id, "enrichment": "done"}, now=NOW_ISO)


def seed(conn) -> Household:
    with db.transaction(conn):
        sam = members.add(
            conn, "Sam", "admin", channel="telegram", channel_user_id="1001", now=NOW_ISO
        )
        members.add(conn, "Alex", "parent", channel="telegram", channel_user_id="1002", now=NOW_ISO)
        members.add(
            conn, "the girls", "kid", channel="telegram", channel_user_id="1003", now=NOW_ISO
        )
        # Mia keeps a wish list (docs/WISHES.md) and writes to the bot on her own. A cat was
        # declined ten days ago: pets are locked on her everyday list until 9 October.
        mia = members.add(
            conn, "Mia", "kid", channel="telegram", channel_user_id="1004", now=NOW_ISO
        )
        conn.execute(
            "UPDATE members SET birth_date = '2017-03-14', gender = 'female' WHERE id = ?",
            (mia.id,),
        )
        # Her little sister, so "Chloe got one, that's not fair" is about a sister the family has.
        chloe = members.add(conn, "Chloe", "kid", channel=None, channel_user_id=None, now=NOW_ISO)
        conn.execute(
            "UPDATE members SET birth_date = '2019-07-02', gender = 'female' WHERE id = ?",
            (chloe.id,),
        )
        cat = wishes.insert(
            conn,
            member_id=mia.id,
            title="A cat",
            topic="pet",
            occasion=None,
            rank=1,
            now="2026-09-15T18:00:00Z",
        )
        wishes.update(
            conn,
            cat.id,
            {
                "status": "declined",
                "answered_by": sam.id,
                "answered_at": "2026-09-15T19:00:00Z",
                "locked_until": "2026-10-09T07:00:00Z",
                "refusal_rung": 1,
            },
            now="2026-09-15T19:00:00Z",
        )

        def idea(title: str, kind: str, **fields):
            return ideas.insert(
                conn, title=title, kind=kind, now=NOW_ISO, suggested_by=sam.id, **fields
            ).id

        ramen = idea("Ramen place on Main St", "restaurant", tags=["ramen", "cheap"], cost_level=1)
        _place(
            conn,
            ramen,
            "Menya Main St",
            hours={d: [{"open": "11:30", "close": "21:00"}] for d in EVERY_DAY},
            travel=12,
            lat=45.64,
            lon=-122.66,
        )
        sushi = idea("Sushi Hana", "restaurant", tags=["sushi", "date night"], cost_level=2)
        _place(
            conn,
            sushi,
            "Sushi Hana",
            hours={d: [{"open": "12:00", "close": "21:30"}] for d in EVERY_DAY},
            travel=15,
            lat=45.62,
            lon=-122.67,
        )
        hopscotch = idea(
            "Hopscotch Portland",
            "outing",
            participants=["with the girls"],
            setting="indoor",
            duration_min=120,
            cost_level=2,
        )
        _place(
            conn,
            hopscotch,
            "Hopscotch",
            hours={d: [{"open": "10:00", "close": "20:00"}] for d in EVERY_DAY},
            travel=35,
            lat=45.52,
            lon=-122.66,
        )
        hike = idea("The falls hike", "outing", setting="outdoor", weather="dry", duration_min=180)
        cafe = idea("Board game cafe", "activity", setting="indoor", duration_min=120)
        # How two of them went, for the dossier a stronger call chooses from (suggest/choosing.py):
        # a favorite, and one that was only so-so. Both long enough ago to be offered again.
        for done, day, rating, notes in (
            (sushi, "2026-06-12", 9, "the girls loved it"),
            (cafe, "2026-07-03", 6, "fun, but loud on a Saturday"),
        ):
            outcomes.insert(
                conn,
                idea_id=done,
                plan_id=None,
                happened_on=day,
                rating=rating,
                would_repeat=None,
                notes=notes,
                recorded_by=sam.id,
                now=NOW_ISO,
            )
            ideas.apply_outcome(conn, done, happened_on=day, avg_rating=float(rating), now=NOW_ISO)
        # What the family has told her about itself: one must, one taste.
        for fact, firm in (("no drives over an hour", True), ("the girls love noodles", False)):
            memories.insert(
                conn,
                member_id=None,
                category="places" if firm else "food",
                fact=fact,
                firm=firm,
                inferred=False,
                until=None,
                source_message_id=None,
                said_by=sam.id,
                now=NOW_ISO,
            )
    words = {
        ramen: "ramen",
        sushi: "sushi",
        hopscotch: "hopscotch",
        hike: "falls",
        cafe: "board game",
    }
    return Household(
        ramen=ramen, sushi=sushi, hopscotch=hopscotch, hike=hike, cafe=cafe, words=words
    )


def calendar_events(calendar) -> None:
    calendar.seed(
        "Soccer practice",
        datetime(2026, 9, 25, 17, tzinfo=TZ),
        datetime(2026, 9, 25, 18, tzinfo=TZ),
    )
    calendar.seed(
        "Swim lessons", datetime(2026, 9, 26, 9, tzinfo=TZ), datetime(2026, 9, 26, 11, tzinfo=TZ)
    )
