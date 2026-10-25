import { useState } from "react";
import { CameraPicker } from "./components/CameraPicker";
import { EventLog } from "./components/EventLog";
import { GestureList } from "./components/GestureList";
import { HandCanvas } from "./components/HandCanvas";
import { StatePanel } from "./components/StatePanel";
import { useEngine } from "./lib/useEngine";

export default function App() {
  const engine = useEngine();
  const [preview, setPreview] = useState(false);

  const togglePreview = (on: boolean) => {
    setPreview(on);
    engine.send({ cmd: "preview", on });
  };

  return (
    <div className="flex h-screen flex-col gap-3 p-3">
      <header className="flex items-center gap-3 px-1">
        <h1 className="text-sm font-semibold tracking-wide">GestureKey</h1>
        <span className="text-xs text-white/30">{engine.version ? `v${engine.version}` : ""}</span>
        <span className={`ml-2 flex items-center gap-1.5 text-xs ${engine.connected ? "text-emerald-300" : "text-white/40"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${engine.connected ? "bg-emerald-400" : "bg-white/30 animate-pulse"}`} />
          {engine.connected ? "motor conectado" : "conectando al motor…"}
        </span>
        {engine.connected && engine.camera && (
          <span className="text-xs text-white/30">
            · {engine.camera.width}×{engine.camera.height} @ {Math.round(engine.camera.fps)} fps
          </span>
        )}
        <button
          className={`ml-auto rounded-full px-3 py-1 text-xs font-medium transition ${
            engine.enabled ? "bg-emerald-400/15 text-emerald-300" : "bg-white/5 text-white/50"
          }`}
          disabled={!engine.connected}
          onClick={() => engine.send({ cmd: "set_enabled", enabled: !engine.enabled })}
        >
          {engine.enabled ? "Gestos activos" : "Gestos apagados"}
        </button>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[1fr_300px] gap-3">
        <div className="grid min-h-0 grid-rows-[1fr_180px] gap-3">
          <HandCanvas frame={engine.frame} preview={preview ? engine.preview : null} />
          <EventLog log={engine.log} />
        </div>
        <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto">
          <StatePanel frame={engine.frame} />
          <CameraPicker config={engine.config} cameras={engine.cameras} preview={preview}
                        send={engine.send} onPreview={togglePreview} />
          <GestureList
            config={engine.config}
            onToggle={(key, enabled) => engine.send({ cmd: "set_config", patch: { gestures: { [key]: { enabled } } } })}
          />
        </aside>
      </main>
    </div>
  );
}
