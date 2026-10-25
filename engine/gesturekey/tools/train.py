"""
Train the hand-pose classifier and evaluate it honestly.

    uv run python -m gesturekey.tools.train                    # evaluate only
    uv run python -m gesturekey.tools.train --save             # also replace the engine's model
    uv run python -m gesturekey.tools.train --no-legacy        # ignore the v2 dataset
    uv run python -m gesturekey.tools.train --exclude OK ROCK  # choose which poses to drop

Frames from one recording are near-duplicates, so a random split — what the
v2 script did — reports accuracy the model doesn't have on a new day, light
or camera. Reports, depending on the data available:

  cross-camera   train on the v2 dataset (old webcam), test on the new sessions,
                 on the poses both have. The number that says "works on other cameras".
  held-out time  per session and pose, the last 25 % of the frames (a separate take
                 in practice) are held out; train on the rest.
  sessions       GroupKFold over sessions, once there are at least 3.
"""
from __future__ import annotations
import argparse
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import List

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold

from gesturekey.runtime.engine import MODEL_PATH
from gesturekey.tools.dataset import data_dir, data_files, read

LEGACY = "legacy"
HOLDOUT = 0.25


def load(folder: Path, legacy: bool, exclude: List[str]):
    X, y, groups = [], [], []
    for path in data_files(folder):
        if path.name.startswith("legacy") and not legacy:
            continue
        for session, label, features in read(path):
            if label in exclude:
                continue
            X.append(features)
            y.append(label)
            groups.append(session)
    return np.asarray(X), np.asarray(y), np.asarray(groups)


def model() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=200, min_samples_leaf=3, class_weight="balanced",
                                  random_state=42, n_jobs=-1)


def report(title: str, truth: np.ndarray, pred: np.ndarray) -> float:
    labels = sorted(set(truth) | set(pred))
    acc = float((truth == pred).mean())
    print(f"\n── {title}: accuracy {100 * acc:.1f} % on {len(truth)} frames")
    print(classification_report(truth, pred, labels=labels, zero_division=0, digits=3))
    width = max(6, max(len(l) for l in labels) // 2)
    print("confusion (rows = truth, columns = predicted)")
    print(" " * 16 + " ".join(f"{l[:width]:>{width}}" for l in labels))
    for label, line in zip(labels, confusion_matrix(truth, pred, labels=labels)):
        print(f"  {label:<14}" + " ".join(f"{v:>{width}}" for v in line))
    return acc


def time_holdout(y: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Mask of test rows: the last HOLDOUT of each (session, pose), in recording order."""
    test = np.zeros(len(y), dtype=bool)
    rows = defaultdict(list)
    for i, key in enumerate(zip(groups, y)):
        rows[key].append(i)
    for idx in rows.values():
        cut = int(len(idx) * (1 - HOLDOUT))
        test[idx[cut:]] = True
    return test


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.train")
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--no-legacy", action="store_true")
    # THUMB_UP, OK and ROCK were dropped; THUMB_DOWN is recorded but unused so far
    parser.add_argument("--exclude", nargs="*", default=["OK", "ROCK", "THUMB_UP", "THUMB_DOWN"],
                        help="poses to leave out")
    parser.add_argument("--save", action="store_true", help="write the model the engine loads")
    args = parser.parse_args()

    X, y, groups = load(data_dir(args.data), legacy=not args.no_legacy, exclude=args.exclude)
    if len(y) == 0:
        raise SystemExit("No training data found.")
    sessions = sorted(set(groups))
    print(f"{len(y)} frames · sessions: {', '.join(sessions)}")
    per = Counter(zip(groups, y))
    for label in sorted(set(y)):
        print(f"  {label:<14}" + "".join(f"{per[(s, label)]:>9}" for s in sessions))

    # cross-camera: the old webcam's data predicting the new camera's
    new = groups != LEGACY
    if (~new).any() and new.any():
        shared = np.isin(y, np.unique(y[~new]))
        m = model().fit(X[~new], y[~new])
        report("cross-camera (trained on the v2 dataset, tested on the new sessions)",
               y[new & shared], m.predict(X[new & shared]))

    # held-out takes within each session
    test = time_holdout(y, groups)
    m = model().fit(X[~test], y[~test])
    report("held-out time blocks (last 25 % of every pose in every session)", y[test], m.predict(X[test]))

    if len(sessions) >= 3:
        pred = np.empty_like(y)
        for tr, te in GroupKFold(n_splits=min(5, len(sessions))).split(X, y, groups):
            pred[te] = model().fit(X[tr], y[tr]).predict(X[te])
        report("held-out sessions (GroupKFold)", y, pred)
    else:
        print("\n(record at least 3 sessions for a held-out-session score)")

    if args.save:
        final = model().fit(X, y)
        final.verbose = 0
        if MODEL_PATH.exists():
            backup = MODEL_PATH.with_name(f"{MODEL_PATH.stem}-{time.strftime('%Y%m%d-%H%M%S')}.bak")
            shutil.copy2(MODEL_PATH, backup)
            print(f"\nPrevious model kept as {backup.name}")
        joblib.dump(final, MODEL_PATH, compress=3)
        print(f"Saved {MODEL_PATH.name} · classes {list(final.classes_)}")


if __name__ == "__main__":
    main()
