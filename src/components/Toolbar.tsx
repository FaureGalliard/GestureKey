import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ToolbarProps {
    panelOpen: boolean
    onTogglePanel: () => void
    active: boolean
    onToggleActive: () => void
}

const ITEMS = [
    {
        id: 'gestures',
        label: 'Gestures',
        icon: (
            <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round">
                <path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2" />
                <path d="M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v2" />
                <path d="M10 10.5a2 2 0 0 0-2-2 2 2 0 0 0-2 2v1.5" />
                <path d="M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8 2 2 0 1 1 4 0" />
            </svg>
        ),
    },
    {
        id: 'console',
        label: 'Console',
        icon: (
            <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round">
                <polyline points="4 17 10 11 4 5" />
                <line
                    x1="12"
                    y1="19"
                    x2="20"
                    y2="19"
                />
            </svg>
        ),
    },
    {
        id: 'settings',
        label: 'Settings',
        icon: (
            <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round">
                <circle
                    cx="12"
                    cy="12"
                    r="3"
                />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
        ),
    },
]

export function Toolbar({
    panelOpen,
    onTogglePanel,
    active,
    onToggleActive,
}: ToolbarProps) {
    const [open, setOpen] = useState(false)

    const handleItem = (id: string) => {
        if (id === 'console') onTogglePanel()
    }

    const isActive = (id: string) => {
        if (id === 'console') return panelOpen
        return false
    }

    return (
        <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2">
            {/* main button */}
            <button
                onClick={() => setOpen((o) => !o)}
                className="w-9 h-9 flex items-center justify-center rounded-full bg-[#1a1a1a] text-white hover:bg-[#2a2a2a] transition-all duration-150 shadow-lg">
                <AnimatePresence
                    mode="wait"
                    initial={false}>
                    {open ? (
                        <motion.div
                            key="close"
                            initial={{ opacity: 0, scale: 0.7 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.7 }}
                            transition={{ duration: 0.12 }}>
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2.5"
                                strokeLinecap="round">
                                <line
                                    x1="4"
                                    y1="4"
                                    x2="20"
                                    y2="20"
                                />
                                <line
                                    x1="20"
                                    y1="4"
                                    x2="4"
                                    y2="20"
                                />
                            </svg>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="menu"
                            initial={{ opacity: 0, scale: 0.7 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.7 }}
                            transition={{ duration: 0.12 }}>
                            <svg
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round">
                                <line
                                    x1="4"
                                    y1="6"
                                    x2="20"
                                    y2="6"
                                />
                                <line
                                    x1="4"
                                    y1="12"
                                    x2="20"
                                    y2="12"
                                />
                                <line
                                    x1="4"
                                    y1="18"
                                    x2="20"
                                    y2="18"
                                />
                            </svg>
                        </motion.div>
                    )}
                </AnimatePresence>
            </button>

            {/* dropdown */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: -6, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -6, scale: 0.95 }}
                        transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }}
                        className="flex flex-col gap-1.5 items-end">
                        {ITEMS.map((item, i) => (
                            <motion.div
                                key={item.id}
                                initial={{ opacity: 0, y: -4 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -4 }}
                                transition={{ delay: i * 0.04, duration: 0.15 }}
                                className="group flex items-center gap-2">
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-100 text-[10px] font-medium text-white/40 tracking-wider pointer-events-none select-none">
                                    {item.label.toUpperCase()}
                                </span>
                                <button
                                    onClick={() => handleItem(item.id)}
                                    className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 shadow-md ${
                                        isActive(item.id)
                                            ? 'bg-white text-[#111]'
                                            : 'bg-[#1a1a1a] text-white/70 hover:text-white hover:bg-[#2a2a2a]'
                                    }`}>
                                    {item.icon}
                                </button>
                            </motion.div>
                        ))}

                        <div className="w-px h-3 bg-white/10" />

                        {/* pause/resume */}
                        <motion.div
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -4 }}
                            transition={{ delay: ITEMS.length * 0.04, duration: 0.15 }}
                            className="group flex items-center gap-2">
                            <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-100 text-[10px] font-medium text-white/40 tracking-wider pointer-events-none select-none">
                                {active ? 'PAUSE' : 'RESUME'}
                            </span>
                            <button
                                onClick={onToggleActive}
                                className={`w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 shadow-md ${
                                    !active
                                        ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                                        : 'bg-[#1a1a1a] text-white/70 hover:text-white hover:bg-[#2a2a2a]'
                                }`}>
                                {active ? (
                                    <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="currentColor">
                                        <rect
                                            x="6"
                                            y="4"
                                            width="4"
                                            height="16"
                                            rx="1"
                                        />
                                        <rect
                                            x="14"
                                            y="4"
                                            width="4"
                                            height="16"
                                            rx="1"
                                        />
                                    </svg>
                                ) : (
                                    <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 24"
                                        fill="currentColor">
                                        <polygon points="5,3 19,12 5,21" />
                                    </svg>
                                )}
                            </button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
