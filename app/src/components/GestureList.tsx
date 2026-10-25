import { GESTURES, type EngineConfig, type GestureKey } from "../lib/protocol";

interface Props {
  config: EngineConfig | null;
  onToggle: (key: GestureKey, enabled: boolean) => void;
}

export function GestureList({ config, onToggle }: Props) {
  return (
    <section className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
      <h2 className="text-xs uppercase tracking-wider text-white/40">Gestos</h2>
      <ul className="mt-3 space-y-1">
        {(Object.keys(GESTURES) as GestureKey[]).map((key) => {
          const on = config?.gestures[key]?.enabled ?? false;
          return (
            <li key={key}>
              <label className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-white/[0.04]">
                <input
                  type="checkbox"
                  className="accent-emerald-400"
                  checked={on}
                  disabled={!config}
                  onChange={(e) => onToggle(key, e.target.checked)}
                />
                <span className="flex-1">
                  <span className="block text-sm text-white/85">{GESTURES[key].label}</span>
                  <span className="block text-xs text-white/35">{GESTURES[key].hint}</span>
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
