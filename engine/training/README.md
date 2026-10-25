# Training the hand-pose model

The engine classifies each frame into a hand pose (PALM, FIST, …) with a random
forest over finger distances and angles (`vision/classifier.py`). Gestures are
built on top of those poses plus motion.

## What's here

| File | What |
|---|---|
| `data/legacy_v2_features.csv` | The v2 dataset recovered from git history (Jan 2026): 6 992 frames, 6 poses, **one 11-minute session**, old webcam, features only (no raw landmarks). |
| `legacy_train_model.py` | The v2 training script, for reference. It split train/test at random inside that single session, so its ~100 % accuracy was optimistic. |
| `data/session-*.csv` | New recordings from `tools.collect`: raw image + world landmarks of both hands, one file per session. |

## Record

```bash
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.collect
```

Pick a pose with its key, press **SPACE** to record, SPACE again to stop.
Each run of the tool is one session.

| Key | Pose | Used for |
|---|---|---|
| 1 | PALM ✋ | grab (arm), screenshot, task view, power |
| 2 | FIST ✊ | grab, close |
| 3 | PINCH 🤏 | zoom |
| 4 | TWO_FINGERS ✌️ | scroll |
| 5 | THREE_FINGERS 🤟 | volume |
| 6 | FOUR_FINGERS 🖖 | play / pause |
| 7 | POINT ☝️ | **new** — mouse cursor |
| 8 | THUMB_UP 👍 | **new** — confirm / Enter |
| 9 | THUMB_DOWN 👎 | **new** — mute (replaces palm-fist-palm) |
| r | ROCK 🤘 | **new** — media (next / previous track) |
| k | OK 👌 | **new** — later (dictation) |
| 0 | OTHER | **new** — relaxed hand, half-open, scratching, typing: explicitly "no pose" |

**OTHER matters most.** Today the model must pick one of six poses even for a
relaxed hand; most false triggers come from that.

### Protocol (per session, ~10 minutes)

- 20–30 s per pose, in 3–4 short takes.
- Move while holding the pose: rotate the wrist, go near and far, up and down.
- Both hands.
- Include the transitions people really make (open → fist, sideways palm) as OTHER
  only if they are clearly in between.
- Vary the conditions across sessions: daylight / lamp, sitting closer / further,
  sleeves, another person if possible.

Aim for **at least 4 sessions** on different days or lighting before trusting
the numbers.

## Train and evaluate

```bash
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.train            # evaluate
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.train --save     # replace the model
```

Evaluation holds out whole sessions (GroupKFold), so the reported accuracy is
what to expect on a session the model never saw. `--save` backs up the current
model before replacing it.

## Other tools

| Command | What |
|---|---|
| `uv run python -m gesturekey.tools.replay <video.mp4>` | Run a video through the real pipeline without acting, print what fires |
| `uv run python -m gesturekey.tools.export --latest` | Recorded session (`GESTUREKEY_RECORD=1`) → CSV of movements: state, owner, events, wrist, palm centre, tilt, all landmarks |
| `uv run python -m gesturekey.tools.analyze --latest` | Jitter, flicker and timing report of a recorded session |

## Next: better features

Recordings keep raw landmarks, including MediaPipe **world landmarks** (metres,
centred on the hand), so new features can be tried without recording again —
e.g. joint flexion angles in 3D, thumb-to-fingertip distances, palm orientation.
Those are far less sensitive to camera, distance and wrist rotation than the
current 2D features.
