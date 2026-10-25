# Prueba manual de gestos

Línea base antes de tocar el jitter: cuánto tiembla, cuánto parpadea el estado y qué
gestos funcionan hoy con la MX Brio. Toma unos 20 minutos. Anota en la tabla del final.

## 0. Preparación

1. Luz de frente (no a tu espalda), cámara a la altura de los ojos, tú a **~70 cm**.
2. Cierra las apps que usen la cámara (OBS, Teams, Logi Tune con vista previa).
3. Lanza con la grabación activada:

   ```bash
   cd /d/GestureKey/app && GESTUREKEY_RECORD=1 pnpm tauri dev
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
| C1 | Desplazar | navegador, página larga | ✌️ dos dedos; aleja la mano un poco hacia abajo o arriba y **mantenla ahí** | scroll continuo, más rápido cuanto más lejos; vuelve al punto inicial y para; bájala rápido y termina sin saltos |
| C2 | Volumen | cualquier sitio | 🤟 tres dedos; sube o baja la mano | la barra del overlay sigue tu altura; sube y vuelve: el mismo volumen del inicio |
| C3 | Zoom | navegador | 🤏 pinza; abre o cierra el pulgar y el índice | un paso de zoom por cada apertura; vuelve a cerrar y regresa al zoom inicial |
| C4 | Mover ventana | Bloc de notas sin maximizar | ✋ palma → ✊ puño y mantén → mueve → ✋ abre | la ventana sigue a la mano, aguanta movimientos rápidos y **se queda donde la sueltas** |
| C5 | Acoplar | Bloc de notas | igual que C4, pero **lánzala** rápido a un lado y abre la mano en el lanzamiento | se acopla a esa mitad |
| C6 | Maximizar | Bloc de notas | igual que C5, lanzándola hacia arriba | se maximiza |
| C7 | Encender / apagar | cualquier sitio | ✋✋ dos palmas **quietas** | aparece el anillo arriba; a 1.5 s se apaga; repite para encender |
| C8 | Reproducir / pausar | YouTube | 🖖 cuatro dedos un momento → ✊ | pausa o reanuda el video (ya no apaga los gestos) |
| C9 | Vista de tareas | escritorio | ✋✋ dos palmas separadas → júntalas | Win+Tab |
| C10 | Captura | cualquier sitio | ✋ palma cerca → empújala rápido lejos de la cámara | toast "Captura guardada"; aparece en Imágenes › Capturas de pantalla |
| C11 | Cerrar ventana | **un Bloc de notas vacío** | ✊ puño **quieto** un momento → tirón rápido hacia abajo | Alt+F4 |

## D. Conflictos · ~2 min

| # | Prueba | Esperado |
|---|---|---|
| D1 | Agarra una ventana (C4) y arrástrala **rápido hacia abajo** | se mueve, **no** se cierra |
| D2 | ✋ → ✊ (pasando por cuatro dedos) | agarra la ventana, **no** pausa el video |
| D3 | Scroll con ✌️ y, sin bajar la mano, pasa a 🤟 | el scroll se detiene; no salta el volumen de golpe |
| D4 | ✋✋ dos palmas que se **acercan** | vista de tareas, **no** el anillo de apagar |

## E. Uso normal · 2 min

Con los gestos activos, usa la PC como siempre: escribe, usa el mouse, tócate la cara,
toma agua, gesticula hablando. **No hagas gestos a propósito.**

Cuenta en *Actividad* los eventos que se dispararon solos: son los falsos positivos.

## F. Cerrar y analizar

1. Cierra GestureKey desde la bandeja (**Salir**): así se cierra el archivo de grabación.
2. Analiza la última grabación:

   ```bash
   cd /d/GestureKey/engine && uv run python -m gesturekey.tools.analyze --latest
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
| C7 Encender / apagar | | | |
| C8 Reproducir / pausar | | | |
| C9 Vista de tareas | | | |
| C10 Captura | | | |
| C11 Cerrar ventana | | | |
| D1–D4 | | | |
| E (falsos en 2 min) | — | | |
| A/B (parpadeos que viste) | — | | |

## Qué cambió desde la primera prueba

- Landmarks filtrados una sola vez (One Euro) y estados con filtro probabilístico: menos parpadeo.
- Los gestos continuos terminan al cambiar de pose, al dudar el modelo o al bajar la mano rápido.
- Scroll tipo joystick, volumen absoluto y zoom reversible (con deshacer del último ¼ s al salir).
- Silenciar está **apagado por defecto** (chocaba con mover ventanas); vuelve con 👎.
- Overlay arriba de la pantalla con el gesto en curso, toasts y el anillo de encender/apagar.
