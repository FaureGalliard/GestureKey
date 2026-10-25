import { RefreshCw, Settings2, SunDim } from "lucide-react";
import { Preview } from "../components/Preview";
import { Page } from "../components/ui/Page";
import { Pill } from "../components/ui/Pill";
import { Switch } from "../components/ui/Switch";
import { useT } from "../i18n";
import type { Dict } from "../i18n/en";
import type { EngineState, LogEntry } from "../lib/useEngine";

interface Props {
  engine: EngineState;
  toast: LogEntry | null;
  videoOn: boolean;
  onOpenSettings: () => void;
}

/** What to tell the user, in plain words, given the engine and camera state. */
function headline(engine: EngineState, t: Dict["home"]): { title: string; subtitle: string; cameraProblem: boolean } {
  const { connected, enabled, cameraStatus: cam } = engine;
  if (!connected) return { ...t.starting, cameraProblem: false };
  switch (cam?.status) {
    case "busy":
    case "missing":
      return { ...t[cam.status], cameraProblem: true };
    case "opening":
    case "reconnecting":
      return { ...t[cam.status], cameraProblem: false };
  }
  return { ...(enabled ? t.ready : t.paused), cameraProblem: false };
}

export function Home({ engine, toast, videoOn, onOpenSettings }: Props) {
  const t = useT().home;
  const { connected, enabled, frame, cameraStatus } = engine;
  const { title, subtitle, cameraProblem } = headline(engine, t);

  return (
    <Page
      title={title}
      subtitle={subtitle}
      aside={
        // one 32 px row: switch + settings share height and weight
        <div className="flex h-8 items-center gap-2 rounded-full bg-white/[0.04] pl-1.5 pr-1">
          <span className="pl-1.5 text-[12px] font-medium text-fg-muted">{enabled ? t.on : t.off}</span>
          <Switch
            size="lg"
            label={t.toggle}
            on={enabled}
            disabled={!connected}
            onChange={(on) => engine.send({ cmd: "set_enabled", enabled: on })}
          />
          <span className="mx-0.5 h-4 w-px bg-white/10" />
          <button
            onClick={onOpenSettings}
            title={t.settings}
            aria-label={t.settings}
            className="grid h-6 w-6 place-items-center rounded-full text-fg-muted transition-colors hover:bg-white/10 hover:text-fg"
          >
            <Settings2 size={15} strokeWidth={1.75} />
          </button>
        </div>
      }
    >
      {cameraProblem && (
        <div className="mb-5 flex items-center gap-3">
          <Pill variant="primary" onClick={() => engine.send({ cmd: "reconnect_camera" })}>
            <RefreshCw size={12} strokeWidth={2} />
            {t.retry}
          </Pill>
          <span className="text-[12.5px] text-fg-faint">{t.retryAlt}</span>
        </div>
      )}

      <Preview frame={frame} connected={connected && cameraStatus?.status === "ok"} toast={toast}
               preview={videoOn ? engine.preview : null} />

      {cameraStatus?.low_light ? (
        <p className="mt-4 flex items-center gap-2 text-[12.5px] text-warn">
          <SunDim size={14} strokeWidth={1.75} />
          {t.lowLight(cameraStatus.measured_fps ?? 0)}
        </p>
      ) : (
        <p className="mt-4 text-[12.5px] text-fg-faint">{t.tip}</p>
      )}
    </Page>
  );
}
