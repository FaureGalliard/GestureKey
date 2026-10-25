import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Stage } from "./components/Stage";
import { TitleBar } from "./components/TitleBar";
import type { LogEntry } from "./lib/useEngine";
import { useEngine } from "./lib/useEngine";

const TOAST_MS = 1400;

export default function App() {
  const engine = useEngine();
  const [videoOn, setVideoOn] = useState(false);
  const [toast, setToast] = useState<LogEntry | null>(null);

  // newest gesture event → toast for a moment
  const newest = engine.log.find((e) => e.kind === "event") ?? null;
  useEffect(() => {
    if (!newest) return;
    setToast(newest);
    const timer = window.setTimeout(() => setToast(null), TOAST_MS);
    return () => window.clearTimeout(timer);
  }, [newest?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleVideo = () => {
    engine.send({ cmd: "preview", on: !videoOn });
    setVideoOn(!videoOn);
  };

  return (
    // 1 px accent outline around the window: the teleprompter's signature frame
    <div className="flex h-full flex-col outline outline-1 -outline-offset-1 outline-accent/40">
      <TitleBar connected={engine.connected} version={engine.version} />
      <main className="flex min-h-0 flex-1">
        <Stage
          connected={engine.connected}
          enabled={engine.enabled}
          frame={engine.frame}
          camera={engine.camera}
          preview={engine.preview}
          videoOn={videoOn}
          lastEvent={toast}
          onToggleEnabled={() => engine.send({ cmd: "set_enabled", enabled: !engine.enabled })}
          onToggleVideo={toggleVideo}
        />
        <Sidebar config={engine.config} cameras={engine.cameras} log={engine.log} send={engine.send} />
      </main>
    </div>
  );
}
