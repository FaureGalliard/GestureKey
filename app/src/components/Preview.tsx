import { AnimatePresence, motion } from "framer-motion";
import { EVENT_LABELS, STATE_LABELS, type FrameMsg } from "../lib/protocol";
import type { LogEntry } from "../lib/useEngine";
import { HandCanvas } from "./HandCanvas";

interface Props {
  frame: FrameMsg | null;
  connected: boolean;
  preview?: string | null;   // camera video behind the skeleton
  toast?: LogEntry | null;   // last gesture, shown for a moment
}

/** The hand inside a quiet framed stage. */
export function Preview({ frame, connected, preview = null, toast = null }: Props) {
  const hasHand = !!frame?.hands.length;
  const state = frame?.state ?? "NO HANDS";

  return (
    <div className="relative aspect-[16/9] w-full overflow-hidden rounded-2xl border border-line bg-ink">
      <div
        className="pointer-events-none absolute inset-0 opacity-50"
        style={{
          backgroundImage: "radial-gradient(var(--color-line-strong) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      />
      <HandCanvas frame={frame} preview={preview} />

      {!hasHand && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <p className="text-[13px] text-fg-faint">
            {connected ? "Muestra una mano a la cámara" : "Sin imagen de la cámara"}
          </p>
        </div>
      )}

      {hasHand && (
        <div className="pointer-events-none absolute bottom-4 left-4 rounded-full bg-black/40 px-3 py-1.5 text-[12px] font-medium text-fg backdrop-blur-md">
          {frame?.owner === "GRAB_WINDOW" ? "Moviendo ventana" : STATE_LABELS[state] ?? state}
        </div>
      )}

      <div className="pointer-events-none absolute bottom-4 right-4">
        <AnimatePresence mode="popLayout">
          {toast && (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 10, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
              className="rounded-full bg-accent px-3.5 py-1.5 text-[12px] font-medium text-fg shadow-lg"
            >
              {EVENT_LABELS[toast.text] ?? toast.text}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
