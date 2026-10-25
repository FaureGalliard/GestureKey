import { DICTS, LANGS, useT, type LangSetting } from "../../i18n";
import type { EngineState } from "../../lib/useEngine";
import { Menu } from "../ui/Menu";
import { Section } from "../ui/Page";

export function GeneralTab({ engine }: { engine: EngineState }) {
  const t = useT().settings.general;
  const { config, send } = engine;
  const current = (config?.ui?.language ?? "auto") as LangSetting;
  // each language in its own name, so anyone can find theirs
  const options = [
    { value: "auto" as LangSetting, label: t.auto },
    ...LANGS.map((lang) => ({ value: lang as LangSetting, label: DICTS[lang].langName })),
  ];

  return (
    <Section title={t.language}>
      <div className="border-b border-line py-3.5">
        <p className="mb-2.5 text-[12.5px] leading-snug text-fg-faint">{t.languageHint}</p>
        <Menu
          value={current}
          options={options}
          disabled={!config}
          onChange={(language) => send({ cmd: "set_config", patch: { ui: { language } } })}
        />
      </div>
    </Section>
  );
}
