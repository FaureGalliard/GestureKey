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
  grab_window:  { label: "Mover ventana",  hint: "Palma → puño sostenido, mueve; palma suelta" },
  scroll:       { label: "Scroll",         hint: "Dos dedos, sube o baja la mano" },
  volume:       { label: "Volumen",        hint: "Tres dedos hacia la cámara, sube o baja" },
  zoom:         { label: "Zoom",           hint: "Pinza hacia la cámara, abre o cierra" },
  task_view:    { label: "Vista de tareas", hint: "Dos palmas separadas, júntalas" },
  screenshot:   { label: "Captura",        hint: "Empuja la palma lejos de la cámara" },
  close_window: { label: "Cerrar ventana", hint: "Puño con un tirón hacia abajo" },
  mute:         { label: "Silenciar",      hint: "Palma → puño rápido → palma" },
  pause:        { label: "Pausa",          hint: "Cuatro dedos → puño (pausa todo)" },
} as const;

export type GestureKey = keyof typeof GESTURES;

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
