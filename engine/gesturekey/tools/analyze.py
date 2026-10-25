"""
Analyse a recorded session (see runtime/recorder.py).

    uv run python -m gesturekey.tools.analyze <session.jsonl>
    uv run python -m gesturekey.tools.analyze --latest

Reports frame timing, state flicker, jitter while the hand is held still,
how often that jitter would cross the per-frame motion thresholds the
gestures use, handedness flips, and the gesture events that fired.
"""
from __future__ import annotations
import argparse
import json
import math
import statistics as st
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gesturekey.config import settings_path
from gesturekey.core.geometry import hand_center
from gesturekey.vision.tracker import _normalise

STILL_MIN_S   = 2.0     # a constant stable state at least this long counts as a "hold"
MOVE_LIMIT_PX = 40.0    # …and the wrist must stay within this many px of its median
SCROLL_DEADZONE = 0.003  # gestures/scroll.py VELOCITY_DEADZONE (per frame, norm space)
GRAB_DEADZONE   = 0.002  # config GrabWindowConfig.deadzone (per frame, image space)

Frame = Dict[str, Any]


def _load(path: Path) -> Tuple[List[Frame], List[Dict[str, Any]], Tuple[int, int]]:
    frames, events, size = [], [], (1280, 720)
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = msg.get("type")
        if kind == "frame":
            frames.append(msg)
        elif kind == "event":
            events.append(msg)
        elif kind == "camera":
            size = (int(msg["width"]), int(msg["height"]))
    return frames, events, size


def _pct(values: List[float], q: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))]


def _main_hand(f: Frame) -> Optional[Dict[str, Any]]:
    hands = {h["side"]: h for h in f["hands"]}
    return hands.get("Right") or hands.get("Left")


def _segments(frames: List[Frame]) -> List[Tuple[int, int]]:
    """Runs of the same stable state (with a hand) lasting ≥ STILL_MIN_S."""
    out, start = [], 0
    for i in range(1, len(frames) + 1):
        if i == len(frames) or frames[i]["state"] != frames[start]["state"]:
            if (frames[start]["state"] not in ("NO HANDS", "UNKNOWN")
                    and frames[i - 1]["t"] - frames[start]["t"] >= STILL_MIN_S):
                out.append((start, i))
            start = i
    return out


def report(path: Path) -> None:
    frames, events, (w, h) = _load(path)
    if len(frames) < 2:
        print("La grabación no tiene frames suficientes.")
        return

    duration = frames[-1]["t"] - frames[0]["t"]
    dts = [b["t"] - a["t"] for a, b in zip(frames, frames[1:]) if b["t"] > a["t"]]
    with_hand = sum(1 for f in frames if f["hands"])
    print(f"\n== {path.name}")
    print(f"duración {duration:.0f} s · {len(frames)} frames · cámara {w}×{h}")
    print(f"fps medio {len(frames) / duration:.1f} · intervalo p50 {1000 * _pct(dts, .5):.0f} ms, "
          f"p95 {1000 * _pct(dts, .95):.0f} ms, máx {1000 * max(dts):.0f} ms")
    print(f"mano visible {100 * with_hand / len(frames):.0f} % del tiempo")

    # ── states ────────────────────────────────────────────────────────────
    stable_changes = sum(1 for a, b in zip(frames, frames[1:]) if a["state"] != b["state"])
    raw_changes    = sum(1 for a, b in zip(frames, frames[1:]) if a["raw_state"] != b["raw_state"])
    minutes = duration / 60
    print(f"\ncambios de estado: estable {stable_changes / minutes:.0f}/min · crudo {raw_changes / minutes:.0f}/min")
    by_state: Dict[str, List[float]] = {}
    for f in frames:
        if f["hands"]:
            by_state.setdefault(f["raw_state"], []).append(f["confidence"])
    print("confianza media del modelo por estado crudo:")
    for s, confs in sorted(by_state.items(), key=lambda kv: -len(kv[1])):
        low = sum(1 for c in confs if c < 0.6) / len(confs)
        print(f"  {s:<14} {len(confs):>5} frames · media {st.mean(confs):.2f} · bajo 0.60: {100 * low:.0f} %")

    # ── side flips ───────────────────────────────────────────────────────
    flips = 0
    for a, b in zip(frames, frames[1:]):
        if len(a["hands"]) == 1 and len(b["hands"]) == 1 and a["hands"][0]["side"] != b["hands"][0]["side"]:
            flips += 1
    print(f"lateralidad (una mano): {flips} cambios Derecha↔Izquierda")

    # ── holds: jitter with the hand still ────────────────────────────────
    print(f"\nposes sostenidas (≥ {STILL_MIN_S:.0f} s, muñeca dentro de {MOVE_LIMIT_PX:.0f} px):")
    print(f"  {'estado':<14}{'dur':>6}{'jitter muñeca':>15}{'jitter índice':>15}"
          f"{'parpadeos':>11}{'>scroll dz':>12}{'>grab dz':>10}")
    any_hold = False
    for a, b in _segments(frames):
        seg = [f for f in frames[a:b] if _main_hand(f)]
        if len(seg) < 10:
            continue
        hands = [_main_hand(f) for f in seg]
        wrist = [(hd["landmarks"][0][0] * w, hd["landmarks"][0][1] * h) for hd in hands]
        mx, my = st.median(p[0] for p in wrist), st.median(p[1] for p in wrist)
        if max(math.hypot(x - mx, y - my) for x, y in wrist) > MOVE_LIMIT_PX:
            continue   # the hand was moving, not a hold
        any_hold = True

        def rms_step(points: List[Tuple[float, float]]) -> float:
            steps = [math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(points, points[1:])]
            return math.sqrt(sum(s * s for s in steps) / len(steps))

        tip = [(hd["landmarks"][8][0] * w, hd["landmarks"][8][1] * h) for hd in hands]
        flick = sum(1 for p, q in zip(seg, seg[1:]) if p["raw_state"] != q["raw_state"])

        # per-frame deltas the gestures would see while the user holds still
        centers = [hand_center(_normalise([(x * w, y * h) for x, y in hd["landmarks"]])) for hd in hands]
        dy_norm = [abs(q[1] - p[1]) for p, q in zip(centers, centers[1:])]
        d_img = [max(abs(q["landmarks"][0][0] - p["landmarks"][0][0]), abs(q["landmarks"][0][1] - p["landmarks"][0][1]))
                 for p, q in zip(hands, hands[1:])]
        over_scroll = sum(1 for d in dy_norm if d > SCROLL_DEADZONE) / len(dy_norm)
        over_grab = sum(1 for d in d_img if d > GRAB_DEADZONE) / len(d_img)

        print(f"  {seg[0]['state']:<14}{seg[-1]['t'] - seg[0]['t']:>5.1f}s"
              f"{rms_step(wrist):>12.1f} px{rms_step(tip):>12.1f} px"
              f"{flick:>11}{100 * over_scroll:>11.0f}%{100 * over_grab:>9.0f}%")
    if not any_hold:
        print("  (ninguna — sostén cada pose quieta unos segundos)")

    # ── events ──────────────────────────────────────────────────────────
    print(f"\neventos ({len(events)}):")
    for name, n in Counter(e["event"] for e in events).most_common():
        print(f"  {name:<24}{n:>4}")


def _latest() -> Path:
    folder = settings_path().parent / "recordings"
    files = sorted(folder.glob("session-*.jsonl"))
    if not files:
        raise SystemExit(f"No hay grabaciones en {folder}")
    return files[-1]


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.analyze")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--latest", action="store_true", help="analyse the newest recording")
    args = parser.parse_args()
    report(_latest() if args.latest or not args.path else args.path)


if __name__ == "__main__":
    main()
