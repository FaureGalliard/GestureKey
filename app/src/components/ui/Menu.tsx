import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Pill } from "./Pill";

export interface MenuOption<T> {
  value: T;
  label: string;
}

interface Props<T> {
  value: T;
  options: MenuOption<T>[];
  onChange: (value: T) => void;
  onOpen?: () => void;
  disabled?: boolean;
  empty?: ReactNode;
  className?: string;
}

/** Pill that opens the teleprompter-style dropdown (chrome-raised, rounded-xl). */
export function Menu<T extends string | number>({
  value, options, onChange, onOpen, disabled, empty, className = "",
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const current = options.find((o) => o.value === value);

  return (
    <div ref={ref} className={`relative ${className}`}>
      <Pill
        disabled={disabled}
        className="w-full justify-between normal-case tracking-normal"
        onClick={() => {
          if (!open) onOpen?.();
          setOpen((v) => !v);
        }}
      >
        <span className="truncate">{current?.label ?? "—"}</span>
        <span className="text-[9px] opacity-50">{open ? "▲" : "▼"}</span>
      </Pill>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.14, ease: "easeOut" }}
            className="absolute left-0 right-0 top-full z-50 mt-2 flex flex-col overflow-hidden rounded-xl border border-white/10 bg-chrome-raised shadow-xl"
          >
            {options.map((o) => (
              <button
                key={String(o.value)}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                className={`truncate px-4 py-1.5 text-left text-[11px] font-medium transition-colors ${
                  o.value === value ? "bg-accent text-fg" : "text-fg/70 hover:bg-white/10 hover:text-fg"
                }`}
              >
                {o.label}
              </button>
            ))}
            {options.length === 0 && <span className="px-4 py-1.5 text-[11px] text-fg-faint">{empty}</span>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
