import { createContext, useContext, useEffect, type ReactNode } from "react";
import { en, type Dict } from "./en";
import { es } from "./es";
import { fr } from "./fr";
import { ko } from "./ko";

export const DICTS = { en, es, fr, ko } satisfies Record<string, Dict>;
export type Lang = keyof typeof DICTS;
export type LangSetting = Lang | "auto";

export const LANGS = Object.keys(DICTS) as Lang[];
const STORAGE_KEY = "gk.lang";

/** "auto" → the first system language we have, else English. */
export function resolveLang(setting?: string | null): Lang {
  if (setting && setting in DICTS) return setting as Lang;
  const system = typeof navigator !== "undefined" ? navigator.languages ?? [navigator.language] : [];
  for (const tag of system) {
    const base = tag.toLowerCase().split("-")[0];
    if (base in DICTS) return base as Lang;
  }
  return "en";
}

/**
 * The language before the engine's config arrives: last one used (so the
 * first frame isn't in the wrong language), else the system's.
 */
export function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved in DICTS) return saved as Lang;
  } catch {
    /* storage may be unavailable */
  }
  return resolveLang("auto");
}

const Ctx = createContext<Dict>(en);

export function I18nProvider({ lang, children }: { lang: Lang; children: ReactNode }) {
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* ignore */
    }
  }, [lang]);
  return <Ctx.Provider value={DICTS[lang]}>{children}</Ctx.Provider>;
}

/** The current dictionary: `const t = useT(); t.home.ready.title` */
export const useT = () => useContext(Ctx);
