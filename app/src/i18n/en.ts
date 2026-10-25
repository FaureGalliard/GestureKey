// English is the reference: every other language must have exactly this shape (see Dict).
export const en = {
  langName: "English",

  home: {
    starting:     { title: "Starting…", subtitle: "Getting the camera and recognition ready." },
    opening:      { title: "Opening the camera…", subtitle: "One moment." },
    reconnecting: { title: "Reconnecting the camera…", subtitle: "The image was lost; back in a moment." },
    busy: {
      title: "The camera is busy",
      subtitle: "Another app is using the camera (Zoom, Discord, Teams, OBS…). Close it and GestureKey will connect by itself.",
    },
    missing: { title: "Camera not found", subtitle: "Plug in a camera and GestureKey will connect by itself." },
    paused: {
      title: "Paused",
      subtitle: "Gestures are off. Turn them on here, or hold both palms still in front of the camera.",
    },
    ready: { title: "Ready for your gestures", subtitle: "Move your hand in front of the camera to control your PC." },
    retry: "Retry now",
    retryAlt: "or pick another one in Settings › Camera",
    tip: "Tip: with good light from the front, recognition is steadier.",
    lowLight: (fps: number) =>
      `Low light: the camera is running at ${fps} fps. More light from the front makes gestures more precise.`,
    on: "On",
    off: "Off",
    toggle: "Turn gestures on",
    settings: "Settings",
  },

  preview: {
    showHand: "Show a hand to the camera",
    noImage: "No camera image",
    movingWindow: "Moving window",
  },

  settings: {
    title: "Settings",
    close: "Close",
    tabs: { general: "General", gestures: "Gestures", camera: "Camera", advanced: "Advanced" },
    general: {
      language: "Language",
      languageHint: "Used by the app and the on-screen notices.",
      auto: "Automatic (system)",
    },
    gestures: {
      intro: "Turn on only the ones you'll use: fewer gestures, fewer surprises.",
      groups: { navigate: "Navigate", windows: "Windows", media: "Sound & media", other: "Other" },
    },
    camera: {
      section: "Camera",
      device: "Device",
      noCameras: "No cameras",
      mirror: "Mirror view",
      mirrorHint: "Move your hand right and everything goes right.",
      video: "Show video",
      videoHint: "See the camera behind the hand on the home screen.",
      fallback: (i: number) => `Camera ${i}`,
    },
    advanced: {
      diagnostics: "Diagnostics",
      engine: "Engine",
      offline: "offline",
      camera: "Camera",
      processing: "Processing",
      detected: "Detected",
      detectedHint: "Before filtering.",
      owner: "Gesture in progress",
      none: "none",
      activity: "Activity",
      noEvents: "No events yet",
    },
  },

  gestures: {
    scroll:      { label: "Scroll", hint: "Two fingers and move your hand: the page follows; a quick flick goes further" },
    zoom:        { label: "Zoom", hint: "Pinch thumb and index, then open or close them" },
    task_view:   { label: "Task view", hint: "Two open palms apart, then bring them together. Inside: ✌️ move to pick, ✊ to open, palms apart to leave" },
    grab_window: {
      label: "Move windows",
      hint: "Palm, close your fist and drag; open it to let go. Open it tilted towards a side to send the window to that monitor; flick up to maximize; flick down and open to close",
    },
    volume:      { label: "Volume", hint: "Three fingers, raise or lower your hand" },
    mute:        { label: "Mute", hint: "Palm, quick fist, palm again (clashes with moving windows)" },
    pause:       { label: "Play / pause", hint: "Four fingers for a moment, then close your fist" },
    power:       { label: "On / off", hint: "Both open palms held still in front of the camera" },
    screenshot:  { label: "Screenshot", hint: "Hold your palm still for a moment, then push it away from the camera" },
  },

  states: {
    PALM: "Open hand",
    FIST: "Fist",
    PINCH: "Pinch",
    TWO_FINGERS: "Two fingers",
    THREE_FINGERS: "Three fingers",
    FOUR_FINGERS: "Four fingers",
    POINT: "Pointing",
    THUMB_DOWN: "Thumb down",
    OTHER: "Relaxed",
    UNKNOWN: "…",
    "NO HANDS": "No hand",
  } as Record<string, string>,

  events: {
    SCROLL: "Scroll",
    VOLUME_UP: "Volume +",
    VOLUME_DOWN: "Volume −",
    ZOOM_IN: "Zoom in",
    ZOOM_OUT: "Zoom out",
    SCREENSHOT: "Screenshot",
    CLOSE_WINDOW: "Close window",
    MUTE_TOGGLE: "Mute",
    TASK_VIEW: "Task view",
    TASK_VIEW_MOVE: "Task view: next window",
    TASK_VIEW_OPEN: "Task view: window opened",
    TASK_VIEW_CLOSED: "Task view closed",
    MEDIA_PLAY_PAUSE: "Play / pause",
    GRAB_WINDOW_START: "Window grabbed",
    GRAB_WINDOW_RELEASED: "Window released",
    WINDOW_TO_MONITOR: "Window to the other monitor",
    WINDOW_MAXIMIZED: "Window maximized",
    POWER_OFF: "GestureKey off",
    POWER_ON: "GestureKey on",
  } as Record<string, string>,

  overlay: {
    live: { SCROLL: "Scrolling", VOLUME: "Volume", ZOOM: "Zoom", GRAB_WINDOW: "Moving window", TASK_VIEW: "✌️ move · ✊ open · ✋✋ apart to leave" } as Record<string, string>,
    toasts: {
      CLOSE_WINDOW: "Window closed",
      WINDOW_TO_MONITOR: "Window moved to the other monitor",
      WINDOW_MAXIMIZED: "Window maximized",
      SCREENSHOT: "Screenshot saved",
      TASK_VIEW: "Task view",
      TASK_VIEW_OPEN: "Window opened",
      TASK_VIEW_CLOSED: "Task view closed",
      MUTE_TOGGLE: "Mute",
      MEDIA_PLAY_PAUSE: "Play / pause",
      POWER_OFF: "GestureKey off",
      POWER_ON: "GestureKey on",
    } as Record<string, string>,
    zones: { maximize: "Let go to maximize", left: "Let go to snap left", right: "Let go to snap right" },
    holdOff: "Hold to turn GestureKey off",
    holdOn: "Hold to turn GestureKey on",
  },

};

type Widen<T> = T extends (...args: infer A) => infer R ? (...args: A) => R
  : T extends string ? string
  : { [K in keyof T]: Widen<T[K]> };

/** The shape every language must provide. */
export type Dict = Widen<typeof en>;
