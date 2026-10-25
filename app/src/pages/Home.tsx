import { Settings2 } from "lucide-react";
import { Preview } from "../components/Preview";
import { Page } from "../components/ui/Page";
import { Switch } from "../components/ui/Switch";
import type { EngineState, LogEntry } from "../lib/useEngine";

interface Props {
  engine: EngineState;
  toast: LogEntry | null;
  videoOn: boolean;
  onOpenSettings: () => void;
}

export function Home({ engine, toast, videoOn, onOpenSettings }: Props) {
  const { connected, enabled, frame } = engine;
  const paused = frame?.paused;

  const title = !connected ? "Iniciando…" : !enabled ? "En pausa" : paused ? "Pausado con un gesto" : "Listo para tus gestos";
  const subtitle = !connected
    ? "Preparando la cámara y el reconocimiento."
    : !enabled
      ? "Los gestos están apagados. Actívalos cuando quieras."
      : paused
        ? "Cuatro dedos y puño otra vez para reanudar."
        : "Mueve la mano frente a la cámara para controlar tu PC.";

  return (
    <Page
      title={title}
      subtitle={subtitle}
      aside={
        <div className="flex items-center gap-3">
          <Switch
            size="lg"
            label="Activar gestos"
            on={enabled}
            disabled={!connected}
            onChange={(on) => engine.send({ cmd: "set_enabled", enabled: on })}
          />
          <button
            onClick={onOpenSettings}
            title="Ajustes"
            className="grid h-9 w-9 place-items-center rounded-full text-fg-muted transition-colors hover:bg-white/10 hover:text-fg"
          >
            <Settings2 size={18} strokeWidth={1.75} />
          </button>
        </div>
      }
    >
      <Preview frame={frame} connected={connected} toast={toast} preview={videoOn ? engine.preview : null} />
      <p className="mt-4 text-[12.5px] text-fg-faint">
        Consejo: con buena luz de frente el reconocimiento es más estable.
      </p>
    </Page>
  );
}
