import type { Check } from "@/api/generated";

// One row of the Checks table. A save point with no passing replay is run again before it
// counts as doomed; those rounds are one check to a reader, so they share a row.
export type CheckRow = Check & {
  // Position in the table, from 1.
  number: number;
  // The stored checks behind this row, in order. Replays are listed per round.
  rounds: Check[];
};

export function checkRows(checks: readonly Check[]): CheckRow[] {
  const rows: CheckRow[] = [];
  for (const check of [...checks].sort((a, b) => a.index - b.index)) {
    const last = rows.at(-1);
    if (last && last.phase === check.phase && last.save_point === check.save_point) {
      const rounds = [...last.rounds, check];
      rows[rows.length - 1] = {
        ...check,
        id: last.id,
        index: last.index,
        created_at: last.created_at,
        number: last.number,
        passes: last.passes + check.passes,
        samples: last.samples + check.samples,
        rounds,
      };
    } else {
      rows.push({ ...check, number: rows.length + 1, rounds: [check] });
    }
  }
  return rows;
}
