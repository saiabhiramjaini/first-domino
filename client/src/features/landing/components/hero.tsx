"use client";

import { ArrowRightIcon, CheckIcon, CopyIcon, PlayIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useEffect, useRef, useState, type PointerEvent } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

import { HERO_LEAD, HERO_WORDS } from "../hero-words";
import { HeroTerminal } from "./hero-terminal";

const EASE = [0.16, 1, 0.3, 1] as const;
const WORD_MS = 2_600;
const INSTALL = "pip install first-domino";

const LEAVE_MS = 320;

/** Letters rise into view from behind a mask, one after another, and rise out when leaving. */
function MaskedWord({
  text,
  delay = 0,
  leaving = false,
}: {
  text: string;
  delay?: number;
  leaving?: boolean;
}) {
  return (
    <span
      // The mask needs room for the glyphs' full height: the heading's tight line height would
      // otherwise cut the bottoms of letters and the tails of g and y. The margins take that room
      // back so the layout does not move.
      style={{
        display: "inline-flex",
        overflow: "hidden",
        padding: "0.14em 0.04em 0.28em",
        margin: "-0.14em -0.04em -0.28em",
      }}
    >
      {[...text].map((ch, i) => (
        <motion.span
          key={i}
          // Leaving words sink and fade rather than rise: rising would pass up through the
          // line above and show under its descenders.
          initial={{ y: "110%", opacity: 1 }}
          animate={leaving ? { y: "35%", opacity: 0 } : { y: "0%", opacity: 1 }}
          transition={
            leaving
              ? { duration: 0.28, ease: EASE, delay: i * 0.012 }
              : { duration: 0.7, ease: EASE, delay: delay + i * 0.028 }
          }
          style={{ display: "inline-block", whiteSpace: "pre" }}
        >
          {ch}
        </motion.span>
      ))}
    </span>
  );
}

/** A hand-drawn red line that draws itself across the word, left to right, and fades when it leaves. */
function Scribble({ leaving }: { leaving: boolean }) {
  return (
    <motion.span
      aria-hidden="true"
      className="pointer-events-none absolute left-0 block w-full text-destructive"
      style={{ top: "38%", height: "0.32em" }}
      initial={{ clipPath: "inset(0 100% 0 0)", opacity: 1 }}
      animate={leaving ? { opacity: 0 } : { clipPath: "inset(0 0% 0 0)", opacity: 1 }}
      transition={leaving ? { duration: 0.12 } : { duration: 0.45, ease: "easeInOut", delay: 0.85 }}
    >
      <svg viewBox="0 0 100 20" preserveAspectRatio="none" className="block size-full">
        <path
          d="M2 12 C 18 5, 30 16, 48 10 S 78 5, 98 11"
          fill="none"
          stroke="currentColor"
          strokeWidth={7}
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </motion.span>
  );
}

/**
 * The struck-through word under the lead word. A timer, not exit animations, runs the cycle: mark the
 * word as leaving, let it rise out, then mount the next one fresh. Nothing is left behind.
 */
function CyclingWord({ reducedMotion }: { reducedMotion: boolean }) {
  const [cycled, setCycled] = useState(0);
  const [leaving, setLeaving] = useState(false);
  useEffect(() => {
    if (reducedMotion) return;
    let swap = 0;
    const timer = window.setInterval(() => {
      setLeaving(true);
      swap = window.setTimeout(() => {
        setCycled((i) => (i + 1) % HERO_WORDS.length);
        setLeaving(false);
      }, LEAVE_MS);
    }, WORD_MS);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(swap);
    };
  }, [reducedMotion]);
  // With reduced motion, only the last word shows, still.
  const index = reducedMotion ? HERO_WORDS.length - 1 : cycled;
  const word = HERO_WORDS[index] ?? HERO_WORDS[0];
  return (
    <span className="relative block" style={{ height: "1.08em" }} aria-hidden="true">
      <span
        key={index}
        className={`absolute top-0 left-0 inline-block ${word.accent ? "text-domino" : "text-muted-foreground"}`}
      >
        <span className="relative inline-block">
          <MaskedWord text={word.text} leaving={leaving} />
          <Scribble leaving={leaving} />
        </span>
      </span>
    </span>
  );
}

function InstallChip() {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(INSTALL);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1_800);
    } catch {
      setCopied(false);
    }
  }
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={copy}
      className="w-fit gap-2 font-mono text-muted-foreground"
    >
      <span className="text-domino">$</span> {INSTALL}
      {copied ? <CheckIcon aria-hidden="true" /> : <CopyIcon aria-hidden="true" />}
      <span className="sr-only">{copied ? "Copied" : "Copy the install command"}</span>
    </Button>
  );
}

type HeroProps = { appHref: string; startLabel: string };

export function Hero({ appHref, startLabel }: HeroProps) {
  const reducedMotion = usePrefersReducedMotion();
  const backdrop = useRef<HTMLDivElement>(null);

  // A soft light follows the pointer across the dot grid.
  function light(event: PointerEvent<HTMLElement>) {
    const el = backdrop.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--x", `${event.clientX - rect.left}px`);
    el.style.setProperty("--y", `${event.clientY - rect.top}px`);
  }

  const rise = (delay: number) =>
    reducedMotion
      ? {}
      : {
          initial: { opacity: 0, y: 24, filter: "blur(8px)" },
          animate: { opacity: 1, y: 0, filter: "blur(0px)" },
          transition: { duration: 0.9, ease: EASE, delay },
        };

  return (
    <section aria-labelledby="hero-title" className="relative isolate" onPointerMove={light}>
      <div
        ref={backdrop}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(rgba(255,255,255,0.07) 1px, transparent 1px)",
            backgroundSize: "26px 26px",
            maskImage: "linear-gradient(to bottom, black 40%, transparent)",
          }}
        />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(rgba(169,157,255,0.55) 1px, transparent 1px)",
            backgroundSize: "26px 26px",
            maskImage:
              "radial-gradient(260px circle at var(--x, 70%) var(--y, 30%), black, transparent)",
          }}
        />
      </div>

      <div className="mx-auto grid w-full max-w-6xl items-center gap-14 px-4 pt-14 pb-24 sm:px-6 sm:pt-20 lg:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-8">
          <motion.span
            {...rise(0)}
            className="inline-flex w-fit items-center gap-2 rounded-full border bg-card/60 px-3 py-1 font-mono text-xs text-muted-foreground"
          >
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-domino opacity-60 motion-reduce:animate-none" />
              <span className="relative inline-flex size-1.5 rounded-full bg-domino" />
            </span>
            Root causes for failed AI agents, proven by replay
          </motion.span>

          <h1
            id="hero-title"
            aria-label={`${HERO_LEAD} ${HERO_WORDS.map((w) => w.text.replace(".", "")).join(", ")}.`}
            className="text-6xl font-extrabold sm:text-7xl xl:text-8xl"
            style={{ letterSpacing: "-0.055em", lineHeight: 0.92 }}
          >
            <span aria-hidden="true" className="block">
              {reducedMotion ? HERO_LEAD : <MaskedWord text={HERO_LEAD} delay={0.1} />}
            </span>
            <CyclingWord reducedMotion={reducedMotion} />
          </h1>

          <motion.div {...rise(0.35)} className="flex max-w-xl flex-col gap-4">
            <p
              className="text-2xl font-semibold text-balance sm:text-3xl"
              style={{ letterSpacing: "-0.02em" }}
            >
              They show you every step.
              <br />
              <span className="text-muted-foreground">We prove which one broke your agent.</span>
            </p>
            <p className="text-pretty text-muted-foreground">
              Tracing platforms record a failed run and guess what went wrong. First Domino replays
              it from its own save points, finds the first step after which it always fails, then
              fixes that step and replays again to prove it.
            </p>
          </motion.div>

          <motion.div {...rise(0.5)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link href={appHref} className={buttonVariants({ variant: "brand", size: "lg" })}>
                {startLabel}
                <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
              </Link>
              <a href="#film" className={buttonVariants({ variant: "outline", size: "lg" })}>
                <PlayIcon data-icon="inline-start" aria-hidden="true" />
                Watch the film
              </a>
            </div>
            <InstallChip />
          </motion.div>
        </div>

        <div className="min-w-0">
          <HeroTerminal />
        </div>
      </div>
    </section>
  );
}
