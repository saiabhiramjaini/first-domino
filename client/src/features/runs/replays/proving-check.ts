import type { Check } from "@/api/generated";

/**
 * The check that proved a fix of `dominoStep`: a verify or fallback check that rewrote that
 * step (it kept the steps before it) and passed. The last one wins if there are several.
 */
export function provingCheck(checks: readonly Check[], dominoStep: number | null): Check | null {
  if (dominoStep === null) return null;
  const proving = checks.filter(
    (check) =>
      (check.phase === "verify" || check.phase === "fallback") &&
      check.result === "can_succeed" &&
      check.save_point + 1 === dominoStep
  );
  return proving.at(-1) ?? null;
}
