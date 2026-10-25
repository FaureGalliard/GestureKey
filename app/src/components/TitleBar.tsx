import { getCurrentWindow } from "@tauri-apps/api/window";

interface Props {
  connected: boolean;
  version: string | null;
}

const WIN_BTN =
  "flex h-full items-center justify-center px-3.5 text-fg/50 transition-all hover:bg-white/10 hover:text-fg";

/** Teleprompter title bar: 32 px, drag region, quiet title, window controls. */
export function TitleBar({ connected, version }: Props) {
  const win = () => getCurrentWindow(); // lazy: throws outside Tauri (plain browser on :1420)
  return (
    <div data-tauri-drag-region className="flex h-8 shrink-0 select-none items-center justify-between bg-chrome pl-3">
      <div className="pointer-events-none flex items-center gap-2.5">
        <span className="text-[11px] font-medium text-fg/40">GestureKey</span>
        {version && <span className="font-mono text-[10px] text-fg-faint">v{version}</span>}
        <span className="flex items-center gap-1.5 text-[10px] text-fg-faint">
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-live" : "animate-pulse bg-fg-faint"}`} />
          {connected ? "motor" : "conectando…"}
        </span>
      </div>

      <div className="flex h-full items-center">
        <button className={WIN_BTN} title="Minimizar" onClick={() => win().minimize()}>
          <svg width="10" height="1" viewBox="0 0 10 1" fill="currentColor"><rect width="10" height="1" /></svg>
        </button>
        <button className={WIN_BTN} title="Maximizar" onClick={() => win().toggleMaximize()}>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1">
            <rect x="0.5" y="0.5" width="9" height="9" />
          </svg>
        </button>
        <button
          className={`${WIN_BTN} hover:bg-danger`}
          title="Cerrar (sigue en la bandeja)"
          onClick={() => win().close()}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
            <line x1="0" y1="0" x2="10" y2="10" />
            <line x1="10" y1="0" x2="0" y2="10" />
          </svg>
        </button>
      </div>
    </div>
  );
}
