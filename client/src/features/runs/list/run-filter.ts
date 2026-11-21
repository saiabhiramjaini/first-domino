import type { RunStatus } from "@/api/generated";

export type RunFilter = "all" | RunStatus;

export const RUN_FILTERS: ReadonlyArray<{ value: RunFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "failed", label: "Failed" },
  { value: "passed", label: "Passed" },
  { value: "running", label: "Running" },
  { value: "errored", label: "Errored" },
];

export function statusesOf(filter: RunFilter): RunStatus[] | undefined {
  return filter === "all" ? undefined : [filter];
}

/** The filter named in the URL (`?status=failed`), or "all" for anything else. */
export function runFilterFrom(value: string | string[] | undefined): RunFilter {
  const found = RUN_FILTERS.find((item) => item.value === value);
  return found ? found.value : "all";
}
