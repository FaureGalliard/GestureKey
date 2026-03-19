export type HandState =
    | 'PALM'
    | 'FIST'
    | 'PINCH'
    | 'TWO_FINGERS'
    | 'THREE_FINGERS'
    | 'FOUR_FINGERS'
    | 'UNKNOWN'
    | 'NO HANDS'

export type GestureEvent =
    | 'SCROLL'
    | 'VOLUME_UP'
    | 'VOLUME_DOWN'
    | 'ZOOM_IN'
    | 'ZOOM_OUT'
    | 'SCREENSHOT'
    | 'CLOSE_WINDOW'
    | 'MUTE_TOGGLE'
    | 'TASK_VIEW'
    | 'PAUSE_TOGGLE_PAUSED'
    | 'PAUSE_TOGGLE_RESUMED'

export interface GestureMessage {
    state: HandState
    raw_state: HandState
    confidence: number
    event?: GestureEvent
    timestamp: number
}
