import { motion } from "framer-motion";

interface Props {
  on: boolean;
  disabled?: boolean;
  onChange: (on: boolean) => void;
  label: string;
  size?: "md" | "lg";
}

const SIZES = {
  md: { track: "h-[18px] w-8",  knob: 12, pad: 3 },
  lg: { track: "h-7 w-12",      knob: 20, pad: 4 },
};

export function Switch({ on, disabled, onChange, label, size = "md" }: Props) {
  const s = SIZES[size];
  const width = size === "md" ? 32 : 48;
  return (
    <button
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!on)}
      className={`relative shrink-0 rounded-full transition-colors duration-200 disabled:opacity-30 ${s.track} ${
        on ? "bg-accent" : "bg-white/10 hover:bg-white/15"
      }`}
    >
      <motion.span
        className="absolute rounded-full bg-fg shadow-sm"
        style={{ width: s.knob, height: s.knob, top: s.pad }}
        animate={{ left: on ? width - s.knob - s.pad : s.pad }}
        transition={{ duration: 0.24, ease: [0.32, 0.72, 0, 1] }}
      />
    </button>
  );
}
