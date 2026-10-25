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
  owner: string | null;                         // gesture that owns the hand right now
  owner_info: OwnerInfo | null;                 // its live values, e.g. { volume: 0.42 }
  arming: ArmingInfo | null;                    // a deliberate hold in progress
  enabled: boolean;
  fps: number;
}

export interface OwnerInfo {
  volume?: number;                          // VOLUME: current level 0..1
  rate?: number;                            // SCROLL
  zone?: "maximize" | "left" | "right";     // GRAB_WINDOW: what letting go now would do
  hold?: number;                            // MOUSE: still pinch on its way to a right click, 0..1
}

export interface ArmingInfo {
  gesture: string;     // "POWER"
  progress: number;    // 0..1
  action: "on" | "off";
}

export interface EventMsg { type: "event"; event: string; t: number }
export interface StatusMsg { type: "status"; level: "info" | "warn" | "error"; message: string }
export interface PreviewMsg { type: "preview"; jpeg: string }
export interface CameraMsg { type: "camera"; device: number; width: number; height: number; fps: number }
export interface CameraStatusMsg {
  type: "camera_status";
  status: "opening" | "ok" | "reconnecting" | "busy" | "missing";
  device: number;
  name: string;
  message: string;
  low_light?: boolean;
  measured_fps?: number;
}
export interface CamerasMsg { type: "cameras"; devices: { index: number; name: string }[]; active: number }
export interface ConfigMsg { type: "config"; config: EngineConfig }
export interface EnabledMsg { type: "enabled"; enabled: boolean }
export interface HelloMsg {
  type: "hello"; version: string; config: EngineConfig; enabled: boolean; camera: CameraMsg | null;
  camera_status: CameraStatusMsg | null;
}

export type EngineMsg =
  | HelloMsg | FrameMsg | EventMsg | StatusMsg | PreviewMsg
  | CameraMsg | CameraStatusMsg | CamerasMsg | ConfigMsg | EnabledMsg;

export type Command =
  | { cmd: "set_config"; patch: DeepPartial<EngineConfig> }
  | { cmd: "set_enabled"; enabled: boolean }
  | { cmd: "preview"; on: boolean }
  | { cmd: "list_cameras" }
  | { cmd: "reconnect_camera" };

export type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export interface GestureToggle { enabled: boolean; [param: string]: number | boolean }

export interface EngineConfig {
  camera: { name: string; device: number; width: number; height: number; fps: number; mirror: boolean };
  tracking: { min_detection_confidence: number; min_presence_confidence: number; min_tracking_confidence: number };
  states: { switch_rate: number; enter: number; floor: number };
  gestures: { cooldown: number } & Record<GestureKey, GestureToggle>;
  ui: { language: string };    // "auto" | "en" | "es" | "fr" | "ko"
}

/** Gestures the user can switch on/off, in display order. Their texts live in i18n. */
export const GESTURE_KEYS = [
  "mouse", "scroll", "zoom", "task_view", "grab_window", "volume", "mute", "pause", "power", "screenshot",
] as const;

export type GestureKey = (typeof GESTURE_KEYS)[number];

export const GESTURE_GROUPS: { id: "navigate" | "windows" | "media" | "other"; keys: GestureKey[] }[] = [
  { id: "navigate", keys: ["mouse", "scroll", "zoom", "task_view"] },
  { id: "windows",  keys: ["grab_window"] },
  { id: "media",    keys: ["volume", "mute", "pause"] },
  { id: "other",    keys: ["screenshot", "power"] },
];
