"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { DeviationChart } from "@/components/charts/deviation-chart";
import { FrequencyChart } from "@/components/charts/frequency-chart";
import { RunLengthChart } from "@/components/charts/run-length-chart";
import { ZHeatmap, type HeatCell } from "@/components/charts/z-heatmap";
import { Field, NativeSelect } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel, Stat } from "@/components/shared/panel";
import { describeRange, RangeControls } from "@/components/shared/range-controls";
import { ChartSkeleton, ErrorState, RowsSkeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAnalysisRange, type AnalysisRange } from "@/hooks/use-analysis-range";
import { useFrequency, useNgrams, useRuns, useWindows } from "@/lib/api/hooks";
import type { NgramRow, NgramSort } from "@/lib/api/types";
import { formatDecimal, formatInteger, formatPercent, formatSigned } from "@/lib/format";

import { TestResultCard } from "./test-result-card";

const NGRAM_PAGE_SIZE = 25;
const WINDOW_CHOICES = [10, 20, 50, 100, 200];
const DIGIT_LABELS = Array.from({ length: 10 }, (_, digit) => String(digit));

export function FrequencyView() {
  // N-grams, windows and runs hold the range in memory, so the page uses that limit.
  const { range, setRange, dataset } = useAnalysisRange("max_statistics_digits");

  if (dataset.error) {
    return (
      <>
        <Header />
        <ErrorState error={dataset.error} onRetry={() => void dataset.refetch()} />
      </>
    );
  }

  return (
    <>
      <Header />
      <Panel title="Analysis range" description="All sections below use this range.">
        {range ? (
          <RangeControls range={range} onChange={setRange} />
        ) : (
          <Skeleton className="h-14 w-full max-w-lg" />
        )}
      </Panel>
      {range ? (
        <>
          <DigitFrequencySection range={range} />
          <NgramSection
            key={`ngrams-${range.start}-${range.count}`}
            range={range}
            maxLength={dataset.data?.limits.max_ngram_length ?? 6}
          />
          <WindowSection range={range} maxWindows={dataset.data?.limits.max_windows ?? 200} />
          <RunsSection range={range} />
        </>
      ) : (
        <ChartSkeleton />
      )}
    </>
  );
}

function Header() {
  return (
    <PageHeader
      title="Frequency Analysis"
      description="How often digits and digit sequences occur, compared with what independent, equally likely digits would give."
    />
  );
}

function DigitFrequencySection({ range }: { range: AnalysisRange }) {
  const frequency = useFrequency({ start: range.start, count: range.count });
  const data = frequency.data;

  if (frequency.error) {
    return <ErrorState error={frequency.error} onRetry={() => void frequency.refetch()} />;
  }
  return (
    <>
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel
          title="Digit counts"
          description={data ? describeRange(data.range_start, data.range_end) : "Counting digits"}
        >
          {data ? <FrequencyChart digits={data.digits} /> : <ChartSkeleton />}
        </Panel>
        <Panel
          title="Deviation from expected"
          description="Each digit's count minus the expected count, in standard deviations."
        >
          {data ? <DeviationChart digits={data.digits} /> : <ChartSkeleton />}
        </Panel>
      </div>

      <Panel
        title="Frequency table"
        description={
          data
            ? `Expected relative frequency ${formatPercent(data.expected_relative_frequency, 0)} per digit.`
            : "Counting digits"
        }
      >
        {data ? (
          <>
            <Table data-testid="frequency-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="font-mono">Digit</TableHead>
                  <TableHead className="text-right font-mono">Count</TableHead>
                  <TableHead className="text-right font-mono">Relative frequency</TableHead>
                  <TableHead className="text-right font-mono">Expected count</TableHead>
                  <TableHead className="text-right font-mono">Deviation</TableHead>
                  <TableHead className="text-right font-mono">Deviation (sd)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.digits.map((item) => (
                  <TableRow key={item.digit} data-testid={`frequency-row-${item.digit}`}>
                    <TableCell className="font-mono text-cyan">{item.digit}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatInteger(item.count)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatPercent(item.relative_frequency, 4)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatDecimal(item.expected_count, 1)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatSigned(item.deviation, 1)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatSigned(item.standardized_deviation)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Note>{data.note}</Note>
          </>
        ) : (
          <RowsSkeleton rows={10} />
        )}
      </Panel>
    </>
  );
}

function NgramSection({ range, maxLength }: { range: AnalysisRange; maxLength: number }) {
  const router = useRouter();
  const [length, setLength] = useState(2);
  const [sort, setSort] = useState<NgramSort>("count_desc");
  const [offset, setOffset] = useState(0);

  const base = { start: range.start, count: range.count };
  const table = useNgrams({ ...base, n: length, sort, offset, limit: NGRAM_PAGE_SIZE });
  // The 10 x 10 pair grid needs every pair's deviation, in numeric order.
  const pairs = useNgrams(
    length === 2 ? { ...base, n: 2, sort: "ngram", offset: 0, limit: 100 } : null,
  );
  const data = table.data;

  const pairCells = useMemo<HeatCell[]>(
    () =>
      (pairs.data?.rows ?? []).map((row) => ({
        x: Number(row.ngram[1]),
        y: Number(row.ngram[0]),
        z: row.standardized_deviation,
        lines: [
          `<b>Pair ${row.ngram}</b>`,
          `Count: ${formatInteger(row.count)}`,
          `Deviation: ${formatSigned(row.deviation, 1)} (${formatSigned(row.standardized_deviation)} sd)`,
        ],
      })),
    [pairs.data],
  );

  return (
    <Panel
      title="N-gram analysis"
      description="Counts of every sequence of n consecutive digits."
      action={
        <div className="flex flex-wrap gap-3">
          <Field id="ngram-length" label="Length (n)" className="w-28">
            <NativeSelect
              id="ngram-length"
              value={length}
              onChange={(event) => {
                setLength(Number(event.target.value));
                setOffset(0);
              }}
            >
              {Array.from({ length: maxLength }, (_, index) => index + 1).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <Field id="ngram-sort" label="Order" className="w-44">
            <NativeSelect
              id="ngram-sort"
              value={sort}
              onChange={(event) => {
                setSort(event.target.value as NgramSort);
                setOffset(0);
              }}
            >
              <option value="count_desc">Most common first</option>
              <option value="count_asc">Least common first</option>
              <option value="ngram">Numeric order</option>
            </NativeSelect>
          </Field>
        </div>
      }
    >
      {table.error ? (
        <ErrorState error={table.error} onRetry={() => void table.refetch()} />
      ) : data ? (
        <>
          <section aria-label="N-gram summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Sequences counted"
              value={formatInteger(data.windows)}
              detail="one per position"
            />
            <Stat
              label="Possible sequences"
              value={formatInteger(data.possible)}
              detail={`10 to the power ${data.length}`}
            />
            <Stat
              label="Never occur"
              testId="ngram-missing"
              value={formatInteger(data.missing)}
              detail={`${formatInteger(data.observed_distinct)} distinct sequences occur`}
            />
            <Stat
              label="Expected count each"
              value={formatDecimal(data.expected_count, data.expected_count < 100 ? 2 : 1)}
              detail="under a uniform model"
            />
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-mono text-xs text-muted-foreground uppercase">
                  Rows {formatInteger(data.offset + 1)} to{" "}
                  {formatInteger(data.offset + data.rows.length)} of{" "}
                  {formatInteger(data.total_rows)}
                </h3>
                <nav aria-label="N-gram pages" className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - NGRAM_PAGE_SIZE))}
                  >
                    <ChevronLeft aria-hidden /> Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!data.has_more}
                    onClick={() => setOffset(offset + NGRAM_PAGE_SIZE)}
                  >
                    Next <ChevronRight aria-hidden />
                  </Button>
                </nav>
              </div>
              <NgramTable rows={data.rows} firstRank={data.offset + 1} />
            </div>

            <div className="flex min-w-0 flex-col gap-3">
              {length === 2 ? (
                <>
                  <h3 className="font-mono text-xs text-muted-foreground uppercase">
                    Pair grid: first digit by second digit
                  </h3>
                  {pairs.data ? (
                    <ZHeatmap
                      cells={pairCells}
                      xLabels={DIGIT_LABELS}
                      yLabels={DIGIT_LABELS}
                      xName="second digit"
                      yName="first digit"
                      className="h-96"
                      label="Heatmap of the 100 two-digit sequences, coloured by how far each count is from the expected count. Select numeric order in the table for the same values."
                      onCellClick={(cell) => router.push(`/search?q=${cell.y}${cell.x}`)}
                    />
                  ) : (
                    <ChartSkeleton className="h-96" />
                  )}
                  <p className="text-xs text-muted-foreground">
                    Click a cell to search for that pair.
                  </p>
                </>
              ) : (
                <>
                  <h3 className="font-mono text-xs text-muted-foreground uppercase">Extremes</h3>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <ExtremeList title="Most common" rows={data.most_common} />
                    <ExtremeList title="Least common" rows={data.least_common} />
                  </div>
                </>
              )}
            </div>
          </div>

          <Note>{data.note}</Note>
          {data.block_test ? <TestResultCard result={data.block_test} /> : null}
        </>
      ) : (
        <RowsSkeleton rows={8} />
      )}
    </Panel>
  );
}

function NgramTable({ rows, firstRank }: { rows: NgramRow[]; firstRank: number }) {
  return (
    <Table data-testid="ngram-table">
      <TableHeader>
        <TableRow>
          <TableHead className="w-16 font-mono">Row</TableHead>
          <TableHead className="font-mono">Sequence</TableHead>
          <TableHead className="text-right font-mono">Count</TableHead>
          <TableHead className="text-right font-mono">Deviation</TableHead>
          <TableHead className="text-right font-mono">Deviation (sd)</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, index) => (
          <TableRow key={row.ngram}>
            <TableCell className="font-mono text-muted-foreground tabular-nums">
              {formatInteger(firstRank + index)}
            </TableCell>
            <TableCell className="font-mono">
              <Link
                href={`/search?q=${row.ngram}`}
                className="text-cyan underline-offset-4 hover:underline"
              >
                {row.ngram}
              </Link>
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {formatInteger(row.count)}
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {formatSigned(row.deviation, 1)}
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {formatSigned(row.standardized_deviation)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ExtremeList({ title, rows }: { title: string; rows: NgramRow[] }) {
  return (
    <div className="flex flex-col gap-2 border p-3">
      <span className="font-mono text-xs">{title}</span>
      <ol className="flex flex-col gap-1">
        {rows.map((row) => (
          <li key={row.ngram} className="flex justify-between gap-3 font-mono text-xs tabular-nums">
            <Link
              href={`/search?q=${row.ngram}`}
              className="text-cyan underline-offset-4 hover:underline"
            >
              {row.ngram}
            </Link>
            <span className="text-muted-foreground">{formatInteger(row.count)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function WindowSection({ range, maxWindows }: { range: AnalysisRange; maxWindows: number }) {
  const choices = WINDOW_CHOICES.filter((value) => value <= maxWindows && value <= range.count);
  const [requested, setRequested] = useState(20);
  const windowCount = choices.includes(requested) ? requested : (choices.at(-1) ?? 1);
  const windows = useWindows({ start: range.start, count: range.count, windows: windowCount });
  const data = windows.data;

  const cells = useMemo<HeatCell[]>(
    () =>
      (data?.rows ?? []).flatMap((row) =>
        row.standardized.map((z, digit) => ({
          x: row.index,
          y: digit,
          z,
          lines: [
            `<b>Digit ${digit}, window ${row.index + 1}</b>`,
            `Positions ${formatInteger(row.start)} to ${formatInteger(row.end)}`,
            `Count: ${formatInteger(row.counts[digit] ?? 0)}`,
            `Deviation: ${formatSigned(z)} sd`,
          ],
        })),
      ),
    [data],
  );

  return (
    <Panel
      title="Concentration by window"
      description="The range split into equal windows. Each cell shows how far one digit's count in one window is from expected."
      action={
        <Field id="window-count" label="Windows" className="w-28">
          <NativeSelect
            id="window-count"
            value={windowCount}
            onChange={(event) => setRequested(Number(event.target.value))}
          >
            {choices.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </NativeSelect>
        </Field>
      }
    >
      {windows.error ? (
        <ErrorState error={windows.error} onRetry={() => void windows.refetch()} />
      ) : data ? (
        <>
          <section aria-label="Window summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Window size"
              value={formatInteger(data.window_size)}
              detail={`${data.window_count} windows`}
            />
            <Stat
              label="Cells beyond 2 sd"
              testId="cells-beyond-two"
              value={`${formatInteger(data.cells_beyond_two)} of ${formatInteger(data.cells)}`}
              detail={`about ${formatDecimal(data.expected_cells_beyond_two, 1)} expected by chance`}
            />
            <Stat
              label="Cells beyond 3 sd"
              value={`${formatInteger(data.cells_beyond_three)} of ${formatInteger(data.cells)}`}
              detail={`about ${formatDecimal(data.expected_cells_beyond_three, 2)} expected by chance`}
            />
            <Stat
              label="Largest deviation"
              value={`${formatDecimal(data.max_abs_z)} sd`}
              detail="in absolute value"
            />
          </section>
          <ZHeatmap
            cells={cells}
            xLabels={data.rows.map((row) => String(row.index + 1))}
            yLabels={DIGIT_LABELS}
            xName="window"
            yName="digit"
            className="h-96"
            label="Heatmap of digit counts by window, coloured by deviation from the expected count. The summary above gives the number of extreme cells and how many are expected by chance."
          />
          {data.approximation_reliable ? null : (
            <Note className="border-amber/60 bg-amber/5">
              These windows hold fewer than 50 digits each, so the standardized deviations are
              unreliable. Use fewer windows or a longer range.
            </Note>
          )}
          <Note>{data.note}</Note>
        </>
      ) : (
        <ChartSkeleton className="h-96" />
      )}
    </Panel>
  );
}

function RunsSection({ range }: { range: AnalysisRange }) {
  const runs = useRuns({ start: range.start, count: range.count, top: 10 });
  const data = runs.data;
  return (
    <Panel
      title="Repeated digits"
      description="Runs: maximal blocks of one digit repeated, such as 999999."
    >
      {runs.error ? (
        <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
      ) : data ? (
        <>
          <div className="grid gap-6 xl:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-3">
              <h3 className="font-mono text-xs text-muted-foreground uppercase">Longest runs</h3>
              <Table data-testid="longest-runs">
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-mono">Run</TableHead>
                    <TableHead className="text-right font-mono">Length</TableHead>
                    <TableHead className="text-right font-mono">Position</TableHead>
                    <TableHead className="text-right font-mono">Digits</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.longest.map((run) => (
                    <TableRow key={run.position}>
                      <TableCell className="font-mono text-cyan">
                        {String(run.digit).repeat(run.length)}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums">
                        {run.length}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums">
                        {formatInteger(run.position)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/explorer?start=${Math.max(1, run.position - 100)}&select=${run.position}&length=${run.length}`}
                          className="text-primary underline-offset-4 hover:underline"
                        >
                          View in explorer
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex min-w-0 flex-col gap-3">
              <h3 className="font-mono text-xs text-muted-foreground uppercase">Run lengths</h3>
              <RunLengthChart distribution={data.distribution} />
            </div>
          </div>
          <Note>{data.note}</Note>
        </>
      ) : (
        <RowsSkeleton rows={6} />
      )}
    </Panel>
  );
}
