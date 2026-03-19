import { motion } from 'framer-motion'
import type { HandState } from '../types/gesture'

interface Props {
    state: HandState
    rawState: HandState
    confidence: number
}

export function GestureCard({ state, rawState, confidence }: Props) {
    const isActive = state !== 'NO HANDS' && state !== 'UNKNOWN'
    const pct = Math.round(confidence * 100)

    return (
        <div className="flex flex-col gap-2.5">
            <span className="text-[9px] text-white tracking-widest uppercase">State</span>

            <div className="bg-[#1a1a1a] border border-white/10 rounded-xl px-3 py-2.5 flex items-center justify-between">
                <span
                    className={`text-[12px] font-medium tracking-wide ${isActive ? 'text-white' : 'text-white/25'}`}>
                    {state}
                </span>
                <motion.span
                    animate={{
                        backgroundColor: isActive ? '#445ade' : 'rgba(255,255,255,0.08)',
                    }}
                    transition={{ duration: 0.2 }}
                    className="w-2 h-2 rounded-full shrink-0"
                />
            </div>

            <div className="flex flex-col gap-1.5">
                <div className="h-[3px] bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.15 }}
                        className="h-full bg-[#445ade] rounded-full"
                    />
                </div>
                <span className="text-[9px] text-white/20 font-mono">
                    raw: {rawState} — {pct}%
                </span>
            </div>
        </div>
    )
}
