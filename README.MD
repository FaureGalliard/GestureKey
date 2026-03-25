# 🖐️ Hand Gesture System shortcuts

Sistema de deteccion de gestos que activa atajos de teclado (zoom,scroll,task-view, etc)

---

## 📌 Descripción

Este proyecto captura video desde la cámara, detecta la mano en tiempo real y clasifica su estado utilizando un modelo de Machine Learning entrenado previamente.

El sistema está dividido en componentes claros:

- Captura de cámara
- Detección de landmarks
- Clasificación de estado
- Gestión de gestos
- Visualización (modo debug)

---

## 🧩 Tecnologías utilizadas

### 🔹 OpenCV

Se utiliza para:

- Captura de la cámara
- Conversión de color (BGR → RGB)
- Dibujar overlays (texto, líneas, landmarks)
- Visualización en modo debug

### 🔹 MediaPipe

Se utiliza para:

- Detectar manos en la imagen
- Extraer 21 landmarks por mano
- Proveer estructura anatómica

### 🔹 Scikit-learn

Se utiliza para:

- Entrenar el modelo de clasificación
- Predecir el estado actual de la mano

## 🚀 Instalación

### 1️⃣ Crear entorno virtual (Python 3.11)

```bash
python3.11 -m venv venv
```

Activar:

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

```bash
python -m app.main
```

---

### 2️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecutar el proyecto

```bash
python app/main.py
```

```bash
 pyinstaller --onefile --uac-admin main.py
```

## 📈 Flujo de procesamiento

1. OpenCV captura un frame.
2. MediaPipe detecta la mano.
3. Se extraen los 21 landmarks.
4. El modelo clasifica el estado.
5. El gestor de gestos decide la acción.
6. Se dibujan overlays (si debug está activo).

---

## 🎯 Objetivo del proyecto

Separar claramente:

- Captura
- Detección
- Clasificación
- Lógica de negocio
- Visualización

---

## 📌 Requisitos

- Python 3.11
- Cámara funcional
- Sistema operativo compatible con OpenCV

---

## 👨‍💻 Autor

Angel Gabriel Crispin Valdivia

---

gestos en planes:

👉 (ONE_FINGER ) → Mover cursor
👉 (ONE_FINGER ) + mano acercándose (aumenta tamaño) → Click

✋ + swipe vertical (TWO_FINGERS) → Scroll
✌️ (TWO_FINGERS) + swipe horizontal → Cambiar entre apps

✋ + swipe vertical (THREE_FINGERS) → Control de volumen
🤟 (THREE_FINGERS) + swipe horizontal derecha → Siguiente canción
🤟 (THREE_FINGERS) + swipe horizontal izquierda → Canción anterior

🤏 (PINCH) → Zoom in/out
🤏 (PINCH 100%) → Captura de pantalla

✋ + ✋ (2 manos, PALM acercándose) → Vista de tareas (Task View)
✊ + ✊ (2 manos, FIST acercándose) → Minimizar todo / mostrar escritorio

✋ (PALM → FIST) → minimizar + Grab ventana (iniciar “agarre”)
✊ (FIST) + mover → mover ventana
✋ (PALM) → Soltar ventana

✋ (FOURFINGER-> FIST) pausar multimedia
