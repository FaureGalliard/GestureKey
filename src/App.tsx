import './globals.css'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGesture } from './hooks/useGesture'
import { GestureCard } from './components/GestureCard'
import { StateBuffer } from './components/StateBuffer'
import { EventLog } from './components/EventLog'
import { LoadingScreen } from './components/LoadingScreen'

const btn = `flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-full transition-all duration-150`

export default function App() {
    const [panelOpen, setPanelOpen] = useState(false)
    const gesture = useGesture()

    if (!gesture.connected) {
        return <LoadingScreen />
    }

    return (
        <div className="w-screen h-screen bg-[#1a1a1a] flex flex-col font-inter overflow-hidden">
            {/* toolbar */}
            <div className="flex items-center gap-2 px-5 py-3 bg-[#1a1a1a] border-b border-white/10 shrink-0">
                <button
                    onClick={() => setPanelOpen((p) => !p)}
                    className={`${btn} bg-white/10 text-white hover:bg-white/20`}>
                    {panelOpen ? '✕ PANEL' : '≡ PANEL'}
                </button>

                <div className="w-px h-5 mx-1 bg-white/15" />

                {/* active gesture pill */}
                <AnimatePresence mode="wait">
                    {gesture.state !== 'NO HANDS' && gesture.state !== 'UNKNOWN' ? (
                        <motion.div
                            key={gesture.state}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ duration: 0.12 }}
                            className="flex items-center gap-2 bg-[#445ade] rounded-full px-3 py-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-white/60 shrink-0" />
                            <span className="text-[11px] font-medium text-white tracking-wide">
                                {gesture.state}
                            </span>
                            <span className="text-[10px] text-white/60">
                                {(gesture.confidence * 100).toFixed(1)}%
                            </span>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="no-hands"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.12 }}
                            className="flex items-center gap-2 bg-white/5 rounded-full px-3 py-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-white/10 shrink-0" />
                            <span className="text-[11px] font-medium text-white/20">
                                {gesture.state}
                            </span>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="flex-1" />

                <span className="text-[10px] text-white/20 font-mono">v2.0.0</span>
            </div>

            {/* main */}
            <div className="flex flex-1 overflow-hidden">
                {/* side panel */}
                <AnimatePresence>
                    {panelOpen && (
                        <motion.div
                            initial={{ width: 0, opacity: 0 }}
                            animate={{ width: 240, opacity: 1 }}
                            exit={{ width: 0, opacity: 0 }}
                            transition={{ duration: 0.25, ease: [0.32, 0.72, 0, 1] }}
                            className="bg-[#111] border-r border-white/10 overflow-hidden shrink-0 flex flex-col">
                            <div className="w-[240px] h-full flex flex-col gap-4 p-4 overflow-y-auto">
                                <GestureCard
                                    state={gesture.state}
                                    rawState={gesture.rawState}
                                    confidence={gesture.confidence}
                                />
                                <div className="border-t border-white/5" />
                                <StateBuffer buffer={gesture.buffer} />
                                <div className="border-t border-white/5" />
                                <EventLog log={gesture.log} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* camera */}
                <div className="flex-1 bg-[#0d0d0d] relative overflow-hidden flex items-center justify-center">
                    {gesture.frameSrc ? (
                        <img
                            src={gesture.frameSrc}
                            alt="camera"
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <span className="text-[11px] text-white/10 tracking-widest font-mono">
                            CAMERA FEED
                        </span>
                    )}
                </div>
            </div>
        </div>
    )
}
