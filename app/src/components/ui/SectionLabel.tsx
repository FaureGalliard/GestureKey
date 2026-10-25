import type { ReactNode } from "react";

/** The website's section label (uppercase, tracked) at app scale. */
export function SectionLabel({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 pb-2 pt-5">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.04em] text-fg-muted">{children}</h2>
      {aside && <span className="font-mono text-[10px] text-fg-faint">{aside}</span>}
    </div>
  );
}
