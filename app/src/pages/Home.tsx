import { RefreshCw, Settings2, SunDim } from "lucide-react";
import { Preview } from "../components/Preview";
import { Page } from "../components/ui/Page";
import { Pill } from "../components/ui/Pill";
import { Switch } from "../components/ui/Switch";
import type { EngineState, LogEntry } from "../lib/useEngine";

interface Props {
  engine: EngineState;
  toast: LogEntry | null;
  videoOn: boolean;
  onOpenSettings: () => void;
}

/** What to tell the user, in plain words, given the engine and camera state. */
function headline(engine: EngineState): { title: string; subtitle: string; cameraProblem: boolean } {
  const { connected, enabled, cameraStatus: cam } = engine;
  if (!connected) return { title: "Iniciando…", subtitle: "Preparando la cámara y el reconocimiento.", cameraProblem: false };
  switch (cam?.status) {
    case "busy":
    case "missing":
      return { title: cam.status === "busy" ? "La cámara está ocupada" : "No encontramos la cámara",
               subtitle: cam.message, cameraProblem: true };
    case "opening":
      return { title: "Abriendo la cámara…", subtitle: "Un momento.", cameraProblem: false };
    case "reconnecting":
      return { title: "Reconectando la cámara…", subtitle: "Se perdió la imagen; volvemos enseguida.", cameraProblem: false };
  }
  if (!enabled) {
    return { title: "En pausa",
             subtitle: "Los gestos están apagados. Actívalos aquí o con dos palmas quietas frente a la cámara.",
             cameraProblem: false };
  }
  return { title: "Listo para tus gestos", subtitle: "Mueve la mano frente a la cámara para controlar tu PC.", cameraProblem: false };
}

export function Home({ engine, toast, videoOn, onOpenSettings }: Props) {
  const { connected, enabled, frame, cameraStatus } = engine;
  const { title, subtitle, cameraProblem } = headline(engine);

  return (
    <Page
      title={title}
      subtitle={subtitle}
      aside={
        // one 32 px row: switch + settings share height and weight
        <div className="flex h-8 items-center gap-2 rounded-full bg-white/[0.04] pl-1.5 pr-1">
          <span className="pl-1.5 text-[12px] font-medium text-fg-muted">{enabled ? "Activo" : "Apagado"}</span>
          <Switch
            size="lg"
            label="Activar gestos"
            on={enabled}
            disabled={!connected}
            onChange={(on) => engine.send({ cmd: "set_enabled", enabled: on })}
          />
          <span className="mx-0.5 h-4 w-px bg-white/10" />
          <button
            onClick={onOpenSettings}
            title="Ajustes"
            aria-label="Ajustes"
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
            Reintentar ahora
          </Pill>
          <span className="text-[12.5px] text-fg-faint">o elige otra en Ajustes › Cámara</span>
        </div>
      )}

      <Preview frame={frame} connected={connected && cameraStatus?.status === "ok"} toast={toast}
               preview={videoOn ? engine.preview : null} />

      {cameraStatus?.low_light ? (
        <p className="mt-4 flex items-center gap-2 text-[12.5px] text-warn">
          <SunDim size={14} strokeWidth={1.75} />
          Hay poca luz: la cámara va a {cameraStatus.measured_fps} fps. Con más luz de frente los gestos son más precisos.
        </p>
      ) : (
        <p className="mt-4 text-[12.5px] text-fg-faint">
          Consejo: con buena luz de frente el reconocimiento es más estable.
        </p>
      )}
    </Page>
  );
}
