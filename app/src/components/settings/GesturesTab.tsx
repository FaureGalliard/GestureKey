import { useT } from "../../i18n";
import { GESTURE_GROUPS } from "../../lib/protocol";
import type { EngineState } from "../../lib/useEngine";
import { Row, Section } from "../ui/Page";
import { Switch } from "../ui/Switch";

export function GesturesTab({ engine }: { engine: EngineState }) {
  const t = useT();
  const { config, send } = engine;
  return (
    <>
      <p className="mb-6 text-[13px] leading-relaxed text-fg-muted">{t.settings.gestures.intro}</p>
      {GESTURE_GROUPS.map((group) => (
        <Section key={group.id} title={t.settings.gestures.groups[group.id]}>
          {group.keys.map((key) => {
            const on = config?.gestures[key]?.enabled ?? false;
            const text = t.gestures[key];
            return (
              <Row key={key} title={text.label} hint={text.hint} muted={!on}>
                <Switch
                  on={on}
                  disabled={!config}
                  label={text.label}
                  onChange={(enabled) => send({ cmd: "set_config", patch: { gestures: { [key]: { enabled } } } })}
                />
              </Row>
            );
          })}
        </Section>
      ))}
    </>
  );
}
