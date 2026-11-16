"use client";

import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ExperimentList } from "@/components/analysis/experiment-list";
import { FrequencyChart } from "@/components/charts/frequency-chart";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel, Stat } from "@/components/shared/panel";
import { describeRange, RangeControls } from "@/components/shared/range-controls";
import { ChartSkeleton, EmptyState, ErrorState, RowsSkeleton } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalysisRange } from "@/hooks/use-analysis-range";
import { useExperiments, useFrequency, useObservations } from "@/lib/api/hooks";
import type { Observation } from "@/lib/api/types";
import { formatInteger, formatPercent } from "@/lib/format";
import { sanitizePattern } from "@/lib/params";

const QUICK_PATTERNS = ["314159", "123456", "000000", "271828"];

export function OverviewView() {
  // Observations hold the range in memory, so the dashboard uses the tighter limit.
  const { range, setRange, dataset } = useAnalysisRange("max_statistics_digits");
  const params = range ? { start: range.start, count: range.count } : null;
  const frequency = useFrequency(params);
  const observations = useObservations(params);
  const experiments = useExperiments(6);

  if (dataset.error) {
    return (
      <>
        <Header />
        <ErrorState error={dataset.error} onRetry={() => void dataset.refetch()} />
      </>
    );
  }

  const info = dataset.data;
  const top = frequency.data;

  return (
    <>
      <Header />

      <section aria-label="Dataset status" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Digits available"
          accent="cyan"
          testId="stat-total-digits"
          value={info ? formatInteger(info.total_digits) : <Skeleton className="h-7 w-32" />}
          detail={
            info
              ? `${info.chunk_count} chunk${info.chunk_count === 1 ? "" : "s"}, ${
                  info.has_partial_chunk ? "last chunk partial" : "all complete"
                }`
              : "Loading dataset"
          }
        />
        <Stat
          label="Digits analysed"
          accent="purple"
          testId="stat-analysed-digits"
          value={range ? formatInteger(range.count) : <Skeleton className="h-7 w-32" />}
          detail={
            range ? `positions ${formatInteger(range.start)} to ${formatInteger(range.end)}` : " "
          }
        />
        <Stat
          label="Most frequent digit"
          accent="blue"
          testId="stat-most-frequent"
          value={top ? top.most_frequent.join(", ") : <Skeleton className="h-7 w-16" />}
          detail={top ? extremeDetail(top.digits, top.most_frequent[0]) : " "}
        />
        <Stat
          label="Least frequent digit"
          accent="blue"
          testId="stat-least-frequent"
          value={top ? top.least_frequent.join(", ") : <Skeleton className="h-7 w-16" />}
          detail={top ? extremeDetail(top.digits, top.least_frequent[0]) : " "}
        />
      </section>

      <Panel
        title="Analysis range"
        description="Every number on this page is computed from these digits when the page loads."
      >
        {range ? (
          <>
            <RangeControls range={range} onChange={setRange} />
            {range.limited ? (
              <Note>
                The dataset is larger than the server analyses in one request, so this view covers
                the first {formatInteger(range.count)} digits.
              </Note>
            ) : null}
          </>
        ) : (
          <Skeleton className="h-14 w-full max-w-lg" />
        )}
        {info ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="font-mono">
              {String(info.generator.algorithm ?? "unknown generator")}
            </Badge>
            {info.verifications.map((item) => (
              <Badge key={item.method} variant="outline" className="font-mono">
                verified: {item.method}
              </Badge>
            ))}
            <span>
              Position 1 is the first digit after the decimal point.{" "}
              <Link href="/about" className="text-primary underline-offset-4 hover:underline">
                Provenance and conventions
              </Link>
            </span>
          </div>
        ) : null}
      </Panel>

      <div className="grid gap-6 xl:grid-cols-5">
        <Panel
          title="Digit distribution"
          description={top ? describeRange(top.range_start, top.range_end) : "Counting digits"}
          className="xl:col-span-3"
          action={
            <Button asChild variant="ghost" size="sm">
              <Link
                href={range ? `/frequency?start=${range.start}&count=${range.count}` : "/frequency"}
              >
                Frequency analysis <ArrowRight aria-hidden />
              </Link>
            </Button>
          }
        >
          {frequency.error ? (
            <ErrorState error={frequency.error} onRetry={() => void frequency.refetch()} />
          ) : top ? (
            <FrequencyChart digits={top.digits} />
          ) : (
            <ChartSkeleton />
          )}
        </Panel>

        <Panel
          title="Quick search"
          description="Find any digit sequence in the stored digits."
          className="xl:col-span-2"
        >
          <QuickSearch />
        </Panel>
      </div>

      <Panel
        title="Observations"
        description="Facts computed from the analysed range. Descriptive unless marked as a test."
      >
        {observations.error ? (
          <ErrorState error={observations.error} onRetry={() => void observations.refetch()} />
        ) : observations.data ? (
          <>
            <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {observations.data.observations.map((item) => (
                <ObservationCard key={item.key} observation={item} />
              ))}
            </ul>
            <Note>{observations.data.caveat}</Note>
          </>
        ) : (
          <RowsSkeleton rows={4} />
        )}
      </Panel>

      <Panel
        title="Recent experiments"
        description="Searches, test runs and comparisons, newest first."
        action={
          <Button asChild variant="ghost" size="sm">
            <Link href="/experiments">
              All experiments <ArrowRight aria-hidden />
            </Link>
          </Button>
        }
      >
        {experiments.error ? (
          <ErrorState error={experiments.error} onRetry={() => void experiments.refetch()} />
        ) : experiments.data ? (
          experiments.data.experiments.length > 0 ? (
            <ExperimentList experiments={experiments.data.experiments} compact />
          ) : (
            <EmptyState title="No experiments yet">
              <p>Run a search or a statistical test and it will be recorded here.</p>
            </EmptyState>
          )
        ) : (
          <RowsSkeleton rows={3} />
        )}
      </Panel>
    </>
  );
}

function Header() {
  return (
    <PageHeader
      title="Overview"
      description="The decimal digits of pi, verified and ready to explore. Patterns shown here are observations about a finite range, not proofs."
    />
  );
}

function extremeDetail(
  digits: { digit: number; count: number; relative_frequency: number }[],
  digit: number | undefined,
): string {
  const item = digits.find((entry) => entry.digit === digit);
  if (!item) return " ";
  return `${formatInteger(item.count)} occurrences, ${formatPercent(item.relative_frequency)}`;
}

function ObservationCard({ observation }: { observation: Observation }) {
  const href =
    observation.position !== null && observation.position !== undefined
      ? `/explorer?start=${Math.max(1, observation.position - 100)}&select=${observation.position}${
          observation.length ? `&length=${observation.length}` : ""
        }`
      : null;
  return (
    <li className="flex flex-col gap-1.5 border p-3" data-testid={`observation-${observation.key}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {observation.title}
        </span>
        <Badge
          variant={observation.kind === "test" ? "secondary" : "outline"}
          className="font-mono"
        >
          {observation.kind}
        </Badge>
      </div>
      <span className="font-mono text-base font-medium break-all">{observation.value}</span>
      <p className="text-xs leading-relaxed text-muted-foreground">{observation.detail}</p>
      {href ? (
        <Link
          href={href}
          className="self-start text-xs text-primary underline-offset-4 hover:underline"
        >
          View in explorer
        </Link>
      ) : null}
    </li>
  );
}

function QuickSearch() {
  const router = useRouter();
  const [pattern, setPattern] = useState("");
  return (
    <div className="flex flex-col gap-4">
      <form
        role="search"
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (pattern) router.push(`/search?q=${pattern}`);
        }}
      >
        <Input
          aria-label="Digit sequence to search for"
          placeholder="e.g. 314159"
          inputMode="numeric"
          value={pattern}
          onChange={(event) => setPattern(sanitizePattern(event.target.value))}
          className="font-mono"
        />
        <Button type="submit" disabled={!pattern}>
          <Search aria-hidden /> Search
        </Button>
      </form>
      <div className="flex flex-col gap-2">
        <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          Try
        </span>
        <div className="flex flex-wrap gap-2">
          {QUICK_PATTERNS.map((item) => (
            <Button key={item} asChild variant="outline" size="sm" className="font-mono">
              <Link href={`/search?q=${item}`}>{item}</Link>
            </Button>
          ))}
        </div>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Any short sequence is expected to appear in a long run of digits. Finding one is not a sign
        of hidden meaning.
      </p>
    </div>
  );
}
