import { EVENT_LABELS, GESTURES, type CamerasMsg, type Command, type EngineConfig, type GestureKey } from "../lib/protocol";
import type { LogEntry } from "../lib/useEngine";
import { Menu } from "./ui/Menu";
import { SectionLabel } from "./ui/SectionLabel";
import { Switch } from "./ui/Switch";

const LOG_COLOR: Record<LogEntry["kind"], string> = {
  event: "text-fg",
  info:  "text-fg-faint",
  warn:  "text-warn",
  error: "text-danger",
};

interface Props {
  config: EngineConfig | null;
  cameras: CamerasMsg["devices"];
  log: LogEntry[];
  send: (cmd: Command) => void;
}

export function Sidebar({ config, cameras, log, send }: Props) {
  const device  = config?.camera.device ?? 0;
  const options = (cameras.length ? cameras : [{ index: device, name: `Cámara ${device}` }])
    .map((c) => ({ value: c.index, label: c.name }));
  const enabledCount = config
    ? (Object.keys(GESTURES) as GestureKey[]).filter((k) => config.gestures[k]?.enabled).length
    : 0;

  return (
    <aside className="flex w-[300px] shrink-0 flex-col border-l border-line bg-chrome">
      <SectionLabel>Cámara</SectionLabel>
      <div className="px-5 pb-5">
        <Menu
          value={device}
          options={options}
          disabled={!config}
          onOpen={() => send({ cmd: "list_cameras" })}
          onChange={(index) => send({ cmd: "set_config", patch: { camera: { device: index } } })}
          empty="Sin cámaras"
        />
      </div>

      <div className="border-t border-line" />
      <SectionLabel aside={config ? `${enabledCount}/${Object.keys(GESTURES).length}` : undefined}>
        Gestos
      </SectionLabel>
      <ul className="min-h-0 flex-1 overflow-y-auto">
        {(Object.keys(GESTURES) as GestureKey[]).map((key) => {
          const on = config?.gestures[key]?.enabled ?? false;
          return (
            <li key={key} className="flex items-center gap-3 border-b border-line px-5 py-2.5 last:border-b-0">
              <div className="min-w-0 flex-1">
                <div className={`text-[13px] font-medium ${on ? "text-fg" : "text-fg-muted"}`}>{GESTURES[key].label}</div>
                <div className="truncate text-[11px] text-fg-faint" title={GESTURES[key].hint}>{GESTURES[key].hint}</div>
              </div>
              <Switch
                on={on}
                disabled={!config}
                label={GESTURES[key].label}
                onChange={(enabled) => send({ cmd: "set_config", patch: { gestures: { [key]: { enabled } } } })}
              />
            </li>
          );
        })}
      </ul>

      <div className="border-t border-line" />
      <SectionLabel>Actividad</SectionLabel>
      <ul className="h-40 shrink-0 space-y-1 overflow-y-auto px-5 pb-4 font-mono text-[10.5px]">
        {log.length === 0 && <li className="text-fg-faint">Sin eventos todavía</li>}
        {log.map((e) => (
          <li key={e.id} className="flex gap-3">
            <span className="shrink-0 text-fg-faint">{new Date(e.t).toLocaleTimeString([], { hour12: false })}</span>
            <span className={`truncate ${LOG_COLOR[e.kind]}`} title={e.text}>
              {e.kind === "event" ? EVENT_LABELS[e.text] ?? e.text : e.text}
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
