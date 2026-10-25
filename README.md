# 🖐️ GestureKey

Controla tu PC con gestos de la mano: scroll, volumen, zoom, mover ventanas,
vista de tareas y más, usando solo la webcam.

> **v3** separa el proyecto en un **motor Python** (visión + gestos) y una
> **app Tauri + React** que lo lanza como sidecar. La v2 (PyQt) sigue en el tag
> `v2.0.0` y en la rama `legacy/v2`.

---

## 🧩 Estructura

```
engine/                 Motor Python (uv)
  gesturekey/
    core/               tipos, geometría, filtros, cooldowns — sin Qt ni win32
    vision/             cámara, MediaPipe, clasificador, estabilizador
    gestures/           gestos puros + árbitro (quién tiene la mano)
    actions/            lo único que toca el SO: teclas, scroll, ventanas
    runtime/            loop del motor, servidor WebSocket, modo debug
    models/             hand_state_rf.pkl
  tests/                gestos probados con frames sintéticos
app/                    UI Tauri 2 + React 19 + Tailwind 4 (pnpm)
  src/                  React
  src-tauri/            Rust: lanza el motor, bandeja del sistema
docs/protocol.md        mensajes motor ⇄ UI
```

```
cámara → tracker → clasificador → estabilizador → árbitro → gestos → acciones → SO
                                                          ↘ WebSocket → UI (landmarks, estado, eventos)
```

- Los **gestos solo detectan**: devuelven acciones (`Hotkey`, `Scroll`,
  `WindowMove`…) y el `ActionExecutor` las ejecuta en su propio hilo.
- El **árbitro** da la mano a un solo gesto mientras está activo: mientras
  arrastras una ventana, *cerrar ventana* y *silenciar* no se disparan.

---

## 🚀 Desarrollo

Requisitos: Python 3.11 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, Rust (para Tauri).

```bash
cd engine
uv sync
uv run pytest
```

```bash
cd app
pnpm install
pnpm tauri dev          # lanza la UI y el motor (engine/.venv) como sidecar
```

Otras formas de correr el motor:

```bash
pnpm engine             # solo el servidor WebSocket (ws://127.0.0.1:8765)
pnpm engine:debug       # ventana de OpenCV con landmarks, sin UI
```

Para desarrollar la UI con el motor corriendo aparte, pon
`GESTUREKEY_NO_ENGINE=1` antes de `pnpm tauri dev`, o abre
`http://localhost:1420` en el navegador con `pnpm dev`.

### Build

```bash
cd app
pnpm release            # PyInstaller (motor) + instalador NSIS de Tauri
```

> Para mover ventanas de apps que corren como administrador, GestureKey
> también tiene que correr como administrador.

---

## ✋ Gestos

| Gesto | Acción |
|-------|--------|
| ✌️ Dos dedos + mover arriba/abajo | Scroll |
| 🤟 Tres dedos hacia la cámara + arriba/abajo | Volumen |
| 🤏 Pinza hacia la cámara + abrir/cerrar | Zoom (Ctrl + / Ctrl −) |
| ✋ → ✊ sostenido, mover, ✋ | Mover ventana (lanzamiento lateral = snap, hacia arriba = maximizar) |
| ✋ → ✊ rápido → ✋ | Silenciar |
| ✋ empujada lejos de la cámara | Captura (Win + Impr Pant) |
| ✊ con tirón hacia abajo | Cerrar ventana (Alt + F4) |
| ✋ + ✋ separadas que se juntan | Vista de tareas (Win + Tab) |
| 🖖 Cuatro dedos → ✊ | Pausa multimedia y pausa todos los gestos |

La configuración (cámara, umbrales, gestos activos) se guarda en
`%APPDATA%\GestureKey\settings.json`.

### Ideas pendientes

- ☝️ Un dedo → mover cursor; acercar → click
- ✌️ Dos dedos + swipe horizontal → cambiar de app
- 🤟 Tres dedos + swipe horizontal → siguiente/anterior canción
- ✊ + ✊ acercándose → mostrar escritorio
- Reentrenar el clasificador con datos de la cámara nueva (`training/`)

---

## 👨‍💻 Autor

Angel Gabriel Crispin Valdivia
