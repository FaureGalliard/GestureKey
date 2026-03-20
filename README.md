# GestureKey

Control your computer with hand gestures using your webcam. Built with Tauri + React + TypeScript + Python (MediaPipe).

## Requirements

- [Node.js](https://nodejs.org/) 18+
- [Rust](https://rustup.rs/)
- [Python](https://www.python.org/downloads/) 3.11
- Webcam

## Quick start (development)

**1. Clone the repo**

```bash
git clone https://github.com/FaureGalliard/gesturekey
cd gesturekey
```

**2. Install Node dependencies**

```bash
npm install
```

**3. Set up Python environment**

```bash
cd src/backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

**4. Build the Python server**

```bash
# Still inside src/backend with .venv active
pyinstaller server.spec --clean --noconfirm
```

**5. Copy the server to src-tauri**

```bash
# Windows (from project root)
xcopy /E /I src\backend\dist\server src-tauri\server

# Linux/Mac
cp -r src/backend/dist/server src-tauri/server
```

**6. Run in development mode**

```bash
# From project root
npm run tauri dev
```

## Build installer

```bash
# From project root
npm run tauri build
```

The installer is generated in `src-tauri/target/release/bundle/nsis/`.

## Project structure

```
gesturekey/
├── src/                  # React + TypeScript frontend
│   ├── backend/          # Python server (MediaPipe, gestures)
│   │   ├── gestures/     # Gesture detection logic
│   │   ├── vision/       # Camera, hand tracking, classifier
│   │   ├── pipeline/     # State management, cooldowns
│   │   ├── models/       # Trained ML model (.pkl)
│   │   └── server.py     # WebSocket server entry point
│   └── components/       # React components
├── src-tauri/            # Rust/Tauri desktop wrapper
└── public/
```

## Gestures

| Gesture                 | Action             |
| ----------------------- | ------------------ |
| Two fingers up + move   | Scroll             |
| Three fingers up + move | Volume             |
| Pinch + move            | Zoom               |
| Palm → Fist             | Pause/Resume media |
| Palm + Fist + Palm      | Mute toggle        |
| Fist swipe down         | Close window       |
| Both palms approach     | Task view          |

## Recommended IDE

[VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
