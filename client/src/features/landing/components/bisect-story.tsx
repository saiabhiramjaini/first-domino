"use client";

import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { useRef, useState } from "react";

import { useMediaQuery } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";

import { Domino3D, type DominoLook, DominoStage } from "./domino-3d";

// Tile sizes for a phone and for anything wider.
const SIZES = { narrow: { tile: 34, gap: 9 }, wide: { tile: 64, gap: 22 } } as const;

type Stage = {
  eyebrow: string;
  title: string;
  body: string;
  keep: number | null; // where the save point marker sits
  range: [number, number] | null;
  result?: { text: string; tone: "pass" | "fail" | "first" };
  tile: (i: number) => {
    look: DominoLook;
    fall?: number;
    flip?: number;
    glow?: number;
    lift?: number;
    delay?: number;
  };
};

const fallCascade = (i: number, from: number) => (i - from) * 0.12;

// Scrolling walks through a real search, one check per screen.
const STAGES: Stage[] = [
  {
    eyebrow: "The failed run",
    title: "8 steps. One of them broke the run.",
    body: "Your check failed at the end. Every model call is a step, and every step is a save point we can replay from.",
    keep: null,
    range: [1, 8],
    tile: () => ({ look: "idle" }),
  },
  {
    eyebrow: "Check 1",
    title: "Keep steps 1–\u20604, replay the rest.",
    body: "Your own agent runs steps 5 to 8 again, three times, on your machine. One of them passes: the damage is still ahead.",
    keep: 4,
    range: [5, 8],
    result: { text: "can pass · 2 of 3", tone: "pass" },
    tile: (i) => ({ look: i < 4 ? "kept" : "pass" }),
  },
  {
    eyebrow: "Check 2",
    title: "Keep steps 1–\u20606. It always fails.",
    body: "Six replays, not one pass. Something in steps 5 or 6 already decided the outcome.",
    keep: 6,
    range: [5, 6],
    result: { text: "always fails · 0 of 6", tone: "fail" },
    tile: (i) => (i < 6 ? { look: "kept" } : { look: "fail", fall: 1, delay: fallCascade(i, 6) }),
  },
  {
    eyebrow: "Check 3",
    title: "Keep steps 1–\u20605. Still always fails.",
    body: "Step 4 could still pass; step 5 never can. The search is over in three checks instead of eight.",
    keep: 5,
    range: [5, 5],
    result: { text: "always fails · 0 of 6", tone: "fail" },
    tile: (i) => (i < 5 ? { look: "kept" } : { look: "fail", fall: 1, delay: fallCascade(i, 5) }),
  },
  {
    eyebrow: "Found",
    title: "Step 5 is the first domino.",
    body: "The first step after which the run can no longer pass. Everything that went wrong later was falling from here.",
    keep: null,
    range: null,
    tile: (i) => (i === 4 ? { look: "first", glow: 1, lift: 22 } : { look: "dim" }),
  },
  {
    eyebrow: "Proof",
    title: "Fix step 5. Replay. 3 of 3 pass.",
    body: "A model rewrites only that step and your agent runs the rest. The failure turns into a pass: proven, not guessed.",
    keep: null,
    range: null,
    result: { text: "proven · 3 of 3 pass", tone: "first" },
    tile: (i) =>
      i === 4
        ? { look: "first", flip: 1, glow: 0.6, lift: 12 }
        : i < 4
          ? { look: "kept" }
          : { look: "pass", delay: 0.4 + (i - 5) * 0.12, lift: 0 },
  },
];

export function BisectStory() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [stageIndex, setStageIndex] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    setStageIndex(Math.min(STAGES.length - 1, Math.max(0, Math.floor(p * STAGES.length))));
  });
  const stage = STAGES[stageIndex] ?? (STAGES[0] as Stage);
  const { tile: TILE, gap: GAP } = SIZES[useMediaQuery("(min-width: 640px)") ? "wide" : "narrow"];
  const PITCH = TILE + GAP;
  const rowWidth = PITCH * 8 - GAP;

  return (
    <div ref={ref} className="relative" style={{ height: `${STAGES.length * 85}vh` }}>
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
          <div className="flex min-h-64 min-w-0 flex-col gap-4">
            <span className="font-mono text-xs text-muted-foreground">How it works</span>
            <AnimatePresence mode="wait">
              <motion.div
                key={stageIndex}
                initial={{ opacity: 0, y: 24, filter: "blur(8px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -16, filter: "blur(6px)" }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                className="flex flex-col gap-4"
              >
                <span
                  className={cn(
                    "font-mono text-sm",
                    stage.result?.tone === "first" || stageIndex === 4
                      ? "text-domino"
                      : "text-muted-foreground"
                  )}
                >
                  {stage.eyebrow}
                </span>
                <h2
                  className="text-4xl font-bold text-balance sm:text-5xl"
                  style={{ letterSpacing: "-0.04em", lineHeight: 1.02 }}
                >
                  {stage.title}
                </h2>
                <p className="max-w-md text-lg text-pretty text-muted-foreground">{stage.body}</p>
              </motion.div>
            </AnimatePresence>
            <ol className="mt-4 flex gap-2" aria-label="Progress">
              {STAGES.map((s, i) => (
                <li
                  key={s.eyebrow}
                  className={cn(
                    "h-1 w-10 rounded-full transition-colors duration-500",
                    i <= stageIndex ? (i >= 4 ? "bg-domino" : "bg-foreground") : "bg-border"
                  )}
                >
                  <span className="sr-only">{s.eyebrow}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="flex min-w-0 justify-center">
            <div>
              <DominoStage>
                <div
                  className="relative flex items-end"
                  style={{ gap: GAP, width: rowWidth, transformStyle: "preserve-3d" }}
                >
                  {Array.from({ length: 8 }, (_, i) => {
                    const t = stage.tile(i);
                    return (
                      <Domino3D
                        key={i}
                        n={i + 1}
                        size={TILE}
                        look={t.look}
                        fall={t.fall}
                        flip={t.flip}
                        glow={t.glow}
                        lift={t.lift}
                        delay={t.delay}
                      />
                    );
                  })}
                  {/* The save point: everything left of it is kept as recorded. */}
                  <div
                    className="absolute rounded-full bg-domino transition-all duration-700"
                    style={{
                      left: (stage.keep ?? 0) * PITCH - GAP / 2 - 2,
                      bottom: -16,
                      width: 4,
                      height: TILE * 1.9 + 32,
                      opacity: stage.keep ? 1 : 0,
                      boxShadow: "0 0 24px rgba(139,124,255,0.9)",
                      transitionTimingFunction: "cubic-bezier(.16,1,.3,1)",
                    }}
                  >
                    <span className="absolute -top-9 left-1/2 -translate-x-1/2 rounded-md bg-domino px-2 py-1 font-mono text-xs font-bold whitespace-nowrap text-domino-foreground">
                      keep 1–{stage.keep ?? 4}
                    </span>
                  </div>
                  {/* The search range narrows after each check. */}
                  <div
                    className="absolute rounded-b-lg border-2 border-t-0 border-white/35 transition-all duration-700"
                    style={{
                      left: ((stage.range?.[0] ?? 5) - 1) * PITCH,
                      width: ((stage.range?.[1] ?? 5) - (stage.range?.[0] ?? 5)) * PITCH + TILE,
                      top: TILE * 1.9 + 26,
                      height: 16,
                      opacity: stage.range ? 1 : 0,
                      transitionTimingFunction: "cubic-bezier(.16,1,.3,1)",
                    }}
                  >
                    <span className="absolute top-6 left-1/2 -translate-x-1/2 font-mono text-sm whitespace-nowrap text-muted-foreground">
                      {stage.range && stage.range[0] === stage.range[1]
                        ? `step ${stage.range[0]}`
                        : `search range ${stage.range?.[0] ?? 1}–${stage.range?.[1] ?? 8}`}
                    </span>
                  </div>
                </div>
              </DominoStage>
              <div className="mt-24 flex h-10 justify-center">
                <AnimatePresence mode="wait">
                  {stage.result && (
                    <motion.span
                      key={stage.result.text}
                      initial={{ opacity: 0, scale: 1.6 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ type: "spring", damping: 12, stiffness: 180 }}
                      className={cn(
                        "rounded-full px-5 py-2 font-mono text-lg font-semibold",
                        stage.result.tone === "fail" && "bg-destructive/15 text-destructive",
                        stage.result.tone === "pass" && "bg-foreground/10 text-foreground",
                        stage.result.tone === "first" && "bg-domino/15 text-domino"
                      )}
                    >
                      {stage.result.text}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
