import { useCallback, useEffect, useState } from "react";
import { SettingsPanel, type SettingsTab } from "./components/settings/SettingsPanel";
import type { LogEntry } from "./lib/useEngine";
import { useEngine } from "./lib/useEngine";
import { Home } from "./pages/Home";

const TOAST_MS = 1400;

export default function App() {
  const engine = useEngine();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [tab, setTab] = useState<SettingsTab>("gestures");
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

  // the camera video only streams while it is shown
  const { connected, send } = engine;
  useEffect(() => {
    if (connected) send({ cmd: "preview", on: videoOn });
  }, [videoOn, connected, send]);

  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  return (
    <div className="h-full overflow-y-auto">
      <Home engine={engine} toast={toast} videoOn={videoOn} onOpenSettings={() => setSettingsOpen(true)} />
      <SettingsPanel
        open={settingsOpen}
        tab={tab}
        onTab={setTab}
        onClose={closeSettings}
        engine={engine}
        videoOn={videoOn}
        onVideo={setVideoOn}
      />
    </div>
  );
}
