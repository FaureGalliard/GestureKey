# 🖐️ GestureKey

Control your PC with hand gestures in front of the webcam: scroll, volume, zoom,
move windows between monitors, task view and more.

> **v3 (beta)** splits the project into a **Python engine** (vision + gestures)
> and a **Tauri + React app** that runs it as a sidecar. v2 (PyQt) lives on in
> tag `v2.0.0` and branch `legacy/v2`.

---

## ✋ Gestures

| Gesture | Action |
|---|---|
| ☝️ point with the index | Mouse — the cursor follows the hand |
| …🤏 touch the tips of thumb and index | Click (twice = double click); pinch and move = drag; hold = right click |
| …a quick flick sideways | Jump the cursor to the next monitor |
| …park the hand at the camera's edge | The cursor keeps going that way (reach the corners) |
| ✌️ two fingers, move the hand | Scroll whatever is under the cursor — point at it first, no click needed |
| 🤟 three fingers, raise / lower | Volume — same height, same level |
| 🤏 pinch, open / close | Zoom |
| ✋ → ✊ and drag | Move the window (smooth, accelerated, across monitors) |
| …open the hand **tilted** towards a side | Send it to that monitor and maximize it there |
| …park the hand at the camera's edge | Push it on to the next monitor |
| …flick up | Maximize |
| …open the hand with the **fingers down** (or drag it to the bottom edge and open) | Close |
| …open the hand upright | Let go where it is (taken to the top of a monitor = maximize) |
| ✋✋ bring the palms together | Task view (Win+Tab) |
| … then ☝️ point and 🤏 pinch | Open that window (a click) |
| … then ✋✋ move the palms apart | Leave: the window under the cursor if you pointed, else back (Esc) |
| 🖖 four fingers → ✊ | Play / pause media |
| 👆👆 both hands in an L, framing the screen | Screenshot (Win+PrintScreen) |
| ✋✋ both palms still for 1 s | Turn GestureKey on / off (works while off) |

After any gesture nothing new starts for 0.8 s, so putting the hand down never
fires another one. Settings (camera, which gestures are on) are stored in
`%APPDATA%\GestureKey\settings.json`.

---

## 🧩 Layout

```
engine/                 Python engine (uv)
  gesturekey/
    core/               types, geometry, filters, cooldowns — no UI, no OS calls
    vision/             camera, MediaPipe tracker, classifier, probabilistic state filter
    gestures/           pure gesture detectors + the arbiter (who owns the hand)
    actions/            the only part that touches the OS: keys, scroll, windows, volume
    runtime/            engine loop, WebSocket server, recorder, debug window
    tools/              collect / train / replay / export / analyze
    models/             hand_state_rf.pkl
  training/             datasets and the training guide
  tests/                gestures tested with synthetic frames, no camera
app/                    Tauri 2 + React 19 + Tailwind 4 UI (pnpm)
  src/                  app window and the feedback overlay
  src-tauri/            Rust: spawns the engine, tray, overlay window
docs/                   protocol, design system, gesture catalog, testing, platforms
```

```
camera → tracker (One Euro) → classifier → state filter (HMM) → arbiter → gestures → actions → OS
                                                                        ↘ WebSocket → app + overlay
```

- **Gestures only detect.** They return actions (`Hotkey`, `Scroll`,
  `WindowMove`, `VolumeSet`…); the `ActionExecutor` performs them on its own
  thread, and animates dragged windows at 120 Hz.
- **The arbiter** gives the hand to one gesture at a time: while you drag a
  window, nothing else fires.

---

## 🚀 Development

Requirements: Python 3.11 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, Rust.

```bash
cd /d/GestureKey/engine && uv sync && uv run pytest
```

```bash
cd /d/GestureKey/app && pnpm install && pnpm tauri dev
```

Other ways to run the engine:

```bash
cd /d/GestureKey/app && pnpm engine            # WebSocket server only (ws://127.0.0.1:8765)
```

```bash
cd /d/GestureKey/app && pnpm engine:debug      # OpenCV window with landmarks, no UI
```

Record a session and inspect it:

```bash
cd /d/GestureKey/app && GESTUREKEY_RECORD=1 pnpm tauri dev
```

```bash
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.analyze --latest
```

```bash
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.export --latest    # CSV of movements
```

Check a gesture filmed with any camera app:

```bash
cd /d/GestureKey/engine && uv run python -m gesturekey.tools.replay clip.mp4 --trace
```

Retrain the hand-pose model: see [engine/training/README.md](engine/training/README.md).

### Build

```bash
cd /d/GestureKey/app && pnpm release           # PyInstaller engine + NSIS installer
```

> To move windows of apps that run as administrator, GestureKey must run as
> administrator too.

---

## 👨‍💻 Author

Angel Gabriel Crispin Valdivia
