"""The ideas map: home at the middle, north up, each saved place a dot as far out as its drive
and in its direction, drawn once wide and once narrow from the same figures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from familydb.base.config import Settings
from familydb.integrations.geocode import estimate_travel
from familydb.store.ideas import Idea
from familydb.store.places import Place

# The ideas map: home at the middle, north up. A drive of this many minutes lies this share of the
# way out; the first half hour gets 70% of the radius, so the places a family really goes spread.
MAP_RINGS = (
    (15, "15 min", 0.40),
    (30, "30 min", 0.70),
    (60, "1 h", 0.80),
    (120, "2 h", 0.90),
    (180, "3 h", 1.0),
)
COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Degrees clockwise from north that the second point lies from the first."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    east = math.sin(dlmb) * math.cos(phi2)
    north = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
    return math.degrees(math.atan2(east, north)) % 360


def drive_text(minutes: int) -> str:
    """A drive as people say it: "25 min", "1 h 35 min" (past an hour, to five minutes)."""
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(5 * round(minutes / 5), 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


@dataclass(frozen=True)
class Away:
    """Where a saved place lies from home: the estimated drive and which way."""

    minutes: int
    degrees: float

    @property
    def near(self) -> bool:
        return self.minutes < 5

    @property
    def text(self) -> str:
        """For a card: "about 25 min north-east of home (estimate)"."""
        if self.near:
            return "under 5 min from home (estimate)"
        way = COMPASS[round(self.degrees / 45) % 8]
        return f"about {drive_text(self.minutes)} {way} of home (estimate)"

    @property
    def words(self) -> str:
        """For a plan or an idea in a list: "27 min drive, south"."""
        if self.near:
            return "under 5 min from home"
        return f"{drive_text(self.minutes)} drive, {COMPASS[round(self.degrees / 45) % 8]}"


def away_from_home(place: Place | None, settings: Settings) -> Away | None:
    """How far and which way a place is from home; None unless both are on the map."""
    if place is None or place.lat is None or place.lon is None:
        return None
    if settings.home_lat is None or settings.home_lon is None:
        return None
    estimate = estimate_travel(settings, place.lat, place.lon)
    if estimate is None:
        return None
    return Away(estimate[0], bearing(settings.home_lat, settings.home_lon, place.lat, place.lon))


def map_share(minutes: float) -> float:
    """How far from home, as a share of the map's radius, a drive of this many minutes shows."""
    stops = [(0.0, 0.0)] + [(float(m), share) for m, _, share in MAP_RINGS]
    for (near_min, near), (far_min, far) in pairwise(stops):
        if minutes <= far_min:
            return near + (far - near) * (max(minutes, 0) - near_min) / (far_min - near_min)
    return 1.0


# The two drawings of the map: a wide one for the desktop (names 15 px, drawn at 1:1) and a narrow
# one for the phone (names 14 px). (width, height, centre x, centre y, radius, name size, gap).
MAP_SIZES = {
    "wide": (860, 440, 430, 220, 200.0, 15, 12),
    "narrow": (360, 400, 180, 196, 160.0, 14, 10),
}
# The words that say what an idea is, not where: left off a short name ("Silver Falls hike").
KIND_WORDS = frozenset(
    {"day", "trip", "hike", "weekend", "night", "roller", "rink", "walk", "visit"}
)
NAME_JOINS = (" at ", " in ", " for ", " with ", " to ", " on ")


def short_name(title: str) -> str:
    """What names an idea's dot on the map: "Pumpkin patch at Bi-Mart farm" is "Pumpkin patch",
    "Oaks Park roller rink" is "Oaks Park". The card beside it has the whole title."""
    text = " ".join(title.split())
    lowered = text.lower()
    for join in NAME_JOINS:
        at = lowered.find(join)
        if at > 0:
            head = text[:at]
            if len(head.split()) >= 2 or len(head) >= 8:
                text = head
            break
    words = text.split()[:3]
    while len(words) > 1 and words[-1].lower() in KIND_WORDS:
        words.pop()
    return " ".join(words)


Box = tuple[float, float, float, float]


def _meets(one: Box, other: Box) -> bool:
    return one[0] < other[2] and other[0] < one[2] and one[1] < other[3] and other[1] < one[3]


def _label(
    x: float, y: float, name: str, size: str, taken: list[Box]
) -> tuple[float, float, str, Box]:
    """Where a dot's name goes: beside it on the side with room, above or below at the very edge
    where it would meet the compass letters, and anywhere else that clears the other dots and
    names (`taken`, which the caller adds this one to). Returns its x, y, anchor and box."""
    width, _, cx, cy, radius, text_size, gap = MAP_SIZES[size]
    room = len(name) * text_size * 0.52
    left = x < cx
    beside_left = (x - gap, y + 5, "end")
    beside_right = (x + gap, y + 5, "start")
    candidates = [beside_left, beside_right] if left else [beside_right, beside_left]
    above = [(x - 8, y - 18, "end"), (x + 8, y - 18, "start")]
    below = [(x + 8, y + 22, "start"), (x - 8, y + 22, "end")]
    if abs(x - cx) > radius - 40 and abs(y - cy) < 16:
        # Out at the end of the west-east axis, where the compass letter is: above, or below.
        candidates = above[:1] + below[:1] if left else above[1:] + below[1:]
        if left and x - gap - room < 8:
            candidates = [(x - 12, y + 22, "start")]
        elif not left and x + gap + room > width - 8:
            candidates = [(x + 12, y + 22, "end")]
    else:
        candidates += above + below

    def box(spot: tuple[float, float, float | str]) -> Box:
        lx, ly, anchor = spot[0], spot[1], spot[2]
        left_edge = lx - room if anchor == "end" else lx
        return (left_edge, ly - text_size * 0.8, left_edge + room, ly + text_size * 0.3)

    def fits(spot: tuple[float, float, str]) -> bool:
        one = box(spot)
        return one[0] >= 4 and one[2] <= width - 4 and not any(_meets(one, t) for t in taken)

    chosen = next((c for c in candidates if fits(c)), None)
    if chosen is None:
        chosen = next(
            (c for c in candidates if box(c)[0] >= 4 and box(c)[2] <= width - 4), candidates[0]
        )
    one = box(chosen)
    taken.append(one)
    return round(chosen[0], 1), round(chosen[1], 1), chosen[2], one


def places_map(placed: list[tuple[Idea, Away]]) -> dict[str, Any] | None:
    """The map of how far each idea is from home, drawn at both sizes; None when there is nothing
    to show (no idea has a drive time, or every one is inside the first ring, where the cards say
    all there is to say)."""
    if not placed or max(away.minutes for _, away in placed) <= MAP_RINGS[0][0]:
        return None
    ordered = sorted(placed, key=lambda pair: (pair[1].degrees, pair[1].minutes, pair[0].id))
    plots = {}
    for size, (width, height, cx, cy, radius, _, _) in MAP_SIZES.items():
        rings = [
            {
                "r": round(radius * share, 1),
                "name": name,
                "x": cx + (6 if index % 2 == 0 else -6),
                "y": round(cy - radius * share + 15, 1),
                "anchor": "start" if index % 2 == 0 else "end",
            }
            for index, (_, name, share) in enumerate(MAP_RINGS)
        ]
        dots: list[dict[str, Any]] = []
        for idea, away in ordered:
            reach = radius * map_share(away.minutes)
            degrees = away.degrees
            for _ in range(6):  # ideas in the same direction are spread a few degrees apart
                angle = math.radians(degrees)
                x, y = cx + reach * math.sin(angle), cy - reach * math.cos(angle)
                if all(math.hypot(x - one["x"], y - one["y"]) >= 26 for one in dots):
                    break
                degrees += 5
            dots.append({"x": round(x, 1), "y": round(y, 1), "name": short_name(idea.title)})
        # What a name must stay clear of: home, its name, the compass letters and every dot.
        taken: list[Box] = [
            (cx - 8, cy - 8, cx + 8, cy + 8),
            (cx - 22, cy + 8, cx + 22, cy + 26),
            (cx - 12, cy - radius - 20, cx + 2, cy - radius - 2),
            (cx - 12, cy + radius + 2, cx + 2, cy + radius + 20),
            (cx - radius - 20, cy - 6, cx - radius - 2, cy + 10),
            (cx + radius + 2, cy - 6, cx + radius + 20, cy + 10),
        ]
        taken += [(d["x"] - 9, d["y"] - 9, d["x"] + 9, d["y"] + 9) for d in dots]
        for dot in dots:
            dot["label_x"], dot["label_y"], dot["anchor"], _ = _label(
                dot["x"], dot["y"], dot["name"], size, taken
            )
        plots[size] = {
            "width": width,
            "height": height,
            "cx": cx,
            "cy": cy,
            "radius": radius,
            "rings": rings,
            "axis": f"M{cx} {cy - radius:g}V{cy + radius:g}M{cx - radius:g} {cy}H{cx + radius:g}",
            "compass": [
                ("N", cx - 6, cy - radius - 5, "end"),
                ("S", cx - 6, cy + radius + 15, "end"),
                ("W", cx - radius - 8, cy + 5, "end"),
                ("E", cx + radius + 8, cy + 5, "start"),
            ],
            "dots": dots,
        }
    return {"wide": plots["wide"], "narrow": plots["narrow"], "count": len(ordered)}
