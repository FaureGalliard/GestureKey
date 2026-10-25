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
| 9 | THUMB_DOWN 👎 | **new** — mute later (recorded, not in the model yet) |
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

## Tracker

Since 2026-10-25 the engine uses MediaPipe **Tasks** (`HandLandmarker`, model
`gesturekey/models/hand_landmarker.task`) instead of the removed `mp.solutions`
API. On the user's test clip its landmarks match the old API's within ~0.9 % of the
image width (median), it is faster (23 vs 40 ms/frame) and keeps the hand's side
steadier. The first Brio session was recorded with the old API; new sessions are
recorded with Tasks, so later models will match the live tracker even better.

## Model history

| Model | Data | Classes | On the MX Brio session |
|---|---|---|---|
| `models/hand_state_rf_v2.pkl` | v2 (old webcam, one session; the exact data isn't in git) | 6 + UNKNOWN | 87.5 % (palm 80 %, pinch 77 %; a relaxed hand read as fist 182×) |
| `models/hand_state_rf.pkl` (2026-10-25) | v2 dataset + Brio session 1 | 6 + OTHER | 95.9 % held-out time blocks; 94.1 % cross-camera (trained on v2 data only) |

THUMB_UP, OK and ROCK were dropped. THUMB_DOWN is recorded but excluded by default
until mute uses it. POINT is in the model (the cursor needs it) but takes frames from
FIST (~23 % in the held-out blocks): moving windows treats POINT as a fist once it has
seen the palm, and more fist / point sessions should fix it at the source.

## Pretrained alternatives (researched 2026-10-25)

- **MediaPipe Gesture Recognizer** (Tasks API): canned classes None, Closed_Fist,
  Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou — no pinch, three or
  four fingers. Retraining needs Model Maker (unmaintained, needs WSL/Colab on Windows).
  Worth it as a second opinion and as the path off the legacy `mp.solutions` API, which
  MediaPipe removed from 0.10.30 on (we pin 0.10.9).
- **HaGRID v2** (github.com/hukenovs/hagrid): ~1M images, 33 classes + `no_gesture`, with
  MediaPipe 2D landmark annotations — the best source of cross-person / cross-camera data
  for 9 of our 10 poses (no exact pinch). License is CC BY-SA 4.0-style: check before
  shipping a model trained on it. Only the annotation JSONs are needed, not the images.
- Skipped: kinivi/hand-gesture-recognition-mediapipe (4 classes, small dataset), Jester
  (dynamic gestures, no landmarks).
