import type { BenchmarkScore } from "@/api/generated";
import { BENCHMARK_METHOD_LABEL } from "@/components/status/status-tones";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatInteger, formatPercent, formatSeconds, formatUsd } from "@/lib/format";

type BenchmarkTableProps = { scores: readonly BenchmarkScore[] };

export function BenchmarkTable({ scores }: BenchmarkTableProps) {
  return (
    <div className="rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Method</TableHead>
            <TableHead className="text-right">Runs</TableHead>
            <TableHead className="text-right">Exact step</TableHead>
            <TableHead className="text-right">Within one step</TableHead>
            <TableHead className="text-right">Proven by replay</TableHead>
            <TableHead className="text-right">Mean cost</TableHead>
            <TableHead className="text-right">Mean time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {scores.map((score) => (
            <TableRow key={score.method}>
              <TableCell className="font-medium">{BENCHMARK_METHOD_LABEL[score.method]}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatInteger(score.runs_scored)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatPercent(score.exact_accuracy)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatPercent(score.within_one_accuracy)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {score.verified_rate === null ? "No proof" : formatPercent(score.verified_rate)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatUsd(score.mean_cost_usd)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatSeconds(score.mean_seconds)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
