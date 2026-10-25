# Protocolo motor ⇄ UI

El motor (`engine/`) escucha en `ws://127.0.0.1:8765`. Cada mensaje es un objeto JSON.
Solo se aceptan los orígenes de Tauri (`http://tauri.localhost`, `tauri://localhost`),
el de Vite en dev (`http://localhost:1420`) y clientes sin `Origin` (CLI, tests).
Los tipos de TypeScript están en `app/src/lib/protocol.ts`.

## Motor → UI

| `type`    | Cuándo | Campos |
|-----------|--------|--------|
| `hello`   | al conectar | `version`, `config` (AppConfig completo), `enabled`, `camera`, `camera_status` (últimos o `null`) |
| `frame`   | cada frame procesado (30–60 Hz) | `t`, `state`, `raw_state`, `confidence`, `hands[]`, `owner`, `owner_info`, `arming`, `enabled`, `fps` |
| `event`   | un gesto se disparó | `event` (p. ej. `SCROLL`, `GRAB_WINDOW_START`), `t` |
| `status`  | log del motor | `level` (`info`/`warn`/`error`), `message` |
| `camera`  | cámara abierta | `device`, `width`, `height`, `fps` |
| `camera_status` | cada cambio de la cámara | `status` (`opening` / `ok` / `reconnecting` / `busy` / `missing`), `device`, `name`, `message` (texto para el usuario), `low_light`, `measured_fps` |
| `cameras` | respuesta a `list_cameras` | `devices[]` (`index`, `name`), `active` |
| `config`  | tras `set_config` | `config` |
| `enabled` | tras `set_enabled` | `enabled` |
| `preview` | ~12 fps, solo con preview activo | `jpeg` (base64, 480 px de ancho) |

`hands[]`: `{ side: "Left" | "Right", score, landmarks: [[x, y] × 21] }`, en
coordenadas de imagen 0..1 ya espejadas (x crece hacia la derecha del usuario).

`owner`: nombre del gesto que tiene la mano en ese momento (p. ej. `GRAB_WINDOW`), o `null`.

## UI → motor

| `cmd`          | Campos | Efecto |
|----------------|--------|--------|
| `set_config`   | `patch`: AppConfig parcial | mezcla, guarda en `%APPDATA%/GestureKey/settings.json` y aplica (reabre la cámara si cambió) |
| `set_enabled`  | `enabled` | apaga/enciende todos los gestos (el tracking sigue) |
| `preview`      | `on` | activa/desactiva los mensajes `preview` |
| `list_cameras` | — | busca cámaras (sin tocar la activa) y responde con `cameras` |
| `set_config` con `ui.language` | `"auto"`, `"en"`, `"es"`, `"fr"`, `"ko"` | idioma de la app y del overlay (los dos lo leen de la config) |
| `reconnect_camera` | — | reintenta abrir la cámara ahora (el motor ya reintenta solo cada 3 s) |
