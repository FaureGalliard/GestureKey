// Mirror of the engine WebSocket protocol — see docs/protocol.md.

export const ENGINE_URL = "ws://127.0.0.1:8765";

export type Landmark = [number, number];

export interface HandMsg {
  side: "Left" | "Right";
  score: number;
  landmarks: Landmark[]; // 21 points, image space 0..1, already mirrored
}

export interface FrameMsg {
  type: "frame";
  t: number;
  state: string;
  raw_state: string;
  confidence: number;
  hands: HandMsg[];
  owner: string | null;
  paused: boolean;
  fps: number;
}

export interface EventMsg { type: "event"; event: string; t: number }
export interface StatusMsg { type: "status"; level: "info" | "warn" | "error"; message: string }
export interface PreviewMsg { type: "preview"; jpeg: string }
export interface CameraMsg { type: "camera"; device: number; width: number; height: number; fps: number }
export interface CamerasMsg { type: "cameras"; devices: { index: number; name: string }[]; active: number }
export interface ConfigMsg { type: "config"; config: EngineConfig }
export interface EnabledMsg { type: "enabled"; enabled: boolean }
export interface HelloMsg {
  type: "hello"; version: string; config: EngineConfig; enabled: boolean; camera: CameraMsg | null;
}

export type EngineMsg =
  | HelloMsg | FrameMsg | EventMsg | StatusMsg | PreviewMsg
  | CameraMsg | CamerasMsg | ConfigMsg | EnabledMsg;

export type Command =
  | { cmd: "set_config"; patch: DeepPartial<EngineConfig> }
  | { cmd: "set_enabled"; enabled: boolean }
  | { cmd: "preview"; on: boolean }
  | { cmd: "list_cameras" };

export type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export interface GestureToggle { enabled: boolean; [param: string]: number | boolean }

export interface EngineConfig {
  camera: { device: number; width: number; height: number; fps: number; mirror: boolean };
  tracking: { model_complexity: number; min_detection_confidence: number; min_tracking_confidence: number };
  stabilizer: { window: number; consensus: number; min_confidence: number };
  gestures: { cooldown: number } & Record<GestureKey, GestureToggle>;
}

export const GESTURES = {
  scroll:       { label: "Desplazar",        hint: "Dos dedos arriba, mueve la mano arriba o abajo" },
  zoom:         { label: "Zoom",             hint: "Junta el pulgar y el índice, ábrelos o ciérralos" },
  task_view:    { label: "Vista de tareas",  hint: "Dos palmas abiertas separadas, júntalas" },
  grab_window:  { label: "Mover ventanas",   hint: "Palma, luego cierra el puño y arrastra; abre la mano para soltar" },
  close_window: { label: "Cerrar ventana",   hint: "Puño cerrado con un tirón hacia abajo" },
  volume:       { label: "Volumen",          hint: "Tres dedos hacia la cámara, sube o baja la mano" },
  mute:         { label: "Silenciar",        hint: "Palma, puño rápido y palma otra vez" },
  pause:        { label: "Reproducir / pausar", hint: "Cuatro dedos y cierra el puño" },
  screenshot:   { label: "Captura de pantalla", hint: "Empuja la palma abierta lejos de la cámara" },
} as const;

export type GestureKey = keyof typeof GESTURES;

export const GESTURE_GROUPS: { title: string; keys: GestureKey[] }[] = [
  { title: "Navegar",       keys: ["scroll", "zoom", "task_view"] },
  { title: "Ventanas",      keys: ["grab_window", "close_window"] },
  { title: "Sonido y medios", keys: ["volume", "mute", "pause"] },
  { title: "Otros",         keys: ["screenshot"] },
];

/** Hand states in plain words, for people who don't care about class names. */
export const STATE_LABELS: Record<string, string> = {
  PALM: "Mano abierta",
  FIST: "Puño",
  PINCH: "Pinza",
  TWO_FINGERS: "Dos dedos",
  THREE_FINGERS: "Tres dedos",
  FOUR_FINGERS: "Cuatro dedos",
  UNKNOWN: "…",
  "NO HANDS": "Sin mano",
};

export const EVENT_LABELS: Record<string, string> = {
  SCROLL: "Scroll",
  VOLUME_UP: "Volumen +",
  VOLUME_DOWN: "Volumen −",
  ZOOM_IN: "Zoom +",
  ZOOM_OUT: "Zoom −",
  SCREENSHOT: "Captura",
  CLOSE_WINDOW: "Cerrar ventana",
  MUTE_TOGGLE: "Silenciar",
  TASK_VIEW: "Vista de tareas",
  PAUSE_TOGGLE_PAUSED: "Pausado",
  PAUSE_TOGGLE_RESUMED: "Reanudado",
  GRAB_WINDOW_START: "Ventana agarrada",
  GRAB_WINDOW_RELEASED: "Ventana soltada",
};
