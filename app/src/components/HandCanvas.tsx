import { useEffect, useRef } from "react";
import type { FrameMsg } from "../lib/protocol";

const BONES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11],
  [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
];
const TIPS = new Set([4, 8, 12, 16, 20]);

/** Canvas can't read Tailwind classes: resolve the theme tokens once. */
function tokens() {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return { fg: v("--color-fg"), accent: v("--color-accent-light"), hold: v("--color-hold"), muted: v("--color-fg-muted") };
}

interface Props {
  frame: FrameMsg | null;
  preview: string | null; // base64 JPEG, only while the video toggle is on
}

/** Draws the tracked hands from landmarks; the video is optional backdrop. */
export function HandCanvas({ frame, preview }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef    = useRef<HTMLImageElement | null>(null);
  const colors    = useRef<ReturnType<typeof tokens> | null>(null);

  useEffect(() => {
    if (!preview) { imgRef.current = null; return; }
    const img = new Image();
    img.src = `data:image/jpeg;base64,${preview}`;
    img.onload = () => { imgRef.current = img; };
  }, [preview]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const c = (colors.current ??= tokens());

    const dpr = window.devicePixelRatio || 1;
    const { clientWidth: w, clientHeight: h } = canvas;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (imgRef.current) {
      ctx.globalAlpha = 0.28;
      ctx.drawImage(imgRef.current, 0, 0, w, h);
      ctx.globalAlpha = 1;
    }

    const tip = frame?.owner === "GRAB_WINDOW" ? c.hold : c.accent;
    for (const hand of frame?.hands ?? []) {
      const pts = hand.landmarks.map(([x, y]) => [x * w, y * h] as const);

      ctx.strokeStyle = c.fg;
      ctx.globalAlpha = 0.28;
      ctx.lineWidth = 1.5;
      ctx.lineCap = "round";
      ctx.beginPath();
      for (const [a, b] of BONES) {
        ctx.moveTo(pts[a][0], pts[a][1]);
        ctx.lineTo(pts[b][0], pts[b][1]);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;

      pts.forEach(([x, y], i) => {
        const isTip = TIPS.has(i);
        if (isTip) {
          ctx.fillStyle = tip;
          ctx.globalAlpha = 0.18;
          ctx.beginPath();
          ctx.arc(x, y, 11, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
        }
        ctx.fillStyle = isTip ? tip : c.fg;
        ctx.beginPath();
        ctx.arc(x, y, isTip ? 4 : 2.5, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.fillStyle = c.muted;
      ctx.font = "500 10px 'Fira Code', monospace";
      ctx.fillText(hand.side === "Right" ? "DER" : "IZQ", pts[0][0] + 10, pts[0][1] + 14);
    }
  }, [frame]);

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />;
}
