import { AnimatePresence, motion } from "framer-motion";
import { Activity, Camera, Hand, Languages, X, type LucideIcon } from "lucide-react";
import { useEffect } from "react";
import { useT } from "../../i18n";
import type { EngineState } from "../../lib/useEngine";
import { AdvancedTab } from "./AdvancedTab";
import { CameraTab } from "./CameraTab";
import { GeneralTab } from "./GeneralTab";
import { GesturesTab } from "./GesturesTab";

export type SettingsTab = "general" | "gestures" | "camera" | "advanced";

const TABS: { key: SettingsTab; icon: LucideIcon }[] = [
  { key: "general", icon: Languages },
  { key: "gestures", icon: Hand },
  { key: "camera", icon: Camera },
  { key: "advanced", icon: Activity },
];

interface Props {
  open: boolean;
  tab: SettingsTab;
  onTab: (tab: SettingsTab) => void;
  onClose: () => void;
  engine: EngineState;
  videoOn: boolean;
  onVideo: (on: boolean) => void;
}

const EASE = [0.32, 0.72, 0, 1] as const;

/** Settings slide over the home screen from the right; click outside or Esc to close. */
export function SettingsPanel({ open, tab, onTab, onClose, engine, videoOn, onVideo }: Props) {
  const t = useT().settings;
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed bottom-0 right-0 top-0 z-50 flex w-[400px] max-w-[92vw] flex-col border-l border-line bg-chrome shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.36, ease: EASE }}
          >
            <header className="flex items-center justify-between px-6 pb-4 pt-5">
              <h2 className="text-[18px] font-semibold tracking-[-0.01em]">{t.title}</h2>
              <button
                onClick={onClose}
                title={t.close}
                className="grid h-8 w-8 place-items-center rounded-full text-fg-muted transition-colors hover:bg-white/10 hover:text-fg"
              >
                <X size={16} strokeWidth={1.75} />
              </button>
            </header>

            {/* segmented control */}
            <div className="mx-6 mb-2 flex rounded-full bg-white/[0.06] p-1">
              {TABS.map(({ key, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => onTab(key)}
                  className="relative flex flex-1 items-center justify-center gap-1.5 rounded-full py-1.5 text-[12.5px] font-medium"
                >
                  {tab === key && (
                    <motion.span
                      layoutId="settings-tab"
                      className="absolute inset-0 rounded-full bg-chrome-raised shadow-sm"
                      transition={{ duration: 0.28, ease: EASE }}
                    />
                  )}
                  <span className={`relative flex items-center gap-1.5 ${tab === key ? "text-fg" : "text-fg-muted"}`}>
                    <Icon size={14} strokeWidth={1.75} />
                    {t.tabs[key]}
                  </span>
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-8 pt-4">
              {tab === "general" && <GeneralTab engine={engine} />}
              {tab === "gestures" && <GesturesTab engine={engine} />}
              {tab === "camera" && <CameraTab engine={engine} videoOn={videoOn} onVideo={onVideo} />}
              {tab === "advanced" && <AdvancedTab engine={engine} />}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
