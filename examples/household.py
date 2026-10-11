"""The example household: the Okafor-Lindqvists of Portland, on Friday 16 October 2026 at 5:02 pm.

Sam (who runs it) and Alex, Theo (13) and Maya (11). Everything in it is made up, the places
included; addresses are on streets that do not exist and links go to `.example` domains, which
reach nobody. What there is was chosen so that every page has something true to show: a pick for
tonight and the weekend, a plan to rate, a kid's ask and a pitch, a late reminder, a list, things
on near home, outings with faces, one from this time last year, and a conversation with Vera.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from familydb import family as rules
from familydb.app import App
from familydb.base.clock import FixedClock
from familydb.base.config import Settings
from familydb.integrations.events import FoundEvent
from familydb.integrations.open_meteo import DayForecast
from familydb.store import (
    db,
    finds,
    ideas,
    lists,
    members,
    memories,
    messages,
    outcomes,
    pins,
    places,
    plans,
    tasks,
    wishes,
)

TZ = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 10, 16, 17, 2, tzinfo=TZ)  # Friday, a little after five
TODAY = NOW.date()
PASSWORDS = {
    "Sam": "sam keeps the family list",
    "Alex": "alex likes long walks",
    "Theo": "theo plays left wing",
    "Maya": "maya draws dragons",
}
HOME = (45.5152, -122.6784)
# A question asked from Eat that she answered, and an instruction from Do she carried out: their
# messages' ids, which the page reads from the address to show her reply or a receipt.
REPLY_ON_EAT = "e0a1b2c3d4e5f60718293a4b5c6d7e8f"
RECEIPT_ON_DO = "d0c1b2a3948576a6b7c8d9e0f1a2b3c4"
EVERY_DAY = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def iso(moment: datetime) -> str:
    """A local moment as the stores keep a timestamp: UTC, to the second, with a Z."""
    return moment.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(days: float = 0, hours: float = 0) -> str:
    return iso(NOW - timedelta(days=days, hours=hours))


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)


class Forecast:
    """The week's weather as Open-Meteo would give it: dry tomorrow, rain on Sunday."""

    def __init__(self) -> None:
        sky = [
            (3, "overcast", 15.0, 9.0, 20, 0.0),
            (1, "mainly clear", 16.0, 8.0, 5, 0.0),
            (61, "light rain", 13.0, 9.0, 80, 7.5),
            (2, "partly cloudy", 14.0, 7.0, 15, 0.0),
            (3, "overcast", 13.0, 8.0, 35, 0.4),
            (63, "rain", 12.0, 8.0, 85, 11.0),
            (2, "partly cloudy", 14.0, 6.0, 10, 0.0),
            (1, "mainly clear", 15.0, 6.0, 5, 0.0),
        ]
        self.days = [
            DayForecast(TODAY + timedelta(days=n), code, words, high, low, rain, mm, 444, 1102)
            for n, (code, words, high, low, rain, mm) in enumerate(sky)
        ]

    def daily(self, start: date, end: date) -> list[DayForecast]:
        return [day for day in self.days if start <= day.date <= end]


def settings_for(folder: Path, **more: object) -> Settings:
    """The household's settings: a model key that is never used, a bot token that is never
    dialled, home in Portland. Nothing here reaches the network while pages are drawn."""
    base: dict[str, object] = {
        "provider": "openai",
        "openai_api_key": "sk-example-never-used",
        "familydb_path": folder / "familydb.sqlite3",
        "google_key_path": folder / "no-google-key.json",
        "family_tz": "America/Los_Angeles",
        "home_area": "Portland, OR",
        "home_lat": HOME[0],
        "home_lon": HOME[1],
        "telegram_bot_token": "123456:example-token-never-used",
        "web_password": "the-installer-made-this-one",
        "model_watch": False,
        "choosing": False,
        "web_title": "FamilyDB",
    }
    base.update(more)
    return Settings(_env_file=None, **base)


def app_for(settings: Settings) -> App:
    return App(settings, FixedClock(NOW.replace(tzinfo=None), TZ), weather=Forecast())


@dataclass(frozen=True)
class Family:
    sam: members.Member
    alex: members.Member
    theo: members.Member
    maya: members.Member
    # A question asked from Eat that she answered, and an instruction from Do she carried out:
    # the page addresses that show her reply over the page and a receipt under the box.
    reply_on_eat: str
    receipt_on_do: str


def _place(conn: sqlite3.Connection, idea_id: int, name: str, **fields: object) -> None:
    place = places.insert(conn, name=name, now=ago(days=2), last_checked_at=ago(hours=20), **fields)
    ideas.update(conn, idea_id, {"place_id": place.id, "enrichment": "done"}, now=ago(days=2))


def _hours(open_at: str, close_at: str, *, closed: tuple[str, ...] = ()) -> dict[str, object]:
    return {day: [{"open": open_at, "close": close_at}] for day in EVERY_DAY if day not in closed}


def _said(
    conn: sqlite3.Connection,
    who: members.Member,
    text: str,
    answer: str,
    when: str,
    *,
    chat: str = "web",
    update: str | None = None,
    did: list[dict[str, object]] | None = None,
) -> messages.Message:
    asked = messages.insert_in(
        conn,
        channel="web",
        channel_update_id=update,
        chat_id=chat,
        member_id=who.id,
        text=text,
        now=when,
    )
    messages.mark_processed(conn, asked.id, did or [], now=when)
    stamp = iso(datetime.fromisoformat(when.replace("Z", "+00:00")) + timedelta(seconds=9))
    messages.insert_out(
        conn, channel="web", chat_id=chat, text=answer, reply_to=asked.id, now=stamp
    )
    return asked


def seed(conn: sqlite3.Connection, *, passwords: bool = True) -> Family:
    """Write the household into a fresh, migrated database. Without `passwords` nobody has one
    of their own yet, so the family shares one, as on the kitchen tablet."""
    with db.transaction(conn):
        sam = members.add(
            conn, "Sam", "admin", channel="telegram", channel_user_id="7001", now=ago(200)
        )
        alex = members.add(
            conn, "Alex", "parent", channel="telegram", channel_user_id="7002", now=ago(200)
        )
        theo = members.add(conn, "Theo", "kid", now=ago(200))
        maya = members.add(conn, "Maya", "kid", now=ago(200))
        for kid, born, gender in ((theo, "2013-05-09", "male"), (maya, "2015-03-04", "female")):
            members.update_profile(
                conn,
                kid.id,
                display_name=kid.display_name,
                role="kid",
                active=True,
                channel=None,
                channel_user_id=None,
                birth_date=born,
                gender=gender,
            )
        theo, maya = members.get(conn, theo.id), members.get(conn, maya.id)
        assert theo is not None and maya is not None

        # -- where to eat
        kenji_said = messages.insert_in(
            conn,
            channel="telegram",
            channel_update_id="tg-41",
            chat_id="-1001",
            member_id=sam.id,
            text="we should try Kenji's Ramen on Larkspur, Jess says get the spicy miso",
            now=ago(days=10, hours=2),
        )
        messages.mark_processed(conn, kenji_said.id, [], now=ago(days=10, hours=2))
        kenji = ideas.insert(
            conn,
            title="Kenji's Ramen",
            kind="restaurant",
            description="Jess says get the spicy miso. They do a kids' bowl.",
            location_name="SE Larkspur St",
            suggested_by=sam.id,
            source_message_id=kenji_said.id,
            cost_level=2,
            tags=["ramen", "noodles"],
            now=ago(days=10, hours=2),
        )
        _place(
            conn,
            kenji.id,
            "Kenji's Ramen",
            address="2210 SE Larkspur St, Portland",
            lat=45.5046,
            lon=-122.6345,
            hours=_hours("11:00", "21:00", closed=("mon",)),
            summary="A narrow room with a line past six on Fridays that moves fast. Mild broth "
            "for kids, and they bring small bowls without asking.",
            price_note="about $16 a bowl",
            website="https://kenjis-ramen.example",
            phone="+1 503 555 0142",
            travel_minutes=12,
            travel_km=6.1,
        )
        sol = ideas.insert(
            conn,
            title="Taqueria Sol",
            kind="restaurant",
            cost_level=1,
            tags=["tacos", "mexican"],
            suggested_by=alex.id,
            participants=["whole family"],
            now=ago(days=120),
        )
        _place(
            conn,
            sol.id,
            "Taqueria Sol",
            address="418 N Fernwood Ave, Portland",
            lat=45.5361,
            lon=-122.6612,
            hours=_hours("10:00", "22:00"),
            summary="Counter service, quick, and the al pastor is the thing. Picnic tables out "
            "back.",
            price_note="tacos about $4",
            travel_minutes=7,
            travel_km=3.2,
        )
        fig = ideas.insert(
            conn,
            title="Little Fig",
            kind="restaurant",
            cost_level=3,
            tags=["italian", "date night"],
            participants=["Sam", "Alex"],
            needs_booking=True,
            lead_time_days=7,
            suggested_by=alex.id,
            now=ago(days=21),
        )
        _place(
            conn,
            fig.id,
            "Little Fig",
            address="77 NW Quillan St, Portland",
            lat=45.5260,
            lon=-122.6880,
            hours=_hours("17:00", "22:00", closed=("mon", "tue")),
            summary="Twelve tables and handmade pasta. Book a week ahead for a Saturday.",
            price_note="mains $24 to $32",
            booking_url="https://littlefig.example/book",
            travel_minutes=18,
            travel_km=7.4,
        )
        ideas.insert(
            conn,
            title="Pho Lotus",
            kind="restaurant",
            cost_level=1,
            tags=["pho", "vietnamese"],
            suggested_by=theo.id,
            now=ago(days=1, hours=3),
        )
        bramble = ideas.insert(
            conn,
            title="Bramble Pizza Co.",
            kind="restaurant",
            cost_level=2,
            tags=["pizza"],
            now=ago(days=60),
        )

        # -- things to do
        bounce = ideas.insert(
            conn,
            title="Big Air Bounce Hall",
            kind="outing",
            description="The trampoline place by the river. Maya's friend Ava went for her party.",
            suggested_by=maya.id,
            participants=["Maya", "Theo"],
            setting="indoor",
            cost_level=2,
            duration_min=90,
            duration_max=120,
            now=ago(days=3, hours=1),
        )
        _place(
            conn,
            bounce.id,
            "Big Air Bounce Hall",
            address="1900 SE Waterline Rd, Portland",
            lat=45.4930,
            lon=-122.6610,
            hours=_hours("10:00", "20:00"),
            summary="Open jump in 90-minute slots; grip socks are $3 at the door. Quietest before "
            "noon on Saturdays.",
            price_note="$22 a jumper",
            website="https://bigairbounce.example",
            travel_minutes=15,
            travel_km=8.0,
        )
        kites = ideas.insert(
            conn,
            title="Kites on Hawthorn Butte",
            kind="outing",
            setting="outdoor",
            weather="dry",
            cost_level=0,
            suggested_by=alex.id,
            participants=["whole family"],
            now=ago(days=40),
        )
        pumpkins = ideas.insert(
            conn,
            title="Pumpkin carving at Fernwood Farm",
            kind="seasonal",
            description="Pick your own pumpkin, carve it in the barn. Cider for the grown-ups.",
            happens_from="2026-10-01",
            happens_until="2026-10-31",
            cost_level=1,
            setting="outdoor",
            participants=["whole family"],
            now=ago(days=30),
        )
        ideas.insert(
            conn,
            title="Board game night",
            kind="home",
            cost_level=0,
            participants=["whole family"],
            now=ago(days=9),
        )
        science = ideas.insert(
            conn,
            title="Riverside Science Center: the dinosaur hall",
            kind="outing",
            setting="indoor",
            cost_level=2,
            participants=["whole family"],
            now=ago(days=45),
        )
        maze = ideas.insert(
            conn,
            title="Corn maze at Hollow Creek",
            kind="seasonal",
            happens_from="2026-10-03",
            happens_until="2026-11-01",
            cost_level=1,
            setting="outdoor",
            now=ago(days=14),
        )
        ideas.insert(
            conn,
            title="A day at Pebble Cove",
            kind="day_trip",
            description="The beach with the tide pools, two hours west.",
            setting="outdoor",
            weather="dry",
            cost_level=1,
            now=ago(days=130),
        )
        ideas.insert(
            conn,
            title="Pottery drop-in at Kiln & Co.",
            kind="activity",
            cost_level=2,
            participants=["Maya", "Alex"],
            now=ago(days=105),
        )
        ideas.insert(
            conn,
            title="Ice skating at Glacier Rink",
            kind="activity",
            setting="indoor",
            cost_level=2,
            suggested_by=theo.id,
            participants=["Theo", "Maya"],
            now=ago(days=20),
        )
        ideas.insert(
            conn,
            title="Movie night: a dragon film for Maya",
            kind="home",
            cost_level=0,
            now=ago(days=5),
        )
        # Presents: kept from every kid, and from the grown-up they are for.
        ideas.insert(
            conn,
            title="Wool scarf for Alex",
            kind="gift",
            participants=["Alex"],
            suggested_by=sam.id,
            now=ago(days=12),
        )
        ideas.insert(
            conn,
            title="Lego set for Theo's birthday",
            kind="gift",
            participants=["Theo"],
            suggested_by=alex.id,
            now=ago(days=20),
        )

        # -- the calendar (plans kept here; no Google Calendar connected)
        plans.insert(
            conn,
            title="Swim lesson",
            start="2026-10-16T16:30",
            end="2026-10-16T17:15",
            all_day=False,
            idea_id=None,
            location="Eastside pool",
        )
        plans.insert(
            conn,
            title="Theo's soccer game",
            start="2026-10-17T09:00",
            end="2026-10-17T10:30",
            all_day=False,
            idea_id=None,
            location="Laurel Park field 2",
        )
        plans.insert(
            conn,
            title="Dinner at Grandma Ruth's",
            start="2026-10-18T12:30",
            end="2026-10-18T15:00",
            all_day=False,
            idea_id=None,
        )
        plans.insert(
            conn,
            title="Dentist: Theo",
            start="2026-10-21T15:30",
            end="2026-10-21T16:15",
            all_day=False,
            idea_id=None,
            location="Brightside Dental",
        )
        plans.insert(
            conn,
            title="Pumpkin carving at Fernwood Farm",
            start="2026-10-24T10:00",
            end="2026-10-24T13:00",
            all_day=False,
            idea_id=pumpkins.id,
            location="Fernwood Farm",
        )
        plans.insert(
            conn,
            title="Riverside Science Center",
            start="2026-10-03T10:00",
            end="2026-10-03T14:00",
            all_day=False,
            idea_id=science.id,
        )
        kites_plan = plans.insert(
            conn,
            title="Kites on Hawthorn Butte",
            start="2026-10-10T13:00",
            end="2026-10-10T15:30",
            all_day=False,
            idea_id=kites.id,
        )

        # -- what we did
        went = [
            (kites.id, kites_plan.id, "2026-10-10", 9, True, "Theo's kite finally flew.", alex.id),
            (sol.id, None, "2026-10-04", 9, True, "Quick, cheap, everybody happy.", sam.id),
            (bramble.id, None, "2026-09-19", 6, None, "Loud on a Saturday night.", sam.id),
            (sol.id, None, "2026-09-12", 8, True, None, alex.id),
            (pumpkins.id, None, "2025-10-18", 9, True, "The kids want this every year.", sam.id),
            (maze.id, None, "2025-10-25", 7, True, "Maya was scared for about a minute.", alex.id),
        ]
        for idea_id, plan_id, day, rating, again, notes, by in went:
            outcomes.insert(
                conn,
                idea_id=idea_id,
                plan_id=plan_id,
                happened_on=day,
                rating=rating,
                would_repeat=again,
                notes=notes,
                recorded_by=by,
                now=iso(local(date.fromisoformat(day), 20)),
            )
        # Each outing counted on its idea, oldest first, as record_outcome would have.
        so_far: dict[int, list[int]] = {}
        for idea_id, _, day, rating, *_ in sorted(went, key=lambda one: one[2]):
            so_far.setdefault(idea_id, []).append(rating)
            ideas.apply_outcome(
                conn,
                idea_id,
                happened_on=day,
                avg_rating=sum(so_far[idea_id]) / len(so_far[idea_id]),
                now=iso(local(date.fromisoformat(day), 20)),
            )
        # The pumpkins came round again this year, and Bramble was not worth going back to.
        ideas.update(conn, pumpkins.id, {"status": "planned"}, now=ago(days=2))
        ideas.update(conn, bramble.id, {"status": "idea"}, now=ago(days=27))

        # -- reminders and things to do
        def todo(title: str, owner: members.Member | None, due: datetime | None, key: str, **more):
            return tasks.insert(
                conn,
                title=title,
                notes=more.pop("notes", ""),
                owner_id=owner.id if owner else None,
                due_at=iso(due) if due else None,
                preferred_window=more.pop("window", ""),
                operation_key=f"example-{key}",
                channel="web",
                chat_id="web",
                now=more.pop("made", ago(days=5)),
                **more,
            )

        todo("Book flu shots for everyone", alex, local(date(2026, 10, 14), 17), "flu")
        todo("Pay the soccer fees", sam, local(TODAY, 20), "fees", notes="$85, the club's site")
        towels = todo("Buy paper towels", sam, local(date(2026, 10, 18), 10), "towels")
        tasks.add_reminder(conn, towels, iso(local(date(2026, 10, 18), 10)))
        todo("Return the library books", maya, local(date(2026, 10, 17), 16), "library")
        bins = todo(
            "Take the bins out",
            theo,
            local(date(2026, 10, 22), 19),
            "bins",
            repeat={
                "repeat_every": 1,
                "repeat_unit": "week",
                "repeat_from": "schedule",
                "repeat_anchor": iso(local(date(2026, 10, 22), 19)),
            },
        )
        tasks.add_reminder(conn, bins, iso(local(date(2026, 10, 22), 19)))
        todo("Call about the gutter", alex, None, "gutter", window="some Saturday morning")
        # Everyone's, so a grown-up may say I'll handle it: one late, one for some weekend.
        todo("Sign Maya's field trip form", None, local(date(2026, 10, 15), 20), "form")
        todo("Fix the wobbly kitchen chair", None, None, "chair", window="some weekend")

        # -- lists
        for name, things in (
            ("shopping", ["milk", "eggs", "apples", "coffee beans", "tortillas", "cheddar"]),
            ("costco", ["paper towels", "olive oil", "dish soap"]),
            ("camping", ["tent stakes", "headlamps"]),
        ):
            ref = lists.list_id(conn, name, ago(days=20))
            for n, thing in enumerate(things):
                # Who put each there shows at the end of its row.
                lists.add(conn, ref, thing, by=(alex, sam)[n % 2].id, now=ago(days=2))

        # -- the kids' wish lists
        wishes.insert(
            conn,
            member_id=maya.id,
            title="Roller skates",
            topic="roller skates",
            occasion=None,
            rank=1,
            now=ago(days=30),
        )
        sketch = wishes.insert(
            conn,
            member_id=maya.id,
            title="Sketchbook with thick paper",
            topic="sketchbook",
            occasion=None,
            rank=2,
            now=ago(days=2),
        )
        wishes.update(
            conn, sketch.id, {"status": "turned_away", "parent_review": "asked"}, now=ago(days=2)
        )
        wishes.insert(
            conn,
            member_id=maya.id,
            title="Art markers, the 48 set",
            topic="markers",
            occasion="christmas",
            rank=1,
            now=ago(days=12),
        )
        wishes.insert(
            conn,
            member_id=maya.id,
            title="Sushi for my birthday",
            topic="sushi",
            occasion="birthday",
            rank=1,
            now=ago(days=40),
        )
        wishes.insert(
            conn,
            member_id=theo.id,
            title="Over-ear headphones",
            topic="headphones",
            occasion=None,
            rank=1,
            now=ago(days=18),
        )
        wishes.insert(
            conn,
            member_id=theo.id,
            title="A new skateboard deck",
            topic="skateboard",
            occasion="christmas",
            rank=1,
            now=ago(days=25),
        )
        cleats = wishes.insert(
            conn,
            member_id=theo.id,
            title="Soccer cleats, size 7",
            topic="cleats",
            occasion=None,
            rank=2,
            now=ago(days=9),
        )
        wishes.update(conn, cleats.id, {"status": "granted"}, now=ago(days=4))

        # -- what Vera knows
        for who, category, fact, firm in (
            (theo, "health", "allergic to peanuts", True),
            (maya, "food", "doesn't eat meat", True),
            (alex, "routine", "likes to be home by 9 on school nights", False),
            (None, "activities", "the kids love anything with animals", False),
            (sam, "places", "hates waiting in long lines", False),
        ):
            memories.insert(
                conn,
                member_id=who.id if who else None,
                category=category,
                fact=fact,
                firm=firm,
                inferred=False,
                until=None,
                source_message_id=None,
                said_by=sam.id,
                now=ago(days=30),
            )

        # -- what is on near home, as the family's calendars list it
        def listed(source: str, *events: FoundEvent) -> None:
            finds.upsert_many(conn, source, "feed", events, tz=TZ, now=ago(hours=5))

        listed(
            "feed:https://cedarpark.example/events.ics",
            FoundEvent(
                external_id="lanterns-2026",
                title="Lantern walk at Cedar Park",
                starts=local(date(2026, 10, 17), 18),
                ends=local(date(2026, 10, 17), 20),
                venue="Cedar Park, by the pond",
                url="https://cedarpark.example/lantern-walk",
                price_note="Free",
                summary="Bring a lantern or make one at the craft tent from 5:30. Hot cider by "
                "the pond, and a story walk for little ones.",
                category="Family",
            ),
            FoundEvent(
                external_id="harvest-2026",
                title="Fall harvest market",
                starts=local(date(2026, 10, 18), 10),
                ends=local(date(2026, 10, 18), 14),
                venue="Fernwood Commons",
                url="https://cedarpark.example/harvest",
                price_note="Free entry",
                summary="Apples, cider pressing and a hay maze for the small ones.",
                category="Market",
            ),
        )
        listed(
            "feed:https://library.example.org/events.ics",
            FoundEvent(
                external_id="clay-1021",
                title="Kids' clay workshop",
                starts=local(date(2026, 10, 21), 16),
                ends=local(date(2026, 10, 21), 17, 30),
                venue="Riverside Library",
                url="https://library.example.org/clay",
                price_note="$12, ages 8 to 14",
                summary="Hand-building with air-dry clay; take it home the same day.",
                category="Workshop",
            ),
            FoundEvent(
                external_id="dragons-1025",
                title="Story hour: dragons",
                starts=local(date(2026, 10, 25), 11),
                venue="Riverside Library",
                url="https://library.example.org/stories",
                price_note="Free",
                category="Kids",
            ),
        )
        listed(
            "feed:https://symphony.example.org/season.ics",
            FoundEvent(
                external_id="pops-1024",
                title="Halloween pops: the family concert",
                starts=local(date(2026, 10, 24), 15),
                ends=local(date(2026, 10, 24), 16, 30),
                venue="Hall of the Riverside Symphony",
                url="https://symphony.example.org/halloween",
                price_note="$25, kids $10",
                summary="Costumes welcome. Spooky film music, an hour and a half with a break.",
                category="Music",
            ),
        )

        # -- the conversations
        tomorrow = _said(
            conn,
            alex,
            "anything for tomorrow evening after soccer?",
            "Tomorrow's free from noon. The lantern walk at Cedar Park starts at 6 and it's "
            "free; it should stay dry. Or Kenji's Ramen is 12 minutes away and open till 9.",
            ago(hours=2),
        )
        # Sam kept that one at hand: the top of Chat, and of her column on a desk.
        kept = messages.replies_to(conn, tomorrow.id)[-1]
        pins.pin(conn, sam.id, kept.id, now=ago(hours=1.5))
        reply_on_eat = REPLY_ON_EAT
        _said(
            conn,
            sam,
            "somewhere the kids can eat that isn't pizza?",
            "Taqueria Sol: 7 minutes, open till 10, and Maya can have the bean and cheese. You "
            "all gave it a 9 two weeks ago. Kenji's does a mild kids' bowl too.",
            ago(hours=0.02),
            update=reply_on_eat,
        )
        receipt_on_do = RECEIPT_ON_DO
        _said(
            conn,
            sam,
            "save board game night with the Patels for a rainy Sunday",
            "Saved #19 Board game night with the Patels, for a rainy Sunday.",
            ago(hours=0.01),
            update=receipt_on_do,
            did=[{"tool": "add_idea", "ok": True}],
        )
        maya_chat = f"member:{maya.id}"
        _said(
            conn,
            maya,
            "can we go to the bounce place this weekend??",
            "I've told Sam and Alex you'd like Big Air Bounce Hall. Saturday after Theo's soccer "
            "is free, so it's a good time to ask!",
            ago(days=3, hours=1),
            chat=maya_chat,
        )
        _said(
            conn,
            maya,
            "i'd like a sketchbook with thick paper",
            "Lovely. I've asked a grown-up about the sketchbook; you'll hear back soon.",
            ago(days=2),
            chat=maya_chat,
        )

        # -- what the model calls cost, as the log has it, for Status
        for day in range(30):
            for _ in range(2 + day % 3):
                conn.execute(
                    "INSERT INTO llm_calls (iteration, model, created_at, input_tokens, "
                    "output_tokens, cost_usd, kind, provider) VALUES (1, 'gpt-6-luna', ?, 4200, "
                    "180, 0.0031, 'chat', 'openai')",
                    (ago(days=day, hours=3),),
                )
    for person in (sam, alex, theo, maya) if passwords else ():
        rules.choose_password(conn, person.id, PASSWORDS[person.display_name], now=ago(days=150))
    rules.choose_look(conn, maya.id, "afterglow.auto")
    return Family(sam, alex, theo, maya, reply_on_eat, receipt_on_do)


def first_day(conn: sqlite3.Connection) -> members.Member:
    """A new install: the family on the list and a model key, nothing saved yet."""
    with db.transaction(conn):
        sam = members.add(
            conn, "Sam", "admin", channel="telegram", channel_user_id="7001", now=ago()
        )
        members.add(conn, "Alex", "parent", channel="telegram", channel_user_id="7002", now=ago())
    rules.choose_password(conn, sam.id, PASSWORDS["Sam"], now=ago())
    return sam


def build(
    folder: Path, *, empty: bool = False, shared: bool = False
) -> tuple[App, Family | members.Member]:
    """The household's database in `folder`, migrated and seeded, and an App over it with the
    week's weather and her picks made, as the hourly job would have. `empty` is a new install;
    `shared` is the household before anybody chose a password of their own."""
    from familydb import picks

    folder.mkdir(parents=True, exist_ok=True)
    settings = settings_for(folder)
    conn = db.connect(settings.familydb_path)
    try:
        db.migrate(conn)
        family = first_day(conn) if empty else seed(conn, passwords=not shared)
    finally:
        conn.close()
    app = app_for(settings)
    if not empty:
        picks.refresh(app, force=True)
    return app, family
