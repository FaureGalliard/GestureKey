import { forwardRef, type ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger" | "inverted";

const BASE =
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.04em] " +
  "transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-30";

const VARIANTS: Record<Variant, string> = {
  primary:  "bg-accent text-fg hover:bg-accent-strong",
  ghost:    "bg-white/10 text-fg hover:bg-white/20",
  danger:   "bg-white/10 text-fg hover:bg-danger/80",
  inverted: "bg-fg text-chrome hover:bg-fg/90",
};

interface PillProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

/** The teleprompter's rounded-full button. */
export const Pill = forwardRef<HTMLButtonElement, PillProps>(
  ({ variant = "ghost", className = "", ...props }, ref) => (
    <button ref={ref} className={`${BASE} ${VARIANTS[variant]} ${className}`} {...props} />
  ),
);
Pill.displayName = "Pill";

/** Thin vertical divider between pill groups. */
export function PillDivider() {
  return <div className="mx-1 h-5 w-px bg-white/15" />;
}
