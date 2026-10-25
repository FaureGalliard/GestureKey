import type { FrameMsg } from "../lib/protocol";

const STATE_COLORS: Record<string, string> = {
  PALM: "#34d399",
  FIST: "#f87171",
  PINCH: "#60a5fa",
  TWO_FINGERS: "#fbbf24",
  THREE_FINGERS: "#a78bfa",
  FOUR_FINGERS: "#f472b6",
};

export function StatePanel({ frame }: { frame: FrameMsg | null }) {
  const state = frame?.state ?? "NO HANDS";
  const color = STATE_COLORS[state] ?? "rgba(255,255,255,0.35)";
  const conf  = Math.round((frame?.confidence ?? 0) * 100);

  return (
    <section className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-xs uppercase tracking-wider text-white/40">Estado</span>
        <span className="font-mono text-xs text-white/40">{frame ? `${frame.fps.toFixed(0)} fps` : "—"}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold" style={{ color }}>{state.replace("_", " ")}</div>
      <div className="mt-1 text-xs text-white/40">
        crudo: {frame?.raw_state ?? "—"} · {conf}%
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded bg-white/5">
        <div className="h-full transition-[width] duration-100" style={{ width: `${conf}%`, background: color }} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {frame?.owner && (
          <span className="rounded bg-red-400/15 px-2 py-0.5 text-red-300">activo: {frame.owner}</span>
        )}
        {frame?.paused && <span className="rounded bg-amber-400/15 px-2 py-0.5 text-amber-300">pausado</span>}
      </div>
    </section>
  );
}
