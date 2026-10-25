# Plataformas

Hoy GestureKey corre en **Windows**. Linux (y quizá macOS) es un objetivo para más adelante.
No hace falta una versión aparte: casi todo el proyecto ya es multiplataforma y lo que
cambia está aislado detrás de interfaces pequeñas.

## Qué ya es multiplataforma

| Pieza | Linux |
|---|---|
| Tauri + React (UI, bandeja, overlay) | ✔ (bandeja según el escritorio) |
| Motor: MediaPipe, clasificador, filtros, gestos, árbitro, WebSocket | ✔ — puro Python/NumPy |
| Cámara (`vision/camera.py`) | ✔ — ya elige V4L2 en Linux; falta la lista de nombres (vía `v4l2-ctl` o `/sys/class/video4linux`) |

## Qué hay que escribir por plataforma

Todo vive en `engine/gesturekey/actions/`. Los gestos devuelven acciones (`Hotkey`,
`Scroll`, `WindowMove`, `VolumeSet`…); solo el ejecutor sabe cómo hacerlas.

| Acción | Windows (hoy) | Linux X11 | Linux Wayland |
|---|---|---|---|
| Teclas y atajos | `keybd_event` (ctypes) | XTest (`python-xlib`) | `uinput` (dispositivo virtual; requiere permisos) |
| Scroll | `mouse_event` | XTest | `uinput` |
| Mover / acoplar / maximizar ventanas | `SetWindowPos`, `ShowWindow` | EWMH (`python-xlib`) | **limitado**: el compositor no deja mover ventanas ajenas; solo atajos del escritorio (p. ej. Super+←) |
| Volumen del sistema | Core Audio (`pycaw`) | PipeWire / PulseAudio (`pulsectl`) | igual |
| Overlay siempre encima y sin clics | ✔ | ✔ | depende del compositor |
| Ejecutar como admin para ventanas elevadas | sí | no aplica | no aplica |

Plan: `actions/win32.py` + `actions/audio.py` pasan a ser el backend `windows`, y se añade
un backend `linux` (X11 primero; Wayland con lo que el compositor permita). El ejecutor
elige el backend al arrancar. Los gestos, los tests y la UI no cambian.
