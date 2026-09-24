"""Draw the web page's pixel art: the icon sprite, the favicon and the scenes.

Every picture on the page is drawn here as text, a character per pixel, and written out as SVG
made only of square runs, so it stays crisp at any size and the stylesheet can colour the icons.
Change a drawing here and run it again; never edit the .svg files by hand.

    uv run python scripts/pixels.py

Icons are 12 by 12 and take the colour of the text around them (`currentColor`). The scenes
use the phosphor palette below, which matches the tokens at the top of `static/style.css`.
"""

from __future__ import annotations

import math
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "src" / "familydb" / "web" / "static"

# The phosphor ramp, dimmest to brightest, and the amber second phosphor. Same values as the
# stylesheet's --p1..--p4 and --amber.
PALETTE = {
    "0": "#0b0d16",  # silhouettes against the light
    "1": "#123626",  # the far hill
    "2": "#1f5a35",  # the near hill
    "3": "#3fa565",  # where the light catches, pines
    "4": "#6dff9c",  # phosphor green
    "5": "#eef2ef",  # starlight
    "a": "#ffb84d",  # amber: lit windows
    "y": "#ffd978",  # the sun, top to bottom
    "o": "#ff9459",
    "r": "#ff6b7d",
    "k": "#ff8fc8",  # the kite
    "c": "#5fd4ff",
    "l": "#b69cff",
    "s": "#120e2a",  # the dusk sky, top to bottom
    "t": "#1f1747",
    "u": "#35205f",
    "v": "#552770",
    "w": "#7d3275",
    # The test card: the old colour bars, at three-quarter strength as they were broadcast.
    "G": "#c0c0c0",
    "Y": "#c0c000",
    "C": "#00c0c0",
    "N": "#00c000",
    "M": "#c000c0",
    "R": "#c00000",
    "U": "#0000c0",
    "K": "#101010",
    "I": "#00214c",
    "E": "#ffffff",
    "P": "#32006a",
}

ICONS: dict[str, str] = {
    "home": """
        .....##.....
        ....####....
        ...######...
        ..########..
        .##########.
        ##.#....#.##
        ..#......#..
        ..#..##..#..
        ..#..##..#..
        ..#..##..#..
        ..#..##..#..
        ..########..
    """,
    "chat": """
        ............
        .##########.
        #..........#
        #..........#
        #.##.##.##.#
        #..........#
        #..........#
        .##.#######.
        ..#.#.......
        ..##........
        ..#.........
        ............
    """,
    "idea": """
        ....####....
        ..##....##..
        .#........#.
        .#.#......#.
        .#.#......#.
        ..#......#..
        ...#....#...
        ...######...
        ............
        ...######...
        ....####....
        ............
    """,
    "plans": """
        ..#......#..
        .##########.
        .##########.
        .#........#.
        .#.##..##.#.
        .#.##..##.#.
        .#........#.
        .#.##..##.#.
        .#.##..##.#.
        .#........#.
        .##########.
        ............
    """,
    "todo": """
        ..........##
        .........##.
        #######.##..
        #.....###..#
        #.#..###...#
        #.##.##....#
        #..###.....#
        #...#......#
        #..........#
        #..........#
        ############
        ............
    """,
    "family": """
        ..##........
        .####.......
        .####.......
        ..##.....##.
        ........####
        .####....##.
        ######......
        ######..####
        ######..####
        ######..####
        ######..####
        ............
    """,
    "status": """
        ............
        ....#.......
        ....#.......
        ...#.#......
        ...#.#......
        ##.#.#...###
        .##..#..#...
        .....#..#...
        ......#.#...
        ......##....
        ............
        ............
    """,
    "settings": """
        ....####....
        .##.####.##.
        .##########.
        ..########..
        ####....####
        ####....####
        ####....####
        ####....####
        ..########..
        .##########.
        .##.####.##.
        ....####....
    """,
    "signout": """
        #######.....
        #.....#.....
        #.....#..#..
        #.........#.
        #...#######.
        #...########
        #...#######.
        #.........#.
        #.....#..#..
        #.....#.....
        #######.....
        ............
    """,
    "plus": """
        ............
        .....##.....
        .....##.....
        .....##.....
        .....##.....
        .##########.
        .##########.
        .....##.....
        .....##.....
        .....##.....
        .....##.....
        ............
    """,
    "right": """
        ............
        ......#.....
        ......##....
        ......###...
        ......####..
        ###########.
        ###########.
        ......####..
        ......###...
        ......##....
        ......#.....
        ............
    """,
    "left": """
        ............
        .....#......
        ....##......
        ...###......
        ..####......
        .###########
        .###########
        ..####......
        ...###......
        ....##......
        .....#......
        ............
    """,
    "search": """
        ..####......
        .#....#.....
        #......#....
        #......#....
        #......#....
        #......#....
        .#....#.....
        ..####.##...
        .......###..
        ........###.
        .........###
        ..........#.
    """,
    "pin": """
        ....####....
        ..##....##..
        .#........#.
        .#...##...#.
        .#...##...#.
        .#........#.
        ..#......#..
        ..#......#..
        ...#....#...
        ....#..#....
        .....##.....
        ............
    """,
    "clock": """
        ...######...
        ..#......#..
        .#........#.
        #....#.....#
        #....#.....#
        #....#.....#
        #....####..#
        #..........#
        #..........#
        .#........#.
        ..#......#..
        ...######...
    """,
    "user": """
        ....####....
        ...######...
        ...######...
        ...######...
        ....####....
        ............
        ..########..
        .##########.
        .##########.
        .##########.
        .##########.
        ............
    """,
    "star": """
        .....##.....
        ....####....
        ....####....
        ############
        .##########.
        ..########..
        ...######...
        ..########..
        ..###..###..
        .###....###.
        .##......##.
        ............
    """,
    "restaurant": """
        #.#.#...##..
        #.#.#..###..
        #.#.#..###..
        #####..###..
        .###...###..
        ..#....###..
        ..#.....##..
        ..#.....##..
        ..#.....##..
        ..#.....##..
        ..#.....##..
        ............
    """,
    "show": """
        ............
        ............
        ############
        #...#......#
        #..........#
        .#..#.....#.
        .#........#.
        #...#......#
        #..........#
        ############
        ............
        ............
    """,
    "outing": """
        .....##.....
        ....####....
        ...######...
        ....####....
        ...######...
        ..########..
        ...######...
        ..########..
        .##########.
        .....##.....
        .....##.....
        ....####....
    """,
    "day_trip": """
        ............
        ............
        ...######...
        ..#...#..#..
        .#....#...#.
        ############
        #.#########.
        ############
        ..##....##..
        ..##....##..
        ............
        ............
    """,
    "trip": """
        ............
        ....####....
        ....#..#....
        ############
        #..#....#..#
        #..#....#..#
        #..#....#..#
        #..#....#..#
        #..#....#..#
        ############
        ............
        ............
    """,
    "event": """
        .#..........
        .##########.
        .##########.
        .#########..
        .########...
        .#########..
        .##########.
        .#..........
        .#..........
        .#..........
        .#..........
        ###.........
    """,
    "seasonal": """
        .......#####
        .....##....#
        ....#.....##
        ...#.....#.#
        ..#.....#..#
        ..#....#...#
        .#....#...#.
        .#...#...#..
        .#..#..##...
        .#.#.##.....
        .##.........
        #...........
    """,
    "activity": """
        .....#......
        ....###.....
        ...###.#....
        ..####..#...
        .#########..
        ..#..####...
        ...#.###....
        ....###.....
        .....#......
        ......#.....
        .....#.#....
        ......#.....
    """,
    "spark": """
        .....#......
        .....#......
        .....#......
        ....###.....
        ...#####....
        ###########.
        ...#####....
        ....###.....
        .....#......
        .....#......
        .....#......
        ............
    """,
    "bell": """
        .....##.....
        ....####....
        ...#....#...
        ..#......#..
        ..#......#..
        ..#......#..
        ..#......#..
        .#........#.
        ############
        ............
        .....##.....
        ............
    """,
    "link": """
        ......######
        .........###
        ........##.#
        #####..##..#
        #.....##....
        #....##.....
        #...##...#..
        #........#..
        #........#..
        #........#..
        ##########..
        ............
    """,
    "edit": """
        .........##.
        ........#..#
        .......#..#.
        ......#..#..
        .....#..#...
        ....#..#....
        ...#..#.....
        ..#..#......
        .#..#.......
        .#.#........
        .##.........
        ............
    """,
    "x": """
        ............
        .##......##.
        .###....###.
        ..###..###..
        ...######...
        ....####....
        ....####....
        ...######...
        ..###..###..
        .###....###.
        .##......##.
        ............
    """,
    "check": """
        ............
        ............
        ..........##
        .........##.
        ........##..
        .......##...
        ##....##....
        .##..##.....
        ..####......
        ...##.......
        ............
        ............
    """,
    "key": """
        ............
        ............
        .####.......
        #....#......
        #.##.#######
        #.##.#...#.#
        #....#...#.#
        .####.......
        ............
        ............
        ............
        ............
    """,
    "bot": """
        .##########.
        #..........#
        #.########.#
        #.##.##.##.#
        #.########.#
        #.#.####.#.#
        #.##....##.#
        #.########.#
        #..........#
        .##########.
        ....####....
        ..########..
    """,
    "plug": """
        ...#....#...
        ...#....#...
        .##########.
        .#........#.
        .#........#.
        ..#......#..
        ...######...
        .....##.....
        .....##.....
        ......##....
        .......##...
        ........##..
    """,
    "hourglass": """
        ############
        .#........#.
        ..#......#..
        ...#....#...
        ....#..#....
        .....##.....
        .....##.....
        ....#..#....
        ...#.##.#...
        ..#.####.#..
        .#.######.#.
        ############
    """,
    "warning": """
        .....##.....
        .....##.....
        ....#..#....
        ....#..#....
        ...#.##.#...
        ...#.##.#...
        ..#..##..#..
        ..#......#..
        .#...##...#.
        .#........#.
        ############
        ............
    """,
    "heart": """
        ............
        ..##....##..
        .####..####.
        ############
        ############
        ############
        .##########.
        ..########..
        ...######...
        ....####....
        .....##.....
        ............
    """,
    "send": """
        #...........
        ###.........
        #####.......
        #######.....
        #########...
        ..#########.
        ..#########.
        #########...
        #######.....
        #####.......
        ###.........
        #...........
    """,
    "locate": """
        .....##.....
        ...######...
        ..#..##..#..
        .#........#.
        .#........#.
        ####.##.####
        ####.##.####
        .#........#.
        .#........#.
        ..#..##..#..
        ...######...
        .....##.....
    """,
    "list": """
        ............
        ##.#########
        ##.#########
        ............
        ............
        ##.#########
        ##.#########
        ............
        ............
        ##.#########
        ##.#########
        ............
    """,
    "grid": """
        ##.##.##.##.
        ##.##.##.##.
        ............
        ##.##.##.##.
        ##.##.##.##.
        ............
        ##.##.##.##.
        ##.##.##.##.
        ............
        ##.##.##.##.
        ##.##.##.##.
        ............
    """,
    "undo": """
        ............
        ...#........
        ..##........
        .#########..
        ..##......#.
        ...#.......#
        ...........#
        ...........#
        ..........#.
        .#########..
        ............
        ............
    """,
    "sun": """
        .....##.....
        .#...##...#.
        ..#......#..
        ....####....
        ...######...
        ##.######.##
        ##.######.##
        ...######...
        ....####....
        ..#......#..
        .#...##...#.
        .....##.....
    """,
    "sparkles": """
        ........#...
        ........#...
        ..#....###..
        ..#...#####.
        .###...###..
        #####...#...
        .###....#...
        ..#.........
        ..#...#.....
        .....###....
        ......#.....
        ............
    """,
    "person_plus": """
        ..####......
        .######.....
        .######.....
        .######.....
        ..####......
        ............
        .######...#.
        ########.###
        ########..#.
        ########....
        ########....
        ............
    """,
    "coin": """
        ...######...
        ..#......#..
        .#...#....#.
        #...####...#
        #..#.#.....#
        #...###....#
        #....#.#...#
        #..####....#
        #....#.....#
        .#........#.
        ..#......#..
        ...######...
    """,
    "door": """
        ..########..
        ..#......#..
        ..#......#..
        ..#......#..
        ..#......#..
        ..#....#.#..
        ..#......#..
        ..#......#..
        ..#......#..
        ..#......#..
        ..#......#..
        ############
    """,
}


def rows_of(drawing: str) -> list[str]:
    lines = [line.strip() for line in drawing.strip().splitlines()]
    return [line for line in lines if line]


def runs(rows: list[str], wanted: set[str]) -> str:
    """Path data for the pixels whose character is in `wanted`: one rectangle per run."""
    parts = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] in wanted:
                start = x
                while x < len(row) and row[x] in wanted:
                    x += 1
                parts.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
            else:
                x += 1
    return "".join(parts)


def sprite() -> str:
    symbols = []
    for name, drawing in sorted(ICONS.items()):
        rows = rows_of(drawing)
        assert len(rows) == 12 and all(len(row) == 12 for row in rows), name
        symbols.append(
            f'<symbol id="i-{name}" viewBox="0 0 12 12">'
            f'<path fill="currentColor" d="{runs(rows, {"#"})}"/></symbol>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">\n'
        + "\n".join(symbols)
        + "\n</svg>\n"
    )


def picture(grid: list[list[str]], *, background: str | None = None, scale: int = 1) -> str:
    """A many-coloured picture from a grid of palette keys ('.' is see-through)."""
    height, width = len(grid), len(grid[0])
    rows = ["".join(row) for row in grid]
    layers = []
    if background:
        layers.append(f'<rect width="{width}" height="{height}" fill="{background}"/>')
    for key, colour in PALETTE.items():
        data = runs(rows, {key})
        if data:
            layers.append(f'<path fill="{colour}" d="{data}"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width * scale}" height="{height * scale}" shape-rendering="crispEdges">'
        + "".join(layers)
        + "</svg>\n"
    )


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.grid = [["." for _ in range(width)] for _ in range(height)]

    def dot(self, x: int, y: int, key: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = key

    def stamp(self, x: int, y: int, drawing: str) -> None:
        """Lay a small drawing down with its top-left corner at (x, y); '.' leaves what is there."""
        for dy, row in enumerate(rows_of(drawing)):
            for dx, key in enumerate(row):
                if key != ".":
                    self.dot(x + dx, y + dy, key)

    def fill_below(self, surface, key: str) -> None:
        for x in range(self.width):
            for y in range(max(0, round(surface(x))), self.height):
                self.dot(x, y, key)


def sunset() -> str:
    """The home page's screen: a Saturday evening, the family on the hill against the sun."""
    art = Canvas(64, 48)
    # The sky, deep blue at the top to plum at the horizon, stepped with a checkerboard between
    # bands the way an old game would, having only so many colours to go round.
    bands = [(0, "s"), (9, "t"), (17, "u"), (24, "v"), (30, "w")]
    for y in range(48):
        for x in range(64):
            key = "s"
            for start, band in bands:
                if y >= start:
                    key = band
                elif y >= start - 2 and (x + y) % 2 == 0:
                    key = band
                    break
            art.dot(x, y, key)
    stars = [
        (4, 3),
        (11, 7),
        (19, 2),
        (26, 10),
        (33, 4),
        (3, 16),
        (60, 3),
        (61, 14),
        (8, 11),
        (22, 15),
        (48, 2),
        (15, 19),
        (36, 9),
        (42, 6),
        (29, 1),
    ]
    for n, (x, y) in enumerate(stars):
        art.dot(x, y, "c" if n % 4 == 0 else "l" if n % 4 == 1 else "5")
    art.stamp(13, 4, ".5.\n5c5\n.5.")  # one bright star, for wishing on

    # The sun going down behind the hills, yellow to coral, with two bands of cloud across it
    # like a seventies poster.
    cx, cy, r = 38, 34, 15
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r and y not in (cy - 9, cy - 6):
                art.dot(x, y, "y" if y < cy - 9 else "a" if y < cy - 5 else "o" if y < cy else "r")

    far = lambda x: 31 + 15 * math.exp(-(((x - 38) / 13) ** 2)) + 0.8 * math.sin(x / 3.1)  # noqa: E731
    art.fill_below(far, "1")
    near = lambda x: 47 - 8 * math.exp(-(((x - 38) / 20) ** 2)) + 0.6 * math.sin(x / 5)  # noqa: E731
    art.fill_below(near, "2")
    for x in range(64):  # a bright rim where the last light catches the near hill
        art.dot(x, round(near(x)), "3")

    # Home on the far hill, with the porch light on, and a pine beside it.
    art.stamp(
        2,
        20,
        """
        .....r.....
        ....rrr....
        ...rrrrr.3.
        ..rrrrrrr..
        .rrrrrrrrr.
        rrrrrrrrrrr
        .3.......3.
        .3.aa....3.
        .3.aa..3.3.
        .3.....3.3.
        .333333333.
    """,
    )
    art.stamp(15, 20, "..3..\n.333.\n..3..\n.333.\n33333\n.333.\n33333\n..2..\n..2..")

    # The four of them and the dog on the crest, holding hands, dark against the sun.
    grown_up = ".000.\n.000.\n.....\n00000\n00000\n00000\n00000\n.0.0.\n.0.0.\n.0.0.\n.0.0."
    in_a_dress = ".000.\n.000.\n.....\n.000.\n00000\n00000\n00000\n00000\n.0.0.\n.0.0.\n.0.0."
    little = "000\n000\n...\n000\n000\n0.0\n0.0"
    dog = "......0\n0....00\n.00000.\n.0...0."

    def stand(x: int, drawing: str) -> int:
        """Put a figure on the near hill with its feet on the ground; returns its top row."""
        rows = rows_of(drawing)
        top = round(near(x + len(rows[0]) // 2)) - len(rows)
        art.stamp(x, top, drawing)
        return top

    dad, first, mum, second = (
        stand(25, grown_up),
        stand(32, little),
        stand(36, in_a_dress),
        stand(43, little),
    )
    stand(47, dog)
    for x, hand in ((30, dad + 5), (31, dad + 5), (35, first + 4), (41, mum + 5), (42, mum + 5)):
        art.dot(x, hand, "0")  # hands held
    # The younger one's kite, held up high and flying well away to the right.
    art.dot(46, second + 1, "0")
    art.dot(46, second, "0")
    for x, y in [
        (47, second - 2),
        (48, second - 4),
        (49, 26),
        (50, 24),
        (51, 22),
        (53, 20),
        (54, 18),
        (56, 16),
    ]:
        art.dot(x, y, "l")
    art.stamp(
        54,
        7,
        """
        ...k...
        ..kkk..
        .kkckk.
        kccccck
        .kkckk.
        ..kkk..
        ...k...
        ...l...
    """,
    )
    for x, y in [(56, 15), (58, 14)]:
        art.dot(x, y, "c")  # the bows on its tail
    return picture(art.grid)


def horizon() -> str:
    """The strip over the foot of every page: hills, pines, flowers and the odd lit window."""
    art = Canvas(240, 14)

    def ground(x: int) -> float:
        turn = x * math.tau / 240
        return 9 + 2.2 * math.sin(turn * 3) + 0.9 * math.sin(turn * 11)

    art.fill_below(ground, "1")
    for x in range(240):
        art.dot(x, round(ground(x)), "2")
    for x in (18, 23, 71, 118, 124, 129, 187, 214):
        base = round(ground(x))
        art.stamp(x - 2, base - 6, "..2..\n.222.\n..2..\n.222.\n22222\n..2..")
    for x in (44, 160):
        base = round(ground(x))
        art.stamp(x - 3, base - 5, "...2...\n.22222.\n2222222\n.2.a.2.\n.2...2.")
    for x, colour in (
        (8, "k"),
        (33, "a"),
        (57, "l"),
        (96, "k"),
        (104, "c"),
        (141, "a"),
        (175, "l"),
        (201, "k"),
        (228, "c"),
    ):
        art.dot(x, round(ground(x)) - 1, colour)  # a flower here and there
    return picture(art.grid)


def test_card() -> str:
    """No signal: the colour bars a set showed when there was nothing on, for the page that
    is not there."""
    art = Canvas(48, 36)
    widths = [7, 7, 7, 7, 7, 7, 6]
    rows = [
        (range(0, 24), "GYCNMRU"),
        (range(24, 27), "UKMKCKG"),
    ]
    for span, colours in rows:
        x = 0
        for width, colour in zip(widths, colours, strict=True):
            for dx in range(width):
                for y in span:
                    art.dot(x + dx, y, colour)
            x += width
    bottom = [(9, "I"), (8, "E"), (9, "P"), (10, "K"), (3, "K"), (3, "G"), (6, "K")]
    x = 0
    for width, colour in bottom:
        for dx in range(width):
            for y in range(27, 36):
                art.dot(x + dx, y, colour)
        x += width
    return picture(art.grid)


def favicon() -> str:
    rows = rows_of(ICONS["bot"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 16 16" '
        'shape-rendering="crispEdges">'
        f'<rect x="-2" y="-2" width="16" height="16" rx="3" fill="{PALETTE["0"]}"/>'
        f'<path fill="{PALETTE["4"]}" d="{runs(rows, {"#"})}"/></svg>\n'
    )


def main() -> None:
    (STATIC / "art").mkdir(exist_ok=True)
    outputs = {
        STATIC / "icons.svg": sprite(),
        STATIC / "favicon.svg": favicon(),
        STATIC / "art" / "sunset.svg": sunset(),
        STATIC / "art" / "horizon.svg": horizon(),
        STATIC / "art" / "testcard.svg": test_card(),
    }
    for path, text in outputs.items():
        path.write_text(text)
        print(f"{path.relative_to(STATIC.parents[3])}: {len(text):,} bytes")


if __name__ == "__main__":
    main()
