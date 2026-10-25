import { AnimatePresence, motion } from "framer-motion";
import { EVENT_LABELS, type CameraMsg, type FrameMsg } from "../lib/protocol";
import type { LogEntry } from "../lib/useEngine";
import { HandCanvas } from "./HandCanvas";
import { Pill, PillDivider } from "./ui/Pill";

const OWNER_LABELS: Record<string, string> = {
  GRAB_WINDOW: "Moviendo ventana",
  SCROLL: "Scroll",
  VOLUME: "Volumen",
  ZOOM: "Zoom",
};

interface Props {
  connected: boolean;
  enabled: boolean;
  frame: FrameMsg | null;
  camera: CameraMsg | null;
  preview: string | null;
  videoOn: boolean;
  lastEvent: LogEntry | null;
  onToggleEnabled: () => void;
  onToggleVideo: () => void;
}

export function Stage({
  connected, enabled, frame, camera, preview, videoOn, lastEvent, onToggleEnabled, onToggleVideo,
}: Props) {
  const state = frame?.state ?? "NO HANDS";
  const conf  = Math.round((frame?.confidence ?? 0) * 100);
  const hasHand = !!frame?.hands.length;

  return (
    <section className="relative min-w-0 flex-1 overflow-hidden bg-ink">
      {/* dot grid: the stage reads as a surface, not a void */}
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          backgroundImage: "radial-gradient(var(--color-line-strong) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />
      <HandCanvas frame={frame} preview={videoOn ? preview : null} />

      {/* toolbar */}
      <div className="absolute left-5 right-5 top-4 flex items-center gap-2">
        <Pill variant={enabled ? "primary" : "ghost"} disabled={!connected} onClick={onToggleEnabled}>
          <span className={`h-1.5 w-1.5 rounded-full ${enabled ? "bg-fg" : "bg-fg-faint"}`} />
          {enabled ? "Activo" : "Apagado"}
        </Pill>
        <Pill variant={videoOn ? "inverted" : "ghost"} disabled={!connected} onClick={onToggleVideo}>
          Video
        </Pill>
        {camera && connected && (
          <>
            <PillDivider />
            <span className="font-mono text-[10px] text-fg-faint">
              {camera.width}×{camera.height} · {frame ? frame.fps.toFixed(0) : "—"} fps
            </span>
          </>
        )}
        <div className="flex-1" />
        <AnimatePresence>
          {frame?.owner && (
            <motion.span
              key="owner"
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
              className="rounded-full bg-hold/15 px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-hold"
            >
              {OWNER_LABELS[frame.owner] ?? frame.owner}
            </motion.span>
          )}
          {frame?.paused && (
            <motion.span
              key="paused"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="rounded-full bg-warn/15 px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-warn"
            >
              Pausado
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* empty / connecting */}
      {!hasHand && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <p className="text-[13px] text-fg-faint">
            {connected ? "Muestra una mano a la cámara" : "Conectando al motor…"}
          </p>
        </div>
      )}

      {/* state readout: display type, website scale */}
      <div className="pointer-events-none absolute bottom-5 left-5">
        <div className="text-[40px] font-medium leading-none tracking-tight text-fg">
          {state.replace("_", " ").toLowerCase()}
        </div>
        <div className="mt-3 flex items-center gap-3">
          <div className="h-px w-32 bg-line-strong">
            <div className="h-px bg-accent-light transition-[width] duration-100" style={{ width: `${conf}%` }} />
          </div>
          <span className="font-mono text-[10px] text-fg-faint">
            {frame?.raw_state.toLowerCase() ?? "—"} · {conf}%
          </span>
        </div>
      </div>

      {/* last gesture */}
      <div className="pointer-events-none absolute bottom-5 right-5">
        <AnimatePresence mode="popLayout">
          {lastEvent && (
            <motion.div
              key={lastEvent.id}
              initial={{ opacity: 0, y: 10, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
              className="rounded-full bg-accent px-4 py-2 text-[11px] font-medium uppercase tracking-[0.04em] text-fg shadow-lg"
            >
              {EVENT_LABELS[lastEvent.text] ?? lastEvent.text}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
