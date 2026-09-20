from familydb.integrations.geocode import (
    NOMINATIM_URL,
    OPEN_METEO_GEOCODE_URL,
    Geocoder,
    GeoPoint,
    estimate_travel,
    haversine_km,
    is_short_name,
)

NOMINATIM_ROW = [{"lat": "45.5262", "lon": "-122.6836", "display_name": "Hopscotch, Portland, OR"}]
METEO_ROW = {
    "results": [
        {
            "latitude": 45.52,
            "longitude": -122.68,
            "name": "Portland",
            "admin1": "Oregon",
            "country": "United States",
        }
    ]
}


def _geocoder(settings, responses, *, times=None):
    calls: list[tuple[str, dict]] = []
    sleeps: list[float] = []
    clock = iter(times or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def fetch(url, headers):
        calls.append((url, headers))
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    geocoder = Geocoder(settings, sleep=sleeps.append, monotonic=lambda: next(clock))
    geocoder._fetch = staticmethod(fetch)  # type: ignore[method-assign]
    return geocoder, calls, sleeps


def test_nominatim_query_and_result(settings) -> None:
    geocoder, calls, _ = _geocoder(settings, [NOMINATIM_ROW])
    point = geocoder.geocode("Hopscotch Portland")
    assert point == GeoPoint(45.5262, -122.6836, "Hopscotch, Portland, OR", "nominatim")
    url, headers = calls[0]
    assert url.startswith(NOMINATIM_URL) and "q=Hopscotch+Portland" in url and "format=json" in url
    assert headers["User-Agent"].startswith("familydb/")


def test_throttle_between_nominatim_calls(settings) -> None:
    # monotonic() is read once after the first call and twice around the second
    geocoder, _, sleeps = _geocoder(settings, [NOMINATIM_ROW, NOMINATIM_ROW], times=[0.0, 0.3, 0.3])
    geocoder.geocode("first place")
    geocoder.geocode("second place")
    assert len(sleeps) == 1 and abs(sleeps[0] - 0.7) < 1e-6


def test_fallback_only_for_short_names(settings) -> None:
    geocoder, calls, _ = _geocoder(settings, [[], METEO_ROW])
    point = geocoder.geocode("Portland")
    assert point is not None and point.source == "open-meteo" and point.label.startswith("Portland")
    assert calls[1][0].startswith(OPEN_METEO_GEOCODE_URL) and "name=Portland" in calls[1][0]
    geocoder, calls, _ = _geocoder(settings, [[]])
    assert geocoder.geocode("1030 NW 12th Ave, Portland") is None
    assert len(calls) == 1  # an address never falls back
    assert is_short_name("Cannon Beach") and not is_short_name("1030 NW 12th Ave")


def test_failures_are_swallowed_and_results_cached(settings) -> None:
    geocoder, calls, _ = _geocoder(settings, [RuntimeError("down"), RuntimeError("also down")])
    assert geocoder.geocode("Portland") is None
    assert len(calls) == 2
    assert geocoder.geocode("  portland ") is None  # cached, no new calls
    assert len(calls) == 2
    assert geocoder.geocode("   ") is None


def test_distance_and_travel_estimate(settings) -> None:
    assert abs(haversine_km(0, 0, 0, 1) - 111.19) < 0.05
    assert estimate_travel(settings, 45.0, -122.0) is None  # no home coordinates
    home = settings.model_copy(update={"home_lat": 0.0, "home_lon": 0.0})
    minutes, km = estimate_travel(home, 0.0, 1.0)
    assert minutes == 173 and abs(km - 144.5) < 0.2
