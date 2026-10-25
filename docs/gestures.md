# Gestos: catálogo y plan para que no se solapen

## 1. El vocabulario

Un gesto = **pose** × **movimiento** × **manos** × **tiempo**.

| Ingrediente | Valores |
|---|---|
| Pose (clasificador) | hoy: ✋ palma, ✊ puño, 🤏 pinza, ✌️ dos, 🤟 tres, 🖖 cuatro · **por entrenar:** ☝️ índice, 👍 pulgar arriba, 👎 pulgar abajo, 🤘 rock, 👌 OK, y una clase **OTRO** (mano relajada / en transición) |
| Movimiento | quieto (mantener), deslizar ← → ↑ ↓, empujar / jalar (profundidad), girar la muñeca, tirón (flick) |
| Manos | una, dos (simétricas: acercar, separar, mantener) |
| Tiempo | toque (< 0.3 s), mantener (≥ 0.4 s), mantener largo (≥ 1.5 s) |

## 2. Cómo evitar que se solapen

**Regla 1: cada pose es una familia.** Una pose de inicio pertenece a una sola familia, y
la dirección del movimiento elige la acción dentro de ella (como los gestos de touchpad de
Windows: 3 dedos = apps, 4 dedos = escritorios). Cuatro direcciones + mantener = 5 acciones
por pose como máximo.

**Regla 2: armar → actuar → soltar.** Todo gesto empieza con su pose **sostenida** (armado,
~0.2 s). Moverse sin haber armado no hace nada. Esto ya existe (`arm_time`) y es lo que
evita disparos al rascarse la cara.

**Regla 3: ningún gesto es prefijo de otro.** Hoy *silenciar* (palma → puño → palma) es
prefijo de *mover ventana* (palma → puño sostenido). Se resolvió con tiempo, pero es frágil:
el plan mueve silenciar a 👎 y elimina el prefijo.

**Regla 4: lo destructivo pide más.** Cerrar ventana, apagar GestureKey o bloquear la PC
piden mantener más tiempo o un paso de confirmación; lo inocuo (scroll, volumen) es inmediato.

**Regla 5: un dueño a la vez.** El árbitro (ya existe) da la mano al primer gesto que se
activa y silencia a los demás hasta que termina.

**Regla 6: zona activa (opcional).** Solo cuenta lo que ocurre con la mano levantada por
encima de una línea, o acercada a la cámara (como volumen y zoom ya hacen con la profundidad).
Las manos sobre el teclado o en la cara no disparan nada.

**Regla 7: medirlo con tests.** Un test de "matriz de conflictos": para cada gesto, se graba
o sintetiza su secuencia y se comprueba que **solo** ese gesto se dispara. La infraestructura
de frames sintéticos de `engine/tests` ya lo permite.

**Regla 8: feedback visible.** La UI (y más adelante un overlay pequeño) muestra cuándo un
gesto está armado, con un anillo de progreso en los que se mantienen. Si el usuario ve que
algo se está armando, puede abortarlo.

## 3. Apagar / encender GestureKey

**Propuesta:** ✋✋ **dos palmas quietas frente a la cámara durante 1.5 s**, con anillo de
progreso. Es deliberado, casi imposible por accidente y no choca con *vista de tareas*
(que exige *acercar* las palmas: movimiento contra quietud).

Detalle de implementación: cuando GestureKey está apagado, el motor sigue detectando
**solo** este gesto, para poder volver a encenderlo sin tocar nada. Hoy `set_enabled(false)`
apaga el árbitro entero; habrá que separar un detector de "despertar".

El gesto actual de 🖖 → ✊ (que pausa los gestos *y* la música a la vez) se separa en dos:
este para encender/apagar, y otro solo para multimedia.

## 4. Catálogo

Prioridad: **A** = sin reentrenar (poses actuales) · **B** = requiere poses nuevas ·
**C** = más adelante. ✔ = ya existe.

### Ventanas y multitarea

| Gesto | Acción | Teclado | Prio |
|---|---|---|---|
| ✋ → ✊ sostenido + mover | Mover ventana; lanzarla a un lado = acoplar, arriba = maximizar | — | ✔ |
| 🤟 tres dedos ← → | Cambiar de app | Alt+Tab | A |
| 🖖 cuatro dedos ← → | Escritorio virtual anterior / siguiente | Ctrl+Win+← / → | A |
| ✋✋ acercar | Vista de tareas | Win+Tab | ✔ |
| ✊✊ acercar | Mostrar escritorio | Win+D | A |
| ✋ deslizar abajo (lento) | Minimizar ventana | Win+↓ | A |
| ✊ sostenido + tirón abajo | Cerrar ventana (con armado más largo) | Alt+F4 | ✔ (endurecer) |
| ✌️ dos dedos ← → | Pestaña anterior / siguiente | Ctrl+Shift+Tab / Ctrl+Tab | A |
| ✌️ dos dedos tirón abajo | Cerrar pestaña | Ctrl+W | A |

### Mouse

| Gesto | Acción | Prio |
|---|---|---|
| ☝️ índice + mover | Mover el cursor (modo trackpad relativo, filtrado One Euro) | B |
| ☝️ + pinza rápida pulgar-índice | Clic | B |
| ☝️ + dos pinzas | Doble clic | B |
| ☝️ + pinza pulgar-medio | Clic derecho | B |
| ☝️ + pinza sostenida + mover | Arrastrar | B |
| ✌️ dos dedos ↑ ↓ | Scroll | ✔ |

### Sonido y multimedia

| Gesto | Acción | Prio |
|---|---|---|
| 🤟 tres dedos hacia la cámara ↑ ↓ | Volumen | ✔ |
| 👎 mantener | Silenciar (reemplaza palma-puño-palma) | B |
| 🤘 rock ← → | Canción anterior / siguiente | B |
| 🤘 rock mantener | Reproducir / pausar | B |

### Otros

| Gesto | Acción | Prio |
|---|---|---|
| ✋✋ quietas 1.5 s | Encender / apagar GestureKey | A |
| 🤏 pinza hacia la cámara, abrir / cerrar | Zoom | ✔ |
| ✋ empujar lejos de la cámara | Captura (opción: recorte con Win+Shift+S) | ✔ |
| 👍 mantener | Confirmar / Enter | B |
| 👌 OK mantener | Dictado por voz | C |
| — | **Perfiles por app**: el mismo gesto hace cosas distintas en el navegador, en un reproductor o en una presentación (← → = diapositiva) | C |
| — | **Asignación personalizada**: el usuario elige qué hace cada gesto desde Ajustes | C |

## 5. Orden propuesto

1. **Base:** gestos independientes de los fps, One Euro global, filtro bayesiano de estados
   (ver la clase de jitter). Sin esto, cada gesto nuevo hereda el ruido.
2. **Fase A:** encender/apagar con dos palmas, Alt+Tab, escritorios, pestañas, mostrar
   escritorio, minimizar, y la matriz de conflictos en los tests.
3. **Reentrenar:** herramienta de captura y entrenamiento con las poses nuevas + OTRO,
   usando world landmarks.
4. **Fase B:** mouse completo, multimedia con 🤘, 👍 / 👎.
5. **Fase C:** perfiles por app y asignación personalizada.
