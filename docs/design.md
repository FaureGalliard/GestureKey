# Design system

GestureKey comparte lenguaje visual con **Vocal Teleprompter** (la base) y con
**angelcrispin.github.io** (los tokens y la tipografía). Los tokens viven en
`app/src/globals.css` (`@theme`); los componentes usan sus clases, nunca un hex suelto.

## De dónde sale cada cosa

| Elemento | Origen |
|---|---|
| Superficies oscuras `ink` / `chrome` / `chrome-raised` | Teleprompter (`#1a1a1a`, `#242424`) |
| Menús `chrome-raised`, `rounded-xl`, borde `white/10`, entrada `y:-6 → 0` en 140 ms | Teleprompter `Toolbar` |
| Switches y píldoras `rounded-full`, acento como relleno de "encendido" | Teleprompter `Toolbar` |
| Easing de paneles `cubic-bezier(0.32, 0.72, 0, 1)` | Teleprompter |
| Rampa de acento de un solo tono `#445ade` | Web `globals.css` |
| `accent-light` `#7698fe` (acento como texto o línea sobre oscuro) | Color de texto del teleprompter |
| Inter (con tamaño óptico: los títulos usan el corte Display) + Fira Code | Web `fonts.ts` (aquí empaquetadas con `@fontsource`, sin red) |
| Estructura en **filas separadas por líneas de 1 px**, no tarjetas | Web |
| Etiquetas de sección 11 px, semibold, `uppercase`, tracking | Web `TYPE_SCALE` |

La ventana es **nativa** (barra de Windows en tema oscuro). El teleprompter no tiene
bordes porque flota sobre otras apps; GestureKey es una app normal y no lo necesita.

## Layout

Una sola pantalla (Inicio, centrada, máx. 720 px) y un **panel de Ajustes** que se desliza
desde la derecha (botón de engranaje; se cierra con la X, Esc o clic fuera). Sin sidebar:
para una app de una sola función sería demasiado. Íconos: `lucide-react`, `strokeWidth` 1.75.

| Dónde | Para quién | Contenido |
|---|---|---|
| Inicio | todos | estado en lenguaje normal, interruptor principal, ajustes, la mano en vivo |
| Ajustes › Gestos | todos | gestos agrupados (Navegar, Ventanas, Sonido y medios, Otros) con switch |
| Ajustes › Cámara | todos | dispositivo, vista espejo, mostrar video |
| Ajustes › Avanzado | curiosos | fps, resolución, estado crudo + confianza, log del motor |

Lo técnico (fps, confianza, nombres de clase, log) vive **solo** en Avanzado. El resto de
la app habla en palabras normales ("Mano abierta", no `PALM`).

## Reglas

- **El color se gana por rareza.** El acento marca acción (botón primario, switch encendido,
  el gesto que se acaba de disparar) y nada más. Rojo `hold` solo cuando un gesto tiene la mano.
- **Dos tintas, no cinco:** `fg` titula, `fg-muted` explica; `fg-faint` solo para etiquetas
  secundarias y glifos, nunca para texto de cuerpo.
- **Líneas opacas** (`line`, `line-strong`): se leen igual sobre `chrome` y sobre el escenario.
- **Mono para datos** (fps, resolución, confianza, log); Inter para todo lo demás.

## Escala tipográfica

| Clase | Uso |
|---|---|
| `text-[30px] font-semibold tracking-[-0.02em]` | Título de página |
| `text-[14px] text-fg-muted` | Subtítulo de página |
| `text-[14px] font-medium` | Nombre de fila |
| `text-[12.5px] text-fg-faint` | Descripción de fila |
| `text-[11px] font-semibold uppercase tracking-[0.06em]` | Etiqueta de sección |
| `font-mono text-[12px]` | Datos y log (solo Avanzado) |

Inter lleva `cv11` (a de un solo piso) y `ss03` (comillas redondas) para un tono más editorial.
