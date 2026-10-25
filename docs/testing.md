# Prueba manual de gestos

Línea base antes de tocar el jitter: cuánto tiembla, cuánto parpadea el estado y qué
gestos funcionan hoy con la MX Brio. Toma unos 20 minutos. Anota en la tabla del final.

## 0. Preparación

1. Luz de frente (no a tu espalda), cámara a la altura de los ojos, tú a **~70 cm**.
2. Cierra las apps que usen la cámara (OBS, Teams, Logi Tune con vista previa).
3. Lanza con la grabación activada (PowerShell):

   ```powershell
   cd D:\GestureKey\app; $env:GESTUREKEY_RECORD=1; pnpm tauri dev
   ```

   En **Ajustes › Avanzado › Actividad** debe aparecer "Grabando sesión en …".
4. Deja abierto **Ajustes › Avanzado**: ahí ves el estado detectado, la confianza y cada evento.
5. ⚠️ Guarda tu trabajo: *Cerrar ventana* manda Alt+F4 de verdad.

Usa la **mano derecha** salvo que se indique otra.

## A. Quieto (jitter y parpadeo) · ~3 min

Sostén cada pose **5 s sin moverte** con la palma hacia la cámara, y baja la mano 2 s
entre pose y pose (así la grabación las separa sola).

| # | Pose | Qué mirar |
|---|---|---|
| A1 | ✋ palma abierta | ¿el estado se queda fijo en "Mano abierta"? |
| A2 | ✊ puño | |
| A3 | 🤏 pinza (pulgar + índice juntos) | |
| A4 | ✌️ dos dedos | |
| A5 | 🤟 tres dedos | |
| A6 | 🖖 cuatro dedos | |
| A7 | ✋ palma, **a 1.2 m** | ¿se pierde la mano o parpadea más? |
| A8 | ✋ palma, con **menos luz** (apaga una lámpara) | |
| A9 | ✋ palma con la **mano izquierda** | ¿dice "IZQ" en el dibujo? |

## B. Transiciones · ~2 min

| # | Prueba | Qué mirar |
|---|---|---|
| B1 | Palma ↔ puño, lento, 5 veces | ¿cada cambio se detecta una vez, sin estados intermedios raros? |
| B2 | Palma girando de frente a perfil | ¿en qué ángulo deja de ser "Mano abierta"? |
| B3 | Mano relajada, sin pose (como apoyada) | ¿qué estado dice? (no debería disparar nada) |

## C. Cada gesto, 5 intentos · ~10 min

Anota **aciertos / 5**, **falsos** (se disparó otra cosa) y cómo se sintió
(retraso, saltos, demasiado sensible).

| # | Gesto | Dónde | Cómo | Resultado esperado |
|---|---|---|---|---|
| C1 | Desplazar | navegador, página larga | ✌️ dos dedos, espera ½ s, sube y baja la mano (lento y rápido) | scroll fluido; se detiene al quedarte quieto |
| C2 | Volumen | cualquier sitio | 🤟 tres dedos **apuntando a la cámara**, sube y baja | sube/baja el volumen de Windows |
| C3 | Zoom | navegador | 🤏 pinza **apuntando a la cámara**, abre y cierra | Ctrl + / Ctrl − |
| C4 | Mover ventana | Bloc de notas sin maximizar | ✋ palma ½ s → ✊ puño y mantén → mueve → ✋ abre | la ventana sigue a la mano y **se queda donde la sueltas** |
| C5 | Acoplar | Bloc de notas | igual que C4, pero lánzala rápido a la derecha / izquierda | se acopla a esa mitad |
| C6 | Maximizar | Bloc de notas | igual que C4, pero lánzala rápido hacia arriba | se maximiza |
| C7 | Silenciar | cualquier sitio | ✋ → ✊ muy rápido → ✋ | silencia / quita silencio |
| C8 | Pausa | YouTube | 🖖 cuatro dedos ½ s → ✊ | pausa el video y Inicio dice "Pausado con un gesto"; repetir reanuda |
| C9 | Vista de tareas | escritorio | ✋✋ dos palmas separadas → júntalas | Win+Tab |
| C10 | Captura | cualquier sitio | ✋ palma cerca → empújala rápido lejos de la cámara | aparece en Imágenes › Capturas de pantalla |
| C11 | Cerrar ventana | **un Bloc de notas vacío** | ✊ puño → tirón rápido hacia abajo | Alt+F4 |

## D. Conflictos · ~2 min

| # | Prueba | Esperado |
|---|---|---|
| D1 | Agarra una ventana (C4) y arrástrala **rápido hacia abajo** | se mueve, **no** se cierra |
| D2 | ✋ → ✊ y suelta en menos de ⅓ s | silencia o nada, pero **no** agarra la ventana |
| D3 | Scroll con ✌️ y, sin bajar la mano, pasa a 🤟 | el scroll se detiene; no salta el volumen de golpe |
| D4 | ✋✋ dos palmas quietas 3 s, sin acercarlas | no pasa nada (aún no hay gesto de apagar) |

## E. Uso normal · 2 min

Con los gestos activos, usa la PC como siempre: escribe, usa el mouse, tócate la cara,
toma agua, gesticula hablando. **No hagas gestos a propósito.**

Cuenta en *Actividad* los eventos que se dispararon solos: son los falsos positivos.

## F. Cerrar y analizar

1. Cierra GestureKey desde la bandeja (**Salir**): así se cierra el archivo de grabación.
2. Analiza la última grabación:

   ```powershell
   cd D:\GestureKey\engine; uv run python -m gesturekey.tools.analyze --latest
   ```

3. Pásame la salida y la tabla de abajo.

## Tabla de resultados

| # | Aciertos / 5 | Falsos | Notas |
|---|---|---|---|
| C1 Desplazar | | | |
| C2 Volumen | | | |
| C3 Zoom | | | |
| C4 Mover ventana | | | |
| C5 Acoplar | | | |
| C6 Maximizar | | | |
| C7 Silenciar | | | |
| C8 Pausa | | | |
| C9 Vista de tareas | | | |
| C10 Captura | | | |
| C11 Cerrar ventana | | | |
| D1–D4 | | | |
| E (falsos en 2 min) | — | | |
| A/B (parpadeos que viste) | — | | |

## Lo que ya sospecho que va a fallar

- **C7 Silenciar:** exige que el puño dure *exactamente un* frame estable; a 30 fps casi nunca pasa.
- **C11 Cerrar ventana:** mide el centro de la mano *relativo a la muñeca*, así que responde a
  doblar la muñeca más que a bajar el puño.
- **C1–C3:** sus umbrales son por frame y estaban ajustados para la cámara anterior
  (~16 fps); a ~30 fps pueden sentirse lentos o con zona muerta grande.
