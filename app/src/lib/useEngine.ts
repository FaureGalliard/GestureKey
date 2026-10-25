import { useCallback, useEffect, useRef, useState } from "react";
import {
  ENGINE_URL, type CameraMsg, type CameraStatusMsg, type CamerasMsg, type Command, type EngineConfig, type EngineMsg, type FrameMsg,
} from "./protocol";

export interface LogEntry { id: number; t: number; kind: "event" | "info" | "warn" | "error"; text: string }

export interface EngineState {
  connected: boolean;
  version: string | null;
  config: EngineConfig | null;
  enabled: boolean;
  frame: FrameMsg | null;
  camera: CameraMsg | null;
  cameraStatus: CameraStatusMsg | null;
  preview: string | null;
  cameras: CamerasMsg["devices"];
  log: LogEntry[];
  send: (cmd: Command) => void;
}

const MAX_LOG = 80;
const RETRY_MS = 1000;

/** One WebSocket to the engine, reconnecting forever. */
export function useEngine(): EngineState {
  const [connected, setConnected] = useState(false);
  const [version, setVersion]     = useState<string | null>(null);
  const [config, setConfig]       = useState<EngineConfig | null>(null);
  const [enabled, setEnabled]     = useState(true);
  const [frame, setFrame]         = useState<FrameMsg | null>(null);
  const [camera, setCamera]       = useState<CameraMsg | null>(null);
  const [cameraStatus, setCameraStatus] = useState<CameraStatusMsg | null>(null);
  const [preview, setPreview]     = useState<string | null>(null);
  const [cameras, setCameras]     = useState<CamerasMsg["devices"]>([]);
  const [log, setLog]             = useState<LogEntry[]>([]);
  const wsRef  = useRef<WebSocket | null>(null);
  const nextId = useRef(0);

  const push = useCallback((kind: LogEntry["kind"], text: string) => {
    const entry = { id: nextId.current++, t: Date.now(), kind, text };
    setLog((prev) => [entry, ...prev].slice(0, MAX_LOG));
  }, []);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    let pendingFrame: FrameMsg | null = null;
    let raf = 0;

    const connect = () => {
      const ws = new WebSocket(ENGINE_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!disposed) timer = window.setTimeout(connect, RETRY_MS);
      };
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as EngineMsg;
        switch (msg.type) {
          case "hello":
            setVersion(msg.version);
            setConfig(msg.config);
            setEnabled(msg.enabled);
            setCamera(msg.camera);
            setCameraStatus(msg.camera_status);
            break;
          case "frame":
            // frames can arrive at 60 Hz: render at most once per animation frame
            pendingFrame = msg;
            if (!raf) raf = requestAnimationFrame(() => { raf = 0; setFrame(pendingFrame); });
            break;
          case "event":   push("event", msg.event); break;
          case "status":  push(msg.level, msg.message); break;
          case "preview": setPreview(msg.jpeg); break;
          case "config":  setConfig(msg.config); break;
          case "enabled": setEnabled(msg.enabled); break;
          case "cameras": setCameras(msg.devices); break;
          case "camera_status": setCameraStatus(msg); break;
          case "camera":
            setCamera(msg);
            push("info", `Camera ${msg.device}: ${msg.width}×${msg.height} @ ${Math.round(msg.fps)} fps`);
            break;
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      cancelAnimationFrame(raf);
      wsRef.current?.close();
    };
  }, [push]);

  const send = useCallback((cmd: Command) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(cmd));
  }, []);

  return { connected, version, config, enabled, frame, camera, cameraStatus, preview, cameras, log, send };
}
