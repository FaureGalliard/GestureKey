import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

export function LoadingScreen() {
    const [dots, setDots] = useState(0)

    useEffect(() => {
        const interval = setInterval(() => {
            setDots((d) => (d + 1) % 4)
        }, 500)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="w-screen h-screen bg-[#1a1a1a] flex flex-col items-center justify-center gap-8">
            <div className="flex flex-col items-center gap-3">
                <span className="text-[11px] font-inter text-white/20 tracking-[0.3em] uppercase">
                    Gesture Key
                </span>
                <span className="text-[11px] font-inter text-white/30 tracking-widest">
                    Iniciando modelo{'.'.repeat(dots)}
                    <span className="opacity-0">{'.'.repeat(3 - dots)}</span>
                </span>
            </div>

            {/* barra de carga */}
            <div className="w-48 h-px bg-white/10 relative overflow-hidden rounded-full">
                <motion.div
                    className="absolute inset-y-0 left-0 bg-[#445ade]"
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{
                        duration: 1.4,
                        repeat: Infinity,
                        ease: 'easeInOut',
                    }}
                    style={{ width: '50%' }}
                />
            </div>
        </div>
    )
}
