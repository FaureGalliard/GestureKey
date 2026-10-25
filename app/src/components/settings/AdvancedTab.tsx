import type { ReactNode } from "react";
import { EVENT_LABELS, STATE_LABELS } from "../../lib/protocol";
import type { EngineState, LogEntry } from "../../lib/useEngine";
import { Row, Section } from "../ui/Page";

const LOG_COLOR: Record<LogEntry["kind"], string> = {
  event: "text-fg",
  info:  "text-fg-faint",
  warn:  "text-warn",
  error: "text-danger",
};

const Value = ({ children }: { children: ReactNode }) => (
  <span className="font-mono text-[12px] text-fg-muted">{children}</span>
);

export function AdvancedTab({ engine }: { engine: EngineState }) {
  const { frame, camera, version, log, connected } = engine;
  const conf = Math.round((frame?.confidence ?? 0) * 100);

  return (
    <>
      <Section title="Diagnóstico">
        <Row title="Motor"><Value>{connected ? `v${version ?? "?"}` : "sin conexión"}</Value></Row>
        <Row title="Cámara">
          <Value>{camera ? `${camera.width}×${camera.height} · ${Math.round(camera.fps)} fps` : "—"}</Value>
        </Row>
        <Row title="Procesando"><Value>{frame ? `${frame.fps.toFixed(0)} fps` : "—"}</Value></Row>
        <Row title="Detectado" hint="Antes de estabilizar.">
          <Value>{frame ? `${STATE_LABELS[frame.raw_state] ?? frame.raw_state} · ${conf}%` : "—"}</Value>
        </Row>
        <Row title="Gesto en curso"><Value>{frame?.owner?.toLowerCase() ?? "ninguno"}</Value></Row>
      </Section>

      <Section title="Actividad">
        <ul className="space-y-1 py-3 font-mono text-[11.5px]">
          {log.length === 0 && <li className="text-fg-faint">Sin eventos todavía</li>}
          {log.map((e) => (
            <li key={e.id} className="flex gap-4">
              <span className="shrink-0 text-fg-faint">{new Date(e.t).toLocaleTimeString([], { hour12: false })}</span>
              <span className={`truncate ${LOG_COLOR[e.kind]}`} title={e.text}>
                {e.kind === "event" ? EVENT_LABELS[e.text] ?? e.text : e.text}
              </span>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
