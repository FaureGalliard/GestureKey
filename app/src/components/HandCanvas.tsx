import { useEffect, useRef } from "react";
import type { FrameMsg } from "../lib/protocol";

const BONES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11],
  [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
];
const TIPS = new Set([4, 8, 12, 16, 20]);

interface Props {
  frame: FrameMsg | null;
  preview: string | null; // base64 JPEG, only while preview is on
}

/** Draws the tracked hands from landmarks (no video needed). */
export function HandCanvas({ frame, preview }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef    = useRef<HTMLImageElement | null>(null);

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

    const dpr = window.devicePixelRatio || 1;
    const { clientWidth: w, clientHeight: h } = canvas;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (imgRef.current) {
      ctx.globalAlpha = 0.35;
      ctx.drawImage(imgRef.current, 0, 0, w, h);
      ctx.globalAlpha = 1;
    }

    const grabbing = frame?.owner === "GRAB_WINDOW";
    for (const hand of frame?.hands ?? []) {
      const pts = hand.landmarks.map(([x, y]) => [x * w, y * h] as const);
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      for (const [a, b] of BONES) {
        ctx.beginPath();
        ctx.moveTo(pts[a][0], pts[a][1]);
        ctx.lineTo(pts[b][0], pts[b][1]);
        ctx.stroke();
      }
      pts.forEach(([x, y], i) => {
        ctx.fillStyle = TIPS.has(i) ? (grabbing ? "#f87171" : "#34d399") : "rgba(255,255,255,0.8)";
        ctx.beginPath();
        ctx.arc(x, y, TIPS.has(i) ? 4.5 : 3, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.fillStyle = "rgba(255,255,255,0.6)";
      ctx.font = "11px ui-sans-serif, system-ui";
      ctx.fillText(hand.side === "Right" ? "Derecha" : "Izquierda", pts[0][0] + 8, pts[0][1] + 16);
    }
  }, [frame]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-white/5 bg-black/40">
      <canvas ref={canvasRef} className="h-full w-full" />
      {!frame?.hands.length && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-sm text-white/30">
          Muestra una mano a la cámara
        </div>
      )}
    </div>
  );
}
