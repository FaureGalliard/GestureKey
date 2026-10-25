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
  const { config, cameras, send } = engine;
  const device = config?.camera.device ?? 0;
  const options = (cameras.length ? cameras : [{ index: device, name: `Cámara ${device}` }])
    .map((c) => ({ value: c.index, label: c.name }));

  return (
    <Section title="Cámara">
      <div className="border-b border-line py-3.5">
        <div className="mb-2.5 text-[14px] font-medium">Dispositivo</div>
        <Menu
          value={device}
          options={options}
          disabled={!config}
          onOpen={() => send({ cmd: "list_cameras" })}
          onChange={(index) => send({ cmd: "set_config", patch: { camera: { device: index } } })}
          empty="Sin cámaras"
        />
      </div>
      <Row title="Vista espejo" hint="Al mover la mano a la derecha, todo va a la derecha.">
        <Switch
          label="Vista espejo"
          on={config?.camera.mirror ?? true}
          disabled={!config}
          onChange={(mirror) => send({ cmd: "set_config", patch: { camera: { mirror } } })}
        />
      </Row>
      <Row title="Mostrar video" hint="Ver la cámara detrás de la mano en la pantalla principal.">
        <Switch label="Mostrar video" on={videoOn} disabled={!config} onChange={onVideo} />
      </Row>
    </Section>
  );
}
