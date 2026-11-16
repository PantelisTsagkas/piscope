"use client";

import { Play } from "lucide-react";
import { useState } from "react";

import { AutocorrelationChart, parseLagDetails } from "@/components/charts/autocorrelation-chart";
import { CountsComparisonChart } from "@/components/charts/counts-comparison-chart";
import { SimulationChart } from "@/components/charts/simulation-chart";
import { Field, NativeSelect } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel, Stat } from "@/components/shared/panel";
import { describeRange } from "@/components/shared/range-controls";
import { EmptyState, ErrorState, RowsSkeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUrlState } from "@/hooks/use-url-state";
import { useDatasetInfo, useRunComparison, useRunStatistics } from "@/lib/api/hooks";
import type { CompareResponse, DatasetInfo, StatisticsResponse } from "@/lib/api/types";
import {
  formatInteger,
  formatMilliseconds,
  formatPercent,
  formatPValue,
  formatStatistic,
} from "@/lib/format";
import { parseNonNegativeInteger, parsePositiveInteger } from "@/lib/params";

import { TestResultCard } from "./test-result-card";
import {
  parseTestKeys,
  TestOptions,
  testOptionsValid,
  type TestOptionValues,
} from "./test-options";

/** Largest seed a browser can send without losing precision; the API enforces the same cap. */
const MAX_SEED = Number.MAX_SAFE_INTEGER;

export function LabView() {
  const { searchParams, update } = useUrlState();
  const dataset = useDatasetInfo();
  const tab = searchParams.get("tab") === "compare" ? "compare" : "tests";

  return (
    <>
      <PageHeader
        title="Statistical Lab"
        description="Test a range of digits against a model of independent, equally likely digits, and compare it with simulated random sequences."
      />
      <Note>
        A result that is compatible with the model does not show that pi is random or normal. The
        normality of pi is an open problem, and no test on finitely many digits can settle it.
      </Note>
      {dataset.error ? (
        <ErrorState error={dataset.error} onRetry={() => void dataset.refetch()} />
      ) : !dataset.data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <Tabs
          value={tab}
          onValueChange={(value) => update({ tab: value === "tests" ? null : value })}
        >
          <TabsList>
            <TabsTrigger value="tests">Test battery</TabsTrigger>
            <TabsTrigger value="compare">Random comparison</TabsTrigger>
          </TabsList>
          <TabsContent value="tests" className="mt-4 flex flex-col gap-6">
            <BatteryTab info={dataset.data} searchParams={searchParams} />
          </TabsContent>
          <TabsContent value="compare" className="mt-4 flex flex-col gap-6">
            <CompareTab info={dataset.data} searchParams={searchParams} />
          </TabsContent>
        </Tabs>
      )}
    </>
  );
}

interface TabProps {
  info: DatasetInfo;
  searchParams: URLSearchParams;
}

function initialOptions(searchParams: URLSearchParams): TestOptionValues {
  return {
    tests: parseTestKeys(searchParams.get("tests")),
    maxLag: searchParams.get("max_lag") ?? "20",
    ngramLength: searchParams.get("ngram_length") ?? "2",
    runsDichotomy: searchParams.get("runs_dichotomy") === "parity" ? "parity" : "high_low",
  };
}

/** Start and count fields validated against the dataset and a per-request limit. */
function validateRange(startText: string, countText: string, total: number, limit: number) {
  const start = parsePositiveInteger(startText);
  const count = parsePositiveInteger(countText);
  let startError: string | null = null;
  let countError: string | null = null;
  if (start === null) startError = "Enter a whole number of 1 or more.";
  else if (start > total) startError = `The last position is ${formatInteger(total)}.`;
  if (count === null) countError = "Enter a whole number of 1 or more.";
  else if (count > limit) countError = `At most ${formatInteger(limit)} digits.`;
  else if (start !== null && startError === null && count > total - start + 1) {
    countError = `Only ${formatInteger(total - start + 1)} digits remain from that position.`;
  }
  return { start, count, startError, countError };
}

function BatteryTab({ info, searchParams }: TabProps) {
  const limit = info.limits.max_statistics_digits ?? info.total_digits;
  const limits = {
    maxLag: info.limits.max_autocorrelation_lag ?? 100,
    maxNgramLength: info.limits.max_ngram_length ?? 6,
  };
  const [startText, setStartText] = useState(searchParams.get("start") ?? "1");
  const [countText, setCountText] = useState(
    searchParams.get("count") ?? String(Math.min(info.total_digits, limit)),
  );
  const [options, setOptions] = useState(() => initialOptions(searchParams));
  const [correction, setCorrection] = useState<"holm" | "bonferroni">(
    searchParams.get("correction") === "bonferroni" ? "bonferroni" : "holm",
  );
  const run = useRunStatistics();

  const range = validateRange(startText, countText, info.total_digits, limit);
  const valid =
    range.startError === null && range.countError === null && testOptionsValid(options, limits);

  return (
    <>
      <Panel
        title="Test battery"
        description="Runs only when you ask. Every run is recorded under Experiments."
      >
        <form
          aria-label="Test battery"
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid || range.start === null || range.count === null) return;
            run.mutate({
              start: range.start,
              count: range.count,
              tests: options.tests,
              max_lag: parsePositiveInteger(options.maxLag) ?? 20,
              ngram_length: parsePositiveInteger(options.ngramLength) ?? 2,
              runs_dichotomy: options.runsDichotomy,
              correction,
            });
          }}
        >
          <div className="flex flex-wrap items-start gap-3">
            <Field
              id="battery-start"
              label="Start position"
              error={range.startError}
              className="w-36"
            >
              <Input
                id="battery-start"
                inputMode="numeric"
                value={startText}
                onChange={(event) => setStartText(event.target.value)}
                aria-invalid={range.startError !== null}
                className="font-mono"
              />
            </Field>
            <Field id="battery-count" label="Digits" error={range.countError} className="w-36">
              <Input
                id="battery-count"
                inputMode="numeric"
                value={countText}
                onChange={(event) => setCountText(event.target.value)}
                aria-invalid={range.countError !== null}
                className="font-mono"
              />
            </Field>
            <Field
              id="battery-correction"
              label="Multiple-testing correction"
              hint="Applied across the tests in this run."
              className="w-64"
            >
              <NativeSelect
                id="battery-correction"
                value={correction}
                onChange={(event) => setCorrection(event.target.value as "holm" | "bonferroni")}
              >
                <option value="holm">Holm (step-down)</option>
                <option value="bonferroni">Bonferroni</option>
              </NativeSelect>
            </Field>
          </div>
          <TestOptions idPrefix="battery" values={options} limits={limits} onChange={setOptions} />
          <Button type="submit" disabled={!valid || run.isPending} className="self-start">
            <Play aria-hidden /> {run.isPending ? "Running tests" : "Run tests"}
          </Button>
        </form>
      </Panel>

      {run.isPending ? (
        <Panel title="Results" description="Running tests">
          <RowsSkeleton rows={6} />
        </Panel>
      ) : run.error ? (
        <ErrorState error={run.error} />
      ) : run.data ? (
        <BatteryResults result={run.data} />
      ) : (
        <EmptyState title="No tests run yet">
          <p>
            Choose a range and the tests to apply, then run them. Deciding what to test before
            looking at the digits keeps the p-values meaningful.
          </p>
        </EmptyState>
      )}
    </>
  );
}

function BatteryResults({ result }: { result: StatisticsResponse }) {
  return (
    <section
      aria-label="Test results"
      className="flex flex-col gap-4"
      data-testid="battery-results"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Digits tested"
          accent="cyan"
          value={formatInteger(result.sample_size)}
          detail={describeRange(result.range_start, result.range_end)}
        />
        <Stat
          label="Procedures"
          accent="purple"
          value={result.results.length}
          detail={`${result.family_size} with a p-value`}
        />
        <Stat
          label="Correction"
          accent="blue"
          value={result.correction}
          detail={`across ${result.family_size} p-value${result.family_size === 1 ? "" : "s"}`}
        />
        <Stat
          label="Compute time"
          accent="blue"
          value={formatMilliseconds(result.elapsed_ms)}
          detail="on the server"
        />
      </div>
      <Note>{result.multiple_testing_note}</Note>
      {result.results.map((item) => {
        if (item.key !== "autocorrelation") return <TestResultCard key={item.key} result={item} />;
        const { lags, band } = parseLagDetails(item.details);
        return (
          <TestResultCard key={item.key} result={item}>
            {lags.length > 0 ? <AutocorrelationChart lags={lags} band={band} /> : null}
          </TestResultCard>
        );
      })}
      <Note>{result.scope_note}</Note>
    </section>
  );
}

function CompareTab({ info, searchParams }: TabProps) {
  const perSequence = Math.min(
    info.limits.max_random_digits ?? info.total_digits,
    info.limits.max_statistics_digits ?? info.total_digits,
  );
  const maxSimulations = info.limits.max_simulations ?? 200;
  const maxTotal = info.limits.max_simulated_total_digits ?? Number.MAX_SAFE_INTEGER;
  const limits = {
    maxLag: info.limits.max_autocorrelation_lag ?? 100,
    maxNgramLength: info.limits.max_ngram_length ?? 6,
  };

  const [startText, setStartText] = useState(searchParams.get("start") ?? "1");
  const [countText, setCountText] = useState(
    searchParams.get("count") ?? String(Math.min(100_000, info.total_digits, perSequence)),
  );
  const [simulationsText, setSimulationsText] = useState(searchParams.get("simulations") ?? "20");
  const [seedText, setSeedText] = useState(searchParams.get("seed") ?? "");
  const [options, setOptions] = useState(() => initialOptions(searchParams));
  const run = useRunComparison();

  const range = validateRange(startText, countText, info.total_digits, perSequence);
  let countError = range.countError;
  if (countError === null && range.count !== null && range.count < 10) {
    countError = "At least 10 digits.";
  }
  const simulations = parsePositiveInteger(simulationsText);
  let simulationsError: string | null = null;
  if (simulations === null) simulationsError = "Enter a whole number of 1 or more.";
  else if (simulations > maxSimulations) simulationsError = `At most ${maxSimulations}.`;
  else if (range.count !== null && simulations * range.count > maxTotal) {
    simulationsError = `At most ${formatInteger(maxTotal)} simulated digits in total.`;
  }
  const seed = seedText.trim() === "" ? null : parseNonNegativeInteger(seedText);
  let seedError: string | null = null;
  if (seedText.trim() !== "" && seed === null) {
    seedError = `Enter a whole number from 0 to ${formatInteger(MAX_SEED)}.`;
  }
  const valid =
    range.startError === null &&
    countError === null &&
    simulationsError === null &&
    seedError === null &&
    testOptionsValid(options, limits);

  return (
    <>
      <Panel
        title="Random comparison"
        description="Generates pseudo-random digit sequences of the same length and computes the same statistics on them."
      >
        <form
          aria-label="Random comparison"
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid || range.start === null || range.count === null || simulations === null)
              return;
            run.mutate({
              start: range.start,
              count: range.count,
              seed,
              simulations,
              tests: options.tests,
              max_lag: parsePositiveInteger(options.maxLag) ?? 20,
              ngram_length: parsePositiveInteger(options.ngramLength) ?? 2,
              runs_dichotomy: options.runsDichotomy,
            });
          }}
        >
          <div className="flex flex-wrap items-start gap-3">
            <Field
              id="compare-start"
              label="Start position"
              error={range.startError}
              className="w-36"
            >
              <Input
                id="compare-start"
                inputMode="numeric"
                value={startText}
                onChange={(event) => setStartText(event.target.value)}
                aria-invalid={range.startError !== null}
                className="font-mono"
              />
            </Field>
            <Field
              id="compare-count"
              label="Digits per sequence"
              error={countError}
              className="w-40"
            >
              <Input
                id="compare-count"
                inputMode="numeric"
                value={countText}
                onChange={(event) => setCountText(event.target.value)}
                aria-invalid={countError !== null}
                className="font-mono"
              />
            </Field>
            <Field
              id="compare-simulations"
              label="Simulated sequences"
              error={simulationsError}
              className="w-40"
            >
              <Input
                id="compare-simulations"
                inputMode="numeric"
                value={simulationsText}
                onChange={(event) => setSimulationsText(event.target.value)}
                aria-invalid={simulationsError !== null}
                className="font-mono"
              />
            </Field>
            <Field
              id="compare-seed"
              label="Seed"
              hint="Optional. Leave empty and one is chosen and reported."
              error={seedError}
              className="w-56"
            >
              <Input
                id="compare-seed"
                inputMode="numeric"
                placeholder="chosen automatically"
                value={seedText}
                onChange={(event) => setSeedText(event.target.value)}
                aria-invalid={seedError !== null}
                className="font-mono"
              />
            </Field>
          </div>
          <TestOptions idPrefix="compare" values={options} limits={limits} onChange={setOptions} />
          <Button type="submit" disabled={!valid || run.isPending} className="self-start">
            <Play aria-hidden /> {run.isPending ? "Simulating" : "Run comparison"}
          </Button>
        </form>
      </Panel>

      {run.isPending ? (
        <Panel title="Results" description="Simulating sequences">
          <RowsSkeleton rows={6} />
        </Panel>
      ) : run.error ? (
        <ErrorState error={run.error} />
      ) : run.data ? (
        <CompareResults
          result={run.data}
          onReuseSeed={() => setSeedText(String(run.data.source.seed))}
        />
      ) : (
        <EmptyState title="No comparison run yet">
          <p>
            The simulated sequences show how much each statistic varies by chance alone, which is
            the context needed to judge pi&apos;s value.
          </p>
        </EmptyState>
      )}
    </>
  );
}

function CompareResults({
  result,
  onReuseSeed,
}: {
  result: CompareResponse;
  onReuseSeed: () => void;
}) {
  return (
    <section
      aria-label="Comparison results"
      className="flex flex-col gap-6"
      data-testid="compare-results"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Digits per sequence"
          accent="cyan"
          value={formatInteger(result.length)}
          detail={describeRange(result.range_start, result.range_end)}
        />
        <Stat
          label="Simulated sequences"
          accent="purple"
          value={formatInteger(result.simulations)}
          detail={result.source.bit_generator}
        />
        <Stat
          label="Seed"
          accent="blue"
          testId="compare-seed-used"
          value={String(result.source.seed)}
          detail="reuse it to repeat this run exactly"
        />
        <Stat
          label="Compute time"
          accent="blue"
          value={formatMilliseconds(result.elapsed_ms)}
          detail="on the server"
        />
      </div>
      <Note>{result.note}</Note>

      <Panel
        title="Pi among the simulations"
        description="Each dot is one simulated sequence. The diamond is the chosen range of pi."
      >
        <ul className="flex flex-col divide-y">
          {result.statistics.map((statistic) => (
            <li
              key={statistic.key}
              className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0"
              data-testid={`simulated-${statistic.key}`}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <h3 className="font-mono text-sm">{statistic.name}</h3>
                <p className="text-xs text-muted-foreground">
                  Pi:{" "}
                  <span className="font-mono text-foreground">
                    {formatStatistic(statistic.observed)}
                  </span>{" "}
                  {statistic.statistic_name}. Simulated mean{" "}
                  <span className="font-mono text-foreground">
                    {formatStatistic(statistic.simulated_mean)}
                  </span>
                  , sd{" "}
                  <span className="font-mono text-foreground">
                    {formatStatistic(statistic.simulated_std)}
                  </span>
                  .
                </p>
              </div>
              <SimulationChart statistic={statistic} />
              <p className="text-xs text-muted-foreground">
                {formatPercent(statistic.fraction_at_or_below, 0)} of the simulated sequences have a
                value at or below pi&apos;s. This is a description of where pi falls, not a p-value.
              </p>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Digit counts" description="Pi beside the first simulated sequence.">
          <CountsComparisonChart piCounts={result.pi_counts} randomCounts={result.random_counts} />
        </Panel>
        <Panel title="Same tests, side by side" description="Pi and the first simulated sequence.">
          <Table data-testid="compare-table">
            <TableHeader>
              <TableRow>
                <TableHead className="font-mono">Test</TableHead>
                <TableHead className="text-right font-mono">Pi statistic</TableHead>
                <TableHead className="text-right font-mono">Pi p-value</TableHead>
                <TableHead className="text-right font-mono">Simulated statistic</TableHead>
                <TableHead className="text-right font-mono">Simulated p-value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.pi_results.map((pi, index) => {
                const random = result.random_results[index];
                return (
                  <TableRow key={pi.key}>
                    <TableCell className="whitespace-normal">{pi.name}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatStatistic(pi.statistic)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {formatPValue(pi.p_value)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {random ? formatStatistic(random.statistic) : "n/a"}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {random ? formatPValue(random.p_value) : "n/a"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <Note>
            p-values here are unadjusted. A p-value is the chance of a statistic at least this
            extreme if the model were true, not the chance that the model is true.
          </Note>
        </Panel>
      </div>

      <Panel
        title="Reproducibility"
        description="Everything needed to regenerate the simulated sequences."
        action={
          <Button variant="outline" size="sm" onClick={onReuseSeed}>
            Use this seed again
          </Button>
        }
      >
        <dl className="grid gap-x-6 gap-y-3 font-mono text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground uppercase">Seed</dt>
            <dd>{result.source.seed}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground uppercase">Bit generator</dt>
            <dd>{result.source.bit_generator}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground uppercase">NumPy version</dt>
            <dd>{result.source.numpy_version}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-muted-foreground uppercase">Method</dt>
            <dd className="break-all">{result.source.method}</dd>
          </div>
        </dl>
      </Panel>
    </section>
  );
}
