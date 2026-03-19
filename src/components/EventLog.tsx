import { motion, AnimatePresence } from 'framer-motion'
import type { GestureEvent } from '../types/gesture'

interface LogEntry {
    event: GestureEvent
    timestamp: number
}

interface Props {
    log: LogEntry[]
}

function fmt(ts: number) {
    return new Date(ts * 1000).toLocaleTimeString('es-PE', { hour12: false })
}

export function EventLog({ log }: Props) {
    return (
        <div className="flex flex-col gap-2.5 flex-1 min-h-0">
            <span className="text-[9px] text-white tracking-widest uppercase">
                Event log
            </span>
            <div className="flex-1 bg-[#ffffff] border border-white/5 rounded-xl overflow-y-auto min-h-0">
                {log.length === 0 ? (
                    <div className="p-3 text-[9px] text-[#1a1a1a] tracking-widest font-mono">
                        no events yet
                    </div>
                ) : (
                    <AnimatePresence initial={false}>
                        {log.map((entry, i) => (
                            <motion.div
                                key={`${entry.timestamp}-${i}`}
                                initial={{ opacity: 0, y: -4 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.12 }}
                                className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 last:border-0">
                                <span className="text-[9px] text-white/20 font-mono shrink-0">
                                    {fmt(entry.timestamp)}
                                </span>
                                <span className="text-[9px] text-[#445ade] font-medium tracking-wide">
                                    {entry.event}
                                </span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                )}
            </div>
        </div>
    )
}
