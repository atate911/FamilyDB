"""How alike two palettes LOOK, measured on the pictures, independent of how they scored.

Every palette is rendered on the same pages with the same layout, so two renders can be compared
point by point: the distance between two palettes is the average colour difference (CIE Lab,
Delta E 1976) between their screenshots of Home (down to its lists), Chat, Ideas, Status and
phone Home, each shrunk to a common size. Alongside it, the share of points that differ by more
than 5 (a difference anyone would see).

Usage:
  venv/bin/python diversity.py fingerprint DIR [ids...]   # cache DIR/out/<id>/fingerprint.npy
  venv/bin/python diversity.py matrix DIR [ids...]        # print the distance matrix as JSON
  venv/bin/python diversity.py between A_DIR A_ID B_DIR B_ID
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PAGES = [("home", 1500), ("chat", 900), ("ideas", 900), ("status", 900), ("home-phone", 1688)]
W = 200  # each page shrunk to this width


def to_lab(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def fingerprint(folder: Path, pid: str) -> list[np.ndarray] | None:
    cache = folder / "out" / pid / "fingerprint2.npz"
    shots = folder / "out" / pid / "shots"
    if cache.exists() and cache.stat().st_mtime >= max((shots / f"{p}.png").stat().st_mtime for p, _ in PAGES if (shots / f"{p}.png").exists()):
        data = np.load(cache)
        return [data[p] for p, _ in PAGES]
    pages = []
    for page, height in PAGES:
        f = shots / f"{page}.png"
        if not f.exists():
            return None
        img = Image.open(f).convert("RGB")
        # Scroll bars are visible now, so a full page can be a little narrower than the viewport:
        # scale by the real width, never by whole multiples of it.
        scale = img.width / (390 if page.endswith("phone") else 1280)
        img = img.crop((0, 0, img.width, min(img.height, round(height * scale))))
        img = img.crop((0, 0, round(img.width * 0.98), img.height))  # the scroll bar is not the look
        h = round(img.height * W / img.width)
        pages.append(to_lab(np.asarray(img.resize((W, h), Image.BOX)).astype(np.float64)))
    np.savez_compressed(cache, **{p: a for (p, _), a in zip(PAGES, pages)})
    return pages


def distance(a: list[np.ndarray], b: list[np.ndarray]) -> tuple[float, float]:
    """(mean Delta E, share of points differing by more than 5), averaged over the pages."""
    means, shares = [], []
    for x, y in zip(a, b):
        h = min(x.shape[0], y.shape[0])
        d = np.sqrt(((x[:h] - y[:h]) ** 2).sum(-1))
        means.append(float(d.mean()))
        shares.append(float((d > 5).mean()))
    return round(float(np.mean(means)), 2), round(float(np.mean(shares)) * 100, 1)


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "between":
        a = fingerprint(Path(sys.argv[2]), sys.argv[3])
        b = fingerprint(Path(sys.argv[4]), sys.argv[5])
        print(json.dumps(distance(a, b)))
        return
    folder = Path(sys.argv[2])
    ids = sys.argv[3:] or sorted(p.stem for p in (folder / "palettes").glob("*.json"))
    prints = {i: fingerprint(folder, i) for i in ids}
    prints = {i: p for i, p in prints.items() if p is not None}
    if cmd == "fingerprint":
        print("fingerprinted", sorted(prints))
        return
    out = {}
    keys = sorted(prints)
    for i in keys:
        out[i] = {j: distance(prints[i], prints[j]) for j in keys if j != i}
    print(json.dumps(out))


if __name__ == "__main__" and sys.argv[1:2] != ["archive"]:
    main()


def archive_matrix() -> dict:
    """Distances between every palette in archive.json (and today), cached in archive_distances.json."""
    here = Path(__file__).parent
    arc = json.loads((here / "archive.json").read_text())["palettes"]
    prints = {"00-current": fingerprint(here / "round1", "00-current")}
    for key, p in arc.items():
        fp = fingerprint(Path(p["dir"]), p["id"])
        if fp is not None:
            prints[key] = fp
    keys = sorted(prints)
    out = {k: {} for k in keys}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = distance(prints[a], prints[b])
            out[a][b] = out[b][a] = d
    (here / "archive_distances.json").write_text(json.dumps(out))
    return out


if __name__ == "__main__" and sys.argv[1:2] == ["archive"]:
    m = archive_matrix()
    print(len(m), "palettes in the distance matrix")
