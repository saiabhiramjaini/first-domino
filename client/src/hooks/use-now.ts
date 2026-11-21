"use client";

import { useEffect, useState } from "react";

/**
 * The current time, re-read every `intervalMs` so time-based text ("waiting 2 minutes",
 * a running duration) moves even when no data changes. `false` stops the clock.
 */
export function useNow(intervalMs: number | false): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (intervalMs === false) return;
    const timer = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
