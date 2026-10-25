import { motion } from "framer-motion";

interface Props {
  on: boolean;
  disabled?: boolean;
  onChange: (on: boolean) => void;
  label: string;
}

export function Switch({ on, disabled, onChange, label }: Props) {
  return (
    <button
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!on)}
      className={`relative h-[18px] w-8 shrink-0 rounded-full transition-colors duration-200 disabled:opacity-30 ${
        on ? "bg-accent" : "bg-white/10 hover:bg-white/15"
      }`}
    >
      <motion.span
        className="absolute top-[3px] h-3 w-3 rounded-full bg-fg"
        animate={{ left: on ? 17 : 3 }}
        transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
      />
    </button>
  );
}
