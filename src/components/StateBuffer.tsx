import { motion } from 'framer-motion'
import type { HandState } from '../types/gesture'

const ABBR: Record<HandState, string> = {
    PALM: 'PAL',
    FIST: 'FST',
    PINCH: 'PCH',
    TWO_FINGERS: 'TWO',
    THREE_FINGERS: 'THR',
    FOUR_FINGERS: 'FOR',
    UNKNOWN: 'UNK',
    'NO HANDS': '···',
}

interface Props {
    buffer: HandState[]
    size?: number
}

export function StateBuffer({ buffer, size = 6 }: Props) {
    const cells = Array.from({ length: size }, (_, i) => buffer[i] ?? null)

    return (
        <div className="flex flex-col gap-2.5">
            <span className="text-[9px] text-white tracking-widest uppercase">
                Buffer
            </span>
            <div className="flex gap-1.5">
                {cells.map((s, i) => (
                    <motion.div
                        key={i}
                        animate={{
                            borderColor: s
                                ? 'rgba(68,90,222,0.5)'
                                : 'rgba(255,255,255,0.06)',
                            color: s ? '#445ade' : 'rgba(255,255,255,0.15)',
                        }}
                        transition={{ duration: 0.15 }}
                        className="flex-1 rounded-lg py-1.5 text-center text-[8px] font-medium tracking-wide border bg-[#1a1a1a]">
                        {s ? ABBR[s] : '···'}
                    </motion.div>
                ))}
            </div>
        </div>
    )
}
