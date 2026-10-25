"""
Train the hand-pose classifier and evaluate it honestly.

    uv run python -m gesturekey.tools.train                 # evaluate only
    uv run python -m gesturekey.tools.train --save          # also replace the engine's model
    uv run python -m gesturekey.tools.train --no-legacy     # ignore the v2 dataset

Evaluation holds out whole sessions (GroupKFold): frames from one recording
are near-duplicates, so a random split — what the v2 script did — reports
accuracy the model doesn't have on a new day, light or camera.
"""
from __future__ import annotations
import argparse
import shutil
import time
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold, train_test_split

from gesturekey.runtime.engine import MODEL_PATH
from gesturekey.tools.dataset import data_dir, read


def load(folder: Path, legacy: bool):
    X, y, groups = [], [], []
    for path in sorted(folder.glob("*.csv")):
        if path.name.startswith("legacy") and not legacy:
            continue
        for session, label, features in read(path):
            X.append(features)
            y.append(label)
            groups.append(session)
    return np.asarray(X), np.asarray(y), np.asarray(groups)


def model() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=200, min_samples_leaf=3, class_weight="balanced",
                                  random_state=42, n_jobs=-1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey.tools.train")
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--no-legacy", action="store_true")
    parser.add_argument("--save", action="store_true", help="write the model the engine loads")
    args = parser.parse_args()

    X, y, groups = load(data_dir(args.data), legacy=not args.no_legacy)
    if len(y) == 0:
        raise SystemExit("No training data found.")
    sessions = sorted(set(groups))
    print(f"{len(y)} frames, {len(sessions)} sessions")
    for label, n in sorted(Counter(y).items()):
        print(f"  {label:<14} {n:>6}")

    labels = sorted(set(y))
    if len(sessions) >= 2:
        folds = GroupKFold(n_splits=min(5, len(sessions)))
        pred = np.empty_like(y)
        for train_idx, test_idx in folds.split(X, y, groups):
            m = model().fit(X[train_idx], y[train_idx])
            pred[test_idx] = m.predict(X[test_idx])
        truth = y
        print("\nHeld-out sessions (each predicted by a model that never saw it):")
    else:
        print("\nOnly one session: this split is optimistic. Record more sessions for an honest number.")
        X_tr, X_te, y_tr, truth = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        pred = model().fit(X_tr, y_tr).predict(X_te)

    print(classification_report(truth, pred, labels=labels, zero_division=0))
    print("Confusion (rows = truth, cols = predicted):")
    print("  " + " ".join(f"{l[:6]:>6}" for l in labels))
    for label, line in zip(labels, confusion_matrix(truth, pred, labels=labels)):
        print(f"  " + " ".join(f"{v:>6}" for v in line) + f"   {label}")

    if args.save:
        final = model().fit(X, y)
        final.verbose = 0
        if MODEL_PATH.exists():
            backup = MODEL_PATH.with_name(f"{MODEL_PATH.stem}-{time.strftime('%Y%m%d-%H%M%S')}.bak")
            shutil.copy2(MODEL_PATH, backup)
            print(f"\nPrevious model kept as {backup.name}")
        joblib.dump(final, MODEL_PATH)
        print(f"Saved {MODEL_PATH} with classes {list(final.classes_)}")


if __name__ == "__main__":
    main()
