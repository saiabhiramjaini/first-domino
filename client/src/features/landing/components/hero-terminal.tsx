"use client";

import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { useEffect, useState, type PointerEvent } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

import { type Color, finalTerminal, ROWS, terminalAt } from "../terminal-script";

// A terminal palette close to a tuned iTerm theme: soft and readable on the dark window.
const COLORS: Record<Color, string> = {
  fg: "#e4e4e7",
  dim: "#7c7c86",
  green: "#5fd18a",
  cyan: "#56c8d8",
  blue: "#6ea8fe",
  red: "#ff6b6b",
  yellow: "#e5c07b",
  magenta: "#d38cf0",
  violet: "#a99dff",
  string: "#9ad186",
  comment: "#6a6a75",
};
const TRAFFIC = ["#ff5f57", "#febc2e", "#28c840"];
const LINE_EM = 1.66;
const TICK_MS = 33;

/** A real-feeling zsh window: traffic lights, a title, a blinking block cursor, scrolling output. */
export function HeroTerminal() {
  const reducedMotion = usePrefersReducedMotion();
  const [ms, setMs] = useState(0);

  useEffect(() => {
    if (reducedMotion) return;
    const start = performance.now();
    const timer = window.setInterval(() => setMs(performance.now() - start), TICK_MS);
    return () => window.clearInterval(timer);
  }, [reducedMotion]);

  // The window leans a few degrees toward the pointer.
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const rotateY = useSpring(useTransform(px, [-0.5, 0.5], [-6, 6]), {
    stiffness: 120,
    damping: 18,
  });
  const rotateX = useSpring(useTransform(py, [-0.5, 0.5], [5, -5]), {
    stiffness: 120,
    damping: 18,
  });
  function track(event: PointerEvent<HTMLDivElement>) {
    if (reducedMotion) return;
    const rect = event.currentTarget.getBoundingClientRect();
    px.set((event.clientX - rect.left) / rect.width - 0.5);
    py.set((event.clientY - rect.top) / rect.height - 0.5);
  }
  function reset() {
    px.set(0);
    py.set(0);
  }

  const frame = reducedMotion ? finalTerminal() : terminalAt(ms);
  const blinkOn = reducedMotion || Math.floor(ms / 530) % 2 === 0;

  return (
    <div
      className="relative"
      style={{ perspective: 1400 }}
      onPointerMove={track}
      onPointerLeave={reset}
    >
      {/* Light behind the window */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-10 -z-10 rounded-full opacity-70 blur-3xl"
        style={{
          background:
            "radial-gradient(closest-side, color-mix(in srgb, var(--domino) 35%, transparent), transparent)",
        }}
      />
      <motion.figure
        aria-label="A terminal: install First Domino, add two lines to the agent, run it, and the worker finds and proves the failing step"
        initial={reducedMotion ? false : { opacity: 0, y: 40, rotateX: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: 0.35 }}
        style={{ rotateX, rotateY }}
        className="overflow-hidden rounded-xl border border-white/10 shadow-2xl shadow-black/60"
      >
        <div
          className="relative flex h-9 items-center border-b border-black/40"
          style={{ background: "linear-gradient(#2c2c31, #242428)" }}
        >
          <div className="flex gap-2 pl-3.5" aria-hidden="true">
            {TRAFFIC.map((color) => (
              <span
                key={color}
                className="size-3 rounded-full"
                style={{ background: color, boxShadow: "inset 0 0 0 0.5px rgba(0,0,0,0.3)" }}
              />
            ))}
          </div>
          <span className="absolute inset-x-0 text-center font-mono text-xs text-white/50">
            agent — -zsh — 84×{ROWS}
          </span>
        </div>
        <div
          aria-hidden="true"
          className="overflow-hidden px-4 py-3 font-mono"
          style={{
            background: "rgba(15,15,18,0.97)",
            // The type shrinks with the screen, like a terminal window made narrower.
            fontSize: "clamp(8px, 2.3vw, 12px)",
            lineHeight: LINE_EM,
            height: `calc(${ROWS * LINE_EM}em + 24px)`,
          }}
        >
          {frame.lines.map((line, i) => (
            <div key={i} className="whitespace-pre">
              {line.map((span, j) => (
                <span
                  key={j}
                  style={{ color: COLORS[span.color ?? "fg"], fontWeight: span.bold ? 700 : 400 }}
                >
                  {span.text}
                </span>
              ))}
              {frame.cursorLine === i && (
                <span
                  className="inline-block align-text-bottom"
                  style={{
                    width: "0.6em",
                    height: "1.3em",
                    background: blinkOn ? COLORS.fg : "transparent",
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </motion.figure>
    </div>
  );
}
