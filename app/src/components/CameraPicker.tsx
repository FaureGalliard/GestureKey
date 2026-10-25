import type { CamerasMsg, Command, EngineConfig } from "../lib/protocol";

interface Props {
  config: EngineConfig | null;
  cameras: CamerasMsg["devices"];
  preview: boolean;
  send: (cmd: Command) => void;
  onPreview: (on: boolean) => void;
}

export function CameraPicker({ config, cameras, preview, send, onPreview }: Props) {
  const device = config?.camera.device ?? 0;
  const options = cameras.length ? cameras : [{ index: device, name: `Cámara ${device}` }];

  return (
    <section className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
      <h2 className="text-xs uppercase tracking-wider text-white/40">Cámara</h2>
      <div className="mt-3 flex gap-2">
        <select
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 text-sm"
          value={device}
          disabled={!config}
          onChange={(e) => send({ cmd: "set_config", patch: { camera: { device: Number(e.target.value) } } })}
        >
          {options.map((c) => <option key={c.index} value={c.index}>{c.name}</option>)}
        </select>
        <button
          className="rounded-lg border border-white/10 px-3 text-sm text-white/70 hover:bg-white/5"
          disabled={!config}
          onClick={() => send({ cmd: "list_cameras" })}
          title="Buscar cámaras"
        >
          ↻
        </button>
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm text-white/60">
        <input type="checkbox" className="accent-emerald-400" checked={preview}
               onChange={(e) => onPreview(e.target.checked)} />
        Mostrar video de fondo
      </label>
    </section>
  );
}
