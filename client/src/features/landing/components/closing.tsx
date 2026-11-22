"use client";

import { ArrowRightIcon } from "lucide-react";
import { motion, useScroll, useTransform } from "motion/react";
import Link from "next/link";
import { useRef } from "react";

import { buttonVariants } from "@/components/ui/button";

/** The last word: grows into place as you reach the end of the page. */
export function Closing({ appHref, startLabel }: { appHref: string; startLabel: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "center center"] });
  const scale = useTransform(scrollYProgress, [0, 1], [0.7, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [0, 1]);
  const spacing = useTransform(scrollYProgress, [0, 1], ["0.04em", "-0.06em"]);
  return (
    <div ref={ref} className="flex flex-col items-center gap-8 text-center">
      <motion.h2
        style={{ scale, opacity, letterSpacing: spacing, lineHeight: 0.9 }}
        className="bg-gradient-to-b from-foreground to-muted-foreground bg-clip-text text-7xl font-extrabold text-transparent sm:text-8xl lg:text-9xl"
      >
        Stop guessing.
      </motion.h2>
      <p className="max-w-xl text-lg text-pretty text-muted-foreground">
        Find the step that broke your agent, and prove it by replay. Two lines of Python.
      </p>
      <Link href={appHref} className={buttonVariants({ variant: "brand", size: "lg" })}>
        {startLabel}
        <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
      </Link>
    </div>
  );
}
