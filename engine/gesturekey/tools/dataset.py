"""
Training data format shared by tools.collect (writes) and tools.train (reads).

One CSV row per frame, raw coordinates of both hands, so features can be
redesigned later without recording again:

    session, t, label, frame_w, frame_h,
    {left,right}_present, {left,right}_score,
    {side}_x{i}, {side}_y{i}, {side}_z{i}       image landmarks (0..1, mirrored), i = 0..20
    {side}_wx{i}, {side}_wy{i}, {side}_wz{i}    world landmarks (metres)

Features are computed at training time with the very same function the
engine uses live (vision.classifier.feature_vector), so what the model
learns matches what it sees.
"""
from __future__ import annotations
import csv
import gzip
import io
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from gesturekey.core.types import Hand
from gesturekey.vision.classifier import FEATURE_NAMES, feature_vector
from gesturekey.vision.tracker import _normalise

SIDES = ("left", "right")
N = 21

# ⌨ key → pose, for tools.collect. Existing poses first, then the ones to add.
LABEL_KEYS: Dict[str, str] = {
    "1": "PALM", "2": "FIST", "3": "PINCH", "4": "TWO_FINGERS", "5": "THREE_FINGERS",
    "6": "FOUR_FINGERS", "7": "POINT", "8": "THUMB_UP", "9": "THUMB_DOWN",
    "r": "ROCK", "k": "OK", "0": "OTHER",
}


def header() -> List[str]:
    cols = ["session", "t", "label", "frame_w", "frame_h"]
    for side in SIDES:
        cols += [f"{side}_present", f"{side}_score"]
        cols += [f"{side}_{a}{i}" for i in range(N) for a in ("x", "y", "z")]
        cols += [f"{side}_{a}{i}" for i in range(N) for a in ("wx", "wy", "wz")]
    return cols


def row(session: str, t: float, label: str, size: Tuple[int, int], hands: Dict[str, Hand]) -> List[object]:
    out: List[object] = [session, round(t, 3), label, size[0], size[1]]
    for side in SIDES:
        hand = hands.get(side.capitalize())
        if hand is None:
            out += [0, 0.0] + [""] * (N * 6)
            continue
        out += [1, round(hand.score, 3)]
        for (x, y), z in zip(hand.img, hand.z):
            out += [round(x, 5), round(y, 5), round(z, 5)]
        world = hand.world or ((0.0, 0.0, 0.0),) * N
        for wx, wy, wz in world:
            out += [round(wx, 5), round(wy, 5), round(wz, 5)]
    return out


def _open(path: Path) -> io.TextIOBase:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open(newline="", encoding="utf-8")


def data_files(folder: Path) -> List[Path]:
    """Every dataset in the folder, plain or gzipped (a .csv and its .csv.gz count once)."""
    files = {p.name.removesuffix(".gz"): p for p in sorted(folder.glob("*.csv.gz"))}
    for p in sorted(folder.glob("*.csv")):
        files.setdefault(p.name, p)
    return [files[k] for k in sorted(files)]


def read(path: Path) -> Iterator[Tuple[str, str, List[float]]]:
    """(session, label, 20 classifier features) per row, in recording order; legacy feature-only CSVs too."""
    with _open(path) as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        legacy = "state" in cols and "right_x0" not in cols
        for r in reader:
            if legacy:                                   # v2 file: features already computed
                yield "legacy", r["state"], [float(r[c]) for c in FEATURE_NAMES]
                continue
            if not r["label"]:
                continue
            hands = {}
            w, h = float(r["frame_w"]), float(r["frame_h"])
            for side in SIDES:
                if r[f"{side}_present"] != "1":
                    continue
                img = [(float(r[f"{side}_x{i}"]), float(r[f"{side}_y{i}"])) for i in range(N)]
                hands[side.capitalize()] = Hand(side=side.capitalize(),
                                                norm=_normalise([(x * w, y * h) for x, y in img]),
                                                img=img, z=[float(r[f"{side}_z{i}"]) for i in range(N)])
            if hands:
                yield r["session"], r["label"], feature_vector(hands)


def append_rows(path: Path, rows: List[List[object]]) -> None:
    """Append (gzip when the name ends in .gz: appended members read back as one file)."""
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = (lambda: gzip.open(path, "at", newline="", encoding="utf-8")) if path.suffix == ".gz"         else (lambda: path.open("a", newline="", encoding="utf-8"))
    with opener() as fh:
        writer = csv.writer(fh)
        if new:
            writer.writerow(header())
        writer.writerows(rows)


def data_dir(explicit: Optional[Path] = None) -> Path:
    return explicit or Path(__file__).resolve().parents[2] / "training" / "data"
