import { EVENT_LABELS } from "../lib/protocol";
import type { LogEntry } from "../lib/useEngine";

const KIND_COLOR: Record<LogEntry["kind"], string> = {
  event: "text-white/85",
  info:  "text-white/40",
  warn:  "text-amber-300",
  error: "text-red-300",
};

export function EventLog({ log }: { log: LogEntry[] }) {
  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-white/5 bg-white/[0.03] p-4">
      <h2 className="text-xs uppercase tracking-wider text-white/40">Actividad</h2>
      <ul className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto font-mono text-xs">
        {log.length === 0 && <li className="text-white/25">Sin eventos todavía</li>}
        {log.map((e) => (
          <li key={e.id} className="flex gap-3">
            <span className="shrink-0 text-white/25">{new Date(e.t).toLocaleTimeString()}</span>
            <span className={KIND_COLOR[e.kind]}>{e.kind === "event" ? EVENT_LABELS[e.text] ?? e.text : e.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
