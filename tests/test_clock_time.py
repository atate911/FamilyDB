"""Times as the family reads them: 12-hour, "9 am", while what is stored and sent stays 24-hour."""

from __future__ import annotations

from datetime import datetime, time

import pytest

from familydb.dates import clock_time, hour_words, spoken_times

NB = chr(0xA0)  # a no-break space


@pytest.mark.parametrize(
    ("given", "said"),
    [
        ("00:00", f"12{NB}am"),
        ("09:12", f"9:12{NB}am"),
        ("12:00", f"12{NB}pm"),
        ("12:30", f"12:30{NB}pm"),
        ("13:00", f"1{NB}pm"),
        ("2026-10-04T18:30", f"6:30{NB}pm"),
        ("2026-10-04T18:30-07:00", f"6:30{NB}pm"),  # an offset after the minutes is not the time
        (time(7, 5), f"7:05{NB}am"),
        (datetime(2026, 10, 4, 23, 59), f"11:59{NB}pm"),
    ],
)
def test_a_time_is_said_in_twelve_hours(given, said) -> None:
    assert clock_time(given) == said


def test_an_hour_on_the_dot_has_no_minutes() -> None:
    assert [hour_words(h) for h in (0, 7, 12, 21)] == [
        f"12{NB}am",
        f"7{NB}am",
        f"12{NB}pm",
        f"9{NB}pm",
    ]


def test_words_the_engine_made_are_said_in_twelve_hours() -> None:
    said = spoken_times("can go 15:42-16:48 today, daylight until 19:30, open 06:00-24:00")
    assert said == (
        f"can go 3:42{NB}pm to 4:48{NB}pm today, daylight until 7:30{NB}pm, "
        f"open 6{NB}am to 12{NB}am"
    )
    assert spoken_times("task #12, 1:05 long, v0.2.0") == "task #12, 1:05 long, v0.2.0"
