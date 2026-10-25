import { GESTURE_GROUPS, GESTURES } from "../../lib/protocol";
import type { EngineState } from "../../lib/useEngine";
import { Row, Section } from "../ui/Page";
import { Switch } from "../ui/Switch";

export function GesturesTab({ engine }: { engine: EngineState }) {
  const { config, send } = engine;
  return (
    <>
      <p className="mb-6 text-[13px] leading-relaxed text-fg-muted">
        Activa solo los que vayas a usar: menos gestos, menos sorpresas.
      </p>
      {GESTURE_GROUPS.map((group) => (
        <Section key={group.title} title={group.title}>
          {group.keys.map((key) => {
            const on = config?.gestures[key]?.enabled ?? false;
            return (
              <Row key={key} title={GESTURES[key].label} hint={GESTURES[key].hint} muted={!on}>
                <Switch
                  on={on}
                  disabled={!config}
                  label={GESTURES[key].label}
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
