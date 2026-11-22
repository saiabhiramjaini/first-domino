"use client";

import { motion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";

/** The launch film grows from a card to full width as it scrolls into view. */
export function Film() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "center center"] });
  const scale = useTransform(scrollYProgress, [0, 1], [0.84, 1]);
  const radius = useTransform(scrollYProgress, [0, 1], [32, 16]);
  const opacity = useTransform(scrollYProgress, [0, 0.4], [0.3, 1]);
  return (
    <motion.div
      ref={ref}
      style={{ scale, borderRadius: radius, opacity }}
      className="overflow-hidden border border-white/10 bg-card shadow-2xl shadow-black/60"
    >
      <video
        className="block aspect-video w-full"
        controls
        playsInline
        preload="metadata"
        poster="/launch/first-domino-film-poster.jpg"
      >
        <source src="/launch/first-domino-film.mp4" type="video/mp4" />
      </video>
    </motion.div>
  );
}
