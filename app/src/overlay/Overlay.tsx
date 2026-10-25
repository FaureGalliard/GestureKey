import { invoke } from "@tauri-apps/api/core";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowUpDown, Camera, LayoutGrid, Maximize2, MonitorUp, Move, Pause, PanelLeft, PanelRight, Power, PowerOff,
  Volume2, VolumeX, X, ZoomIn,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { I18nProvider, initialLang, resolveLang, useT } from "../i18n";
import type { Dict } from "../i18n/en";
import type { ArmingInfo, FrameMsg } from "../lib/protocol";
import { useEngine } from "../lib/useEngine";

const TOAST_MS = 1400;
const EASE = [0.32, 0.72, 0, 1] as const;

/** Continuous gestures: shown for as long as they own the hand. */
const LIVE: Record<string, LucideIcon> = {
  SCROLL: ArrowUpDown, VOLUME: Volume2, ZOOM: ZoomIn, GRAB_WINDOW: Move,
};

/** One-shot gestures: a short toast. Continuous ones are covered by LIVE. */
const TOASTS: Record<string, LucideIcon> = {
  CLOSE_WINDOW: X, WINDOW_TO_MONITOR: MonitorUp, WINDOW_MAXIMIZED: Maximize2, SCREENSHOT: Camera,
  TASK_VIEW: LayoutGrid, MUTE_TOGGLE: VolumeX, MEDIA_PLAY_PAUSE: Pause, POWER_OFF: PowerOff, POWER_ON: Power,
};

type Item =
  | { kind: "ring"; key: string; arming: ArmingInfo }
  | { kind: "live"; key: string; icon: LucideIcon; label: string; level?: number }
  | { kind: "toast"; key: string; icon: LucideIcon; label: string };

/** While dragging a window: what letting go now would do (like Windows' snap preview). */
const ZONES: Record<string, LucideIcon> = { maximize: Maximize2, left: PanelLeft, right: PanelRight };

function pick(frame: FrameMsg | null, toast: Item | null, t: Dict): Item | null {
  if (frame?.arming) return { kind: "ring", key: "ring", arming: frame.arming };
  const zone = frame?.owner === "GRAB_WINDOW" ? frame.owner_info?.zone : undefined;
  if (zone) return { kind: "live", key: `zone-${zone}`, icon: ZONES[zone], label: t.overlay.zones[zone] };
  const live = frame?.owner ? LIVE[frame.owner] : undefined;
  if (live) {
    return { kind: "live", key: `live-${frame!.owner}`, icon: live, label: t.overlay.live[frame!.owner!] ?? frame!.owner!,
             level: frame!.owner_info?.volume };
  }
  return toast;
}

export function Overlay() {
  const engine = useEngine();
  const lang = engine.config ? resolveLang(engine.config.ui?.language) : initialLang();
  return (
    <I18nProvider lang={lang}>
      <OverlayView engine={engine} />
    </I18nProvider>
  );
}

function OverlayView({ engine }: { engine: ReturnType<typeof useEngine> }) {
  const t = useT();
  const [toast, setToast] = useState<Item | null>(null);

  // newest one-shot event → toast
  const newest = engine.log.find((e) => e.kind === "event" && TOASTS[e.text]);
  useEffect(() => {
    if (!newest) return;
    setToast({ kind: "toast", key: `toast-${newest.id}`, icon: TOASTS[newest.text],
               label: t.overlay.toasts[newest.text] ?? newest.text });
    const timer = window.setTimeout(() => setToast(null), TOAST_MS);
    return () => window.clearTimeout(timer);
  }, [newest?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const item = pick(engine.frame, toast, t);

  // move to the monitor under the cursor whenever something appears
  const visible = useRef(false);
  useEffect(() => {
    if (item && !visible.current) invoke("overlay_place").catch(() => {});
    visible.current = !!item;
  }, [item]);

  return (
    <div className="flex h-full items-start justify-center pt-2">
      <AnimatePresence mode="wait">
        {item && (
          <motion.div
            key={item.kind === "toast" ? item.key : item.kind === "live" ? item.key : "ring"}
            initial={{ opacity: 0, y: -14, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.26, ease: EASE }}
            className="flex items-center gap-3 rounded-full border border-white/10 bg-chrome/90 py-2 pl-2.5 pr-5 text-fg shadow-2xl backdrop-blur-xl"
          >
            {item.kind === "ring" ? <Ring info={item.arming} /> : <Badge icon={item.icon} />}
            <span className="text-[13.5px] font-medium tracking-[-0.005em]">
              {item.kind === "ring"
                ? item.arming.action === "off" ? t.overlay.holdOff : t.overlay.holdOn
                : item.label}
            </span>
            {item.kind === "live" && item.level !== undefined && <Level value={item.level} />}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Badge({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-full bg-accent">
      <Icon size={16} strokeWidth={2} />
    </span>
  );
}

/** Hold progress: the ring fills while the pose is held. */
function Ring({ info }: { info: ArmingInfo }) {
  const r = 14, c = 2 * Math.PI * r;
  const Icon = info.action === "off" ? PowerOff : Power;
  return (
    <span className="relative grid h-8 w-8 place-items-center">
      <svg viewBox="0 0 32 32" className="absolute inset-0 -rotate-90">
        <circle cx="16" cy="16" r={r} fill="none" stroke="var(--color-line-strong)" strokeWidth="2.5" />
        <circle
          cx="16" cy="16" r={r} fill="none" stroke="var(--color-accent-light)" strokeWidth="2.5"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - info.progress)}
          style={{ transition: "stroke-dashoffset 80ms linear" }}
        />
      </svg>
      <Icon size={13} strokeWidth={2} className="text-fg-muted" />
    </span>
  );
}

function Level({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="h-1 w-24 overflow-hidden rounded-full bg-white/10">
        <span className="block h-full rounded-full bg-accent-light transition-[width] duration-75"
              style={{ width: `${Math.round(value * 100)}%` }} />
      </span>
      <span className="w-8 text-right font-mono text-[11px] text-fg-muted">{Math.round(value * 100)}</span>
    </span>
  );
}
