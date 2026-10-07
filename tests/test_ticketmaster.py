"""Ticketmaster's event search: what is read from an answer, what is sent, and that the key
never shows in an error."""

from __future__ import annotations

from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from familydb.integrations import ticketmaster
from familydb.integrations.ticketmaster import (
    Ticketmaster,
    TicketmasterError,
    geohash,
    parse_events,
)
from tests.conftest import TZ

# The real fetcher, before the tests' guard against the network replaces it.
REAL_FETCH = Ticketmaster.__dict__["_fetch"]


def _event(event_id: str, name: str, start: dict, **extra) -> dict:
    return {"id": event_id, "name": name, "dates": {"start": start}, **extra}


PAGE = {
    "_embedded": {
        "events": [
            _event(
                "G1",
                "Brandi Carlile",
                {
                    "localDate": "2026-10-03",
                    "localTime": "19:30:00",
                    "dateTime": "2026-10-04T02:30:00Z",
                },
                url="https://www.ticketmaster.com/event/G1",
                priceRanges=[{"type": "standard", "currency": "USD", "min": 49.5, "max": 129.0}],
                classifications=[
                    {
                        "segment": {"name": "Music"},
                        "genre": {"name": "Folk"},
                        "subGenre": {"name": "Undefined"},
                    }
                ],
                _embedded={
                    "venues": [
                        {
                            "name": "Moda Center",
                            "address": {"line1": "1 N Center Ct St"},
                            "city": {"name": "Portland"},
                            "location": {"latitude": "45.5316", "longitude": "-122.6668"},
                        }
                    ]
                },
                info="Doors open at 6:30.",
            ),
            _event("G2", "Pumpkin patch", {"localDate": "2026-10-10", "timeTBA": True}),
            _event(
                "G3",
                "Called off",
                {"localDate": "2026-10-11", "localTime": "20:00:00"},
                dates={"start": {"localDate": "2026-10-11"}, "status": {"code": "cancelled"}},
            ),
            _event("G4", "Some day", {"dateTBD": True}),
        ]
    },
    "page": {"size": 100, "totalElements": 4, "totalPages": 1, "number": 0},
}


def test_an_answer_is_read_as_dated_things_near_home() -> None:
    found = {e.external_id: e for e in parse_events(PAGE, tz=TZ)}
    assert set(found) == {"G1", "G2"}  # cancelled and undated left out
    show = found["G1"]
    assert show.starts == datetime(2026, 10, 3, 19, 30, tzinfo=TZ)
    assert (show.venue, show.address) == ("Moda Center", "1 N Center Ct St, Portland")
    assert (show.lat, show.lon) == (45.5316, -122.6668)
    assert show.price_note == "$50 to 129" and show.category == "Music, Folk"
    assert show.summary == "Doors open at 6:30." and not show.all_day
    patch = found["G2"]
    assert (patch.starts, patch.all_day) == (date(2026, 10, 10), True)


def test_a_page_with_nothing_on_is_an_empty_list_and_a_strange_answer_says_so() -> None:
    assert parse_events({"page": {"totalPages": 0}}, tz=TZ) == []
    with pytest.raises(TicketmasterError):
        parse_events(["not", "an", "answer"], tz=TZ)


def test_geohash_is_the_standard_one() -> None:
    assert geohash(57.64911, 10.40744, 11) == "u4pruydqqvj"  # the worked example
    assert geohash(45.64, -122.66, 5) == "c20g8"  # Vancouver, WA


def _client(settings) -> Ticketmaster:
    return Ticketmaster(settings.model_copy(update={"ticketmaster_api_key": "tm-key-123"}))


def test_what_is_sent_is_home_rounded_the_radius_and_the_days(settings) -> None:
    url = _client(settings)._url(
        45.638720, -122.661481, 80, date(2026, 9, 26), date(2026, 9, 27), 0
    )
    query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    assert query["geoPoint"] == geohash(45.64, -122.66)
    assert "latlong" not in query and "45.6387" not in url
    assert (query["radius"], query["unit"], query["sort"]) == ("80", "km", "date,asc")
    assert query["startDateTime"] == "2026-09-26T07:00:00Z"  # midnight in Vancouver, in UTC
    assert query["endDateTime"] == "2026-09-28T07:00:00Z"


def test_it_reads_a_second_page_only_when_there_is_one(settings, monkeypatch) -> None:
    asked = []
    second = {**PAGE, "page": {"totalPages": 3}}
    monkeypatch.setattr(
        Ticketmaster, "_fetch", staticmethod(lambda url: asked.append(url) or second)
    )
    found = _client(settings).events(45.6, -122.6, 80, date(2026, 9, 26), date(2026, 10, 23))
    assert len(asked) == ticketmaster.MAX_PAGES and len(found) == 2 * ticketmaster.MAX_PAGES
    asked.clear()
    monkeypatch.setattr(Ticketmaster, "_fetch", staticmethod(lambda url: asked.append(url) or PAGE))
    _client(settings).events(45.6, -122.6, 80, date(2026, 9, 26), date(2026, 10, 23))
    assert len(asked) == 1


def test_an_error_never_repeats_the_key(settings, monkeypatch) -> None:
    import urllib.error
    import urllib.request

    def refused(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(Ticketmaster, "_fetch", REAL_FETCH)
    monkeypatch.setattr(urllib.request, "urlopen", refused)
    with pytest.raises(TicketmasterError) as caught:
        _client(settings).events(45.6, -122.6, 80, date(2026, 9, 26), date(2026, 9, 27))
    assert "tm-key-123" not in str(caught.value) and "401" in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is not None
    assert "tm-key-123" not in repr(caught.value.args)
