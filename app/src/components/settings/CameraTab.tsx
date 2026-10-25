import { useT } from "../../i18n";
import type { EngineState } from "../../lib/useEngine";
import { Menu } from "../ui/Menu";
import { Row, Section } from "../ui/Page";
import { Switch } from "../ui/Switch";

interface Props {
  engine: EngineState;
  videoOn: boolean;
  onVideo: (on: boolean) => void;
}

export function CameraTab({ engine, videoOn, onVideo }: Props) {
  const t = useT().settings.camera;
  const { config, cameras, send } = engine;
  const device = config?.camera.device ?? 0;
  const options = (cameras.length ? cameras : [{ index: device, name: config?.camera.name || t.fallback(device) }])
    .map((c) => ({ value: c.index, label: c.name }));

  return (
    <Section title={t.section}>
      <div className="border-b border-line py-3.5">
        <div className="mb-2.5 text-[14px] font-medium">{t.device}</div>
        <Menu
          value={device}
          options={options}
          disabled={!config}
          onOpen={() => send({ cmd: "list_cameras" })}
          onChange={(index) => send({ cmd: "set_config", patch: { camera: { device: index } } })}
          empty={t.noCameras}
        />
      </div>
      <Row title={t.mirror} hint={t.mirrorHint}>
        <Switch
          label={t.mirror}
          on={config?.camera.mirror ?? true}
          disabled={!config}
          onChange={(mirror) => send({ cmd: "set_config", patch: { camera: { mirror } } })}
        />
      </Row>
      <Row title={t.video} hint={t.videoHint}>
        <Switch label={t.video} on={videoOn} disabled={!config} onChange={onVideo} />
      </Row>
    </Section>
  );
}
