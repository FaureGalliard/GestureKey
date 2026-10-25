# Design system

GestureKey comparte lenguaje visual con **Vocal Teleprompter** (la base) y con
**angelcrispin.github.io** (los tokens y la tipografía). Los tokens viven en
`app/src/globals.css` (`@theme`); los componentes usan sus clases, nunca un hex suelto.

## De dónde sale cada cosa

| Elemento | Origen |
|---|---|
| Barra de título propia de 32 px, `chrome` `#1a1a1a`, título 11 px al 40 % | Teleprompter `TitleBar` |
| Píldoras `rounded-full` 11 px: primary `accent`, ghost `white/10`, divisores `w-px h-5` | Teleprompter `Toolbar` |
| Menús `chrome-raised` `#242424`, `rounded-xl`, borde `white/10`, entrada `y:-6 → 0` en 140 ms | Teleprompter `Toolbar` |
| Contorno de 1 px en el acento alrededor de la ventana | Teleprompter `App` |
| Easing de paneles `cubic-bezier(0.32, 0.72, 0, 1)` | Teleprompter |
| Rampa de acento de un solo tono `#445ade` | Web `globals.css` |
| `accent-light` `#7698fe` (acento como texto o línea sobre oscuro) | Color de texto del teleprompter |
| Inter + Fira Code | Web `fonts.ts` (aquí empaquetadas con `@fontsource`, sin red) |
| Estructura en **filas separadas por líneas de 1 px**, no tarjetas | Web |
| Etiquetas de sección 11 px, semibold, `uppercase`, `tracking-[0.04em]` | Web `TYPE_SCALE` |
| Display de 40 px `font-medium tracking-tight` (el estado de la mano) | Web `TYPE_SCALE` |

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
| `text-[40px] font-medium tracking-tight` | Estado de la mano |
| `text-[13px] font-medium` | Nombre de fila (gesto) |
| `text-[11px] font-semibold uppercase tracking-[0.04em]` | Etiqueta de sección |
| `text-[11px] font-medium uppercase tracking-[0.04em]` | Píldora |
| `text-[11px]` | Descripción de fila |
| `font-mono text-[10px]` | Datos y log |
