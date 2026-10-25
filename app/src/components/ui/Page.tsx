import { motion } from "framer-motion";
import type { ReactNode } from "react";

/** Page shell: display title (Inter's Display optical cut), quiet subtitle, content. */
export function Page({ title, subtitle, aside, children }: {
  title: string;
  subtitle?: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.32, 0.72, 0, 1] }}
      className="mx-auto flex w-full max-w-[720px] flex-col px-10 pb-10 pt-9"
    >
      <header className="mb-7 flex items-end justify-between gap-6">
        <div>
          <h1 className="text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] text-fg">{title}</h1>
          {subtitle && <p className="mt-2 text-[14px] leading-relaxed text-fg-muted">{subtitle}</p>}
        </div>
        {aside}
      </header>
      {children}
    </motion.div>
  );
}

/** The website's section label at app scale. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-fg-faint">{title}</h2>
      <div className="border-t border-line">{children}</div>
    </section>
  );
}

/** Row separated by a 1 px line — rows, not cards. */
export function Row({ title, hint, children, muted }: {
  title: ReactNode;
  hint?: ReactNode;
  children?: ReactNode;
  muted?: boolean;
}) {
  return (
    <div className="flex items-center gap-6 border-b border-line py-3.5">
      <div className="min-w-0 flex-1">
        <div className={`text-[14px] font-medium ${muted ? "text-fg-muted" : "text-fg"}`}>{title}</div>
        {hint && <div className="mt-0.5 text-[12.5px] leading-snug text-fg-faint">{hint}</div>}
      </div>
      {children}
    </div>
  );
}
