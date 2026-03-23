import { motion, AnimatePresence } from 'framer-motion'
import type { GestureState } from '../hooks/useGesture'
import type { GestureEvent, HandState } from '../types/gesture'

interface ConsoleProps {
    gesture: GestureState
}

const STATE_COLORS: Record<string, string> = {
    PALM: 'text-emerald-400',
    FIST: 'text-red-400',
    PINCH: 'text-yellow-400',
    TWO_FINGERS: 'text-blue-400',
    THREE_FINGERS: 'text-purple-400',
    FOUR_FINGERS: 'text-pink-400',
    UNKNOWN: 'text-white/30',
    'NO HANDS': 'text-white/20',
}

const EVENT_LABELS: Record<string, string> = {
    SCROLL: 'Scroll',
    VOLUME_UP: 'Volume ↑',
    VOLUME_DOWN: 'Volume ↓',
    ZOOM_IN: 'Zoom ↑',
    ZOOM_OUT: 'Zoom ↓',
    SCREENSHOT: 'Screenshot',
    CLOSE_WINDOW: 'Close Window',
    MUTE_TOGGLE: 'Mute Toggle',
    TASK_VIEW: 'Task View',
    PAUSE_TOGGLE_PAUSED: 'Paused',
    PAUSE_TOGGLE_RESUMED: 'Resumed',
}

function SectionLabel({ children }: { children: React.ReactNode }) {
    return (
        <p className="text-[9px] font-semibold tracking-[0.15em] text-white/20 uppercase mb-2">
            {children}
        </p>
    )
}

function HandIcon({ side }: { side: string }) {
    const isRight = side === 'Right'
    return (
        <span
            className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${isRight ? 'bg-blue-500/15 text-blue-300' : 'bg-orange-500/15 text-orange-300'}`}>
            {isRight ? 'R' : 'L'}
        </span>
    )
}

function formatTime(ts: number) {
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    })
}

export function Console({ gesture }: ConsoleProps) {
    const confidencePct = Math.round(gesture.confidence * 100)
    const stateColor = STATE_COLORS[gesture.state] ?? 'text-white/50'

    return (
        <div className="flex flex-col gap-5 p-4 h-full overflow-y-auto">
            {/* ── ESTADO ── */}
            <div>
                <SectionLabel>State</SectionLabel>
                <div className="flex items-center justify-between mb-2">
                    <span
                        className={`text-[13px] font-semibold font-mono tracking-wide ${stateColor}`}>
                        {gesture.state}
                    </span>
                    <span className="text-[11px] font-mono text-white/40">
                        {confidencePct}%
                    </span>
                </div>
                {/* confidence bar */}
                <div className="h-0.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-white/30 rounded-full"
                        animate={{ width: `${confidencePct}%` }}
                        transition={{ duration: 0.2 }}
                    />
                </div>
            </div>

            <div className="border-t border-white/5" />

            {/* ── MANOS ── */}
            <div>
                <SectionLabel>Hands</SectionLabel>
                <div className="flex items-center gap-2 h-5">
                    {gesture.hands.length === 0 ? (
                        <span className="text-[11px] text-white/15 font-mono">none</span>
                    ) : (
                        <AnimatePresence>
                            {gesture.hands.map((h) => (
                                <motion.div
                                    key={h}
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    transition={{ duration: 0.15 }}>
                                    <HandIcon side={h} />
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    )}
                </div>
            </div>

            <div className="border-t border-white/5" />

            {/* ── PAUSA ── */}
            <div>
                <SectionLabel>Detection</SectionLabel>
                <div className="flex items-center gap-2">
                    <div
                        className={`w-1.5 h-1.5 rounded-full ${gesture.paused ? 'bg-red-400' : 'bg-emerald-400'}`}
                    />
                    <span className="text-[11px] font-mono text-white/50">
                        {gesture.paused ? 'paused' : 'active'}
                    </span>
                </div>
            </div>

            <div className="border-t border-white/5" />

            {/* ── PIPELINE ── */}
            <div>
                <SectionLabel>Pipeline</SectionLabel>
                <div className="flex flex-col gap-1.5">
                    <div className="flex justify-between">
                        <span className="text-[10px] text-white/30 font-mono">FPS</span>
                        <span className="text-[10px] text-white/60 font-mono tabular-nums">
                            {gesture.fps}
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-[10px] text-white/30 font-mono">
                            Latency
                        </span>
                        <span className="text-[10px] text-white/60 font-mono tabular-nums">
                            {gesture.latency}ms
                        </span>
                    </div>
                </div>
            </div>

            <div className="border-t border-white/5" />

            {/* ── EVENTS ── */}
            <div className="flex-1 min-h-0">
                <SectionLabel>Events</SectionLabel>
                <div className="flex flex-col gap-1.5">
                    <AnimatePresence initial={false}>
                        {gesture.log.length === 0 ? (
                            <span className="text-[10px] text-white/15 font-mono">
                                no events yet
                            </span>
                        ) : (
                            gesture.log.slice(0, 12).map((entry, i) => (
                                <motion.div
                                    key={`${entry.event}-${entry.timestamp}`}
                                    initial={{ opacity: 0, x: 8 }}
                                    animate={{ opacity: 1 - i * 0.07, x: 0 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.15 }}
                                    className="flex items-center justify-between gap-2">
                                    <span className="text-[10px] font-mono text-white/25 tabular-nums shrink-0">
                                        {formatTime(entry.timestamp)}
                                    </span>
                                    <span className="text-[10px] font-mono text-white/60 truncate">
                                        {EVENT_LABELS[entry.event] ?? entry.event}
                                    </span>
                                </motion.div>
                            ))
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    )
}
