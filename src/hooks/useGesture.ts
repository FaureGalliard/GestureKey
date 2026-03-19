import { useState, useEffect, useRef, useCallback } from 'react'
import type { GestureMessage, HandState, GestureEvent } from '../types/gesture'

const WS_URL = 'ws://localhost:8765'
const MAX_LOG = 50

export interface GestureState {
    connected: boolean
    state: HandState
    rawState: HandState
    confidence: number
    buffer: HandState[]
    log: { event: GestureEvent; timestamp: number }[]
    frameSrc: string | null
}

export function useGesture() {
    const [data, setData] = useState<GestureState>({
        connected: false,
        state: 'NO HANDS',
        rawState: 'NO HANDS',
        confidence: 0,
        buffer: [],
        log: [],
        frameSrc: null,
    })

    const ws = useRef<WebSocket | null>(null)
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

    const connect = useCallback(() => {
        if (ws.current?.readyState === WebSocket.OPEN) return

        ws.current = new WebSocket(WS_URL)

        ws.current.onopen = () => setData((d) => ({ ...d, connected: true }))

        ws.current.onclose = () => {
            setData((d) => ({ ...d, connected: false, frameSrc: null }))
            reconnectTimer.current = setTimeout(connect, 2000)
        }

        ws.current.onerror = () => ws.current?.close()

        ws.current.onmessage = (e) => {
            const msg = JSON.parse(e.data)

            // frame stream
            if (msg.type === 'frame') {
                setData((d) => ({
                    ...d,
                    frameSrc: `data:image/jpeg;base64,${msg.data}`,
                }))
                return
            }

            // estado + evento
            const gesture = msg as GestureMessage
            setData((d) => ({
                ...d,
                state: gesture.state,
                rawState: gesture.raw_state,
                confidence: gesture.confidence,
                buffer: [...d.buffer.slice(-5), gesture.state],
                log: gesture.event
                    ? [
                          { event: gesture.event, timestamp: gesture.timestamp },
                          ...d.log,
                      ].slice(0, MAX_LOG)
                    : d.log,
            }))
        }
    }, [])

    useEffect(() => {
        connect()
        return () => {
            reconnectTimer.current && clearTimeout(reconnectTimer.current)
            ws.current?.close()
        }
    }, [connect])

    return data
}
