"use client";

import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { GapChart } from "@/components/charts/gap-chart";
import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel, Stat } from "@/components/shared/panel";
import { EmptyState, ErrorState, RowsSkeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useUrlState } from "@/hooks/use-url-state";
import { useDatasetInfo, useSearch } from "@/lib/api/hooks";
import type { SearchRequest, SearchResponse } from "@/lib/api/types";
import { formatDecimal, formatInteger, formatMilliseconds } from "@/lib/format";
import { parseNonNegativeInteger, parsePositiveInteger, sanitizePattern } from "@/lib/params";

const PAGE_SIZE = 100;
const EXAMPLES = ["314159", "123456", "000000", "999999"];

export function SearchView() {
  const { searchParams, update } = useUrlState();
  const dataset = useDatasetInfo();

  const pattern = sanitizePattern(searchParams.get("q") ?? "");
  const start = parsePositiveInteger(searchParams.get("start"));
  const end = parsePositiveInteger(searchParams.get("end"));
  const offset = parseNonNegativeInteger(searchParams.get("offset")) ?? 0;

  const request: SearchRequest | null =
    pattern && dataset.data
      ? { pattern, start: start ?? 1, end: end ?? null, offset, limit: PAGE_SIZE }
      : null;
  const search = useSearch(request);
  const result = search.data;

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

      <Panel
        title="Search"
        description="Digits only. Overlapping occurrences are all counted: 000 occurs twice in 0000."
      >
        <SearchForm
          key={`${pattern}-${start}-${end}`}
          pattern={pattern}
          start={start}
          end={end}
          total={dataset.data?.total_digits ?? null}
          maxLength={dataset.data?.limits.max_pattern_length ?? 1000}
          busy={search.isFetching}
          onSearch={(next) =>
            update(
              { q: next.pattern, start: next.start, end: next.end, offset: null },
              { push: true },
            )
          }
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            Examples
          </span>
          {EXAMPLES.map((example) => (
            <Button
              key={example}
              variant="outline"
              size="sm"
              className="font-mono"
              onClick={() =>
                update({ q: example, start: null, end: null, offset: null }, { push: true })
              }
            >
              {example}
            </Button>
          ))}
        </div>
      </Panel>

      {!pattern ? (
        <EmptyState title="Enter a sequence to search for">
          <p>
            Results show the first occurrence, the total count, every matching position and the
            distance between consecutive occurrences.
          </p>
        </EmptyState>
      ) : search.error ? (
        <ErrorState error={search.error} onRetry={() => void search.refetch()} />
      ) : result ? (
        <Results
          result={result}
          stale={search.isPlaceholderData}
          onPage={(nextOffset) => update({ offset: nextOffset === 0 ? null : nextOffset })}
        />
      ) : (
        <Panel title="Results" description="Searching">
          <RowsSkeleton rows={6} />
        </Panel>
      )}
    </>
  );
}

function Header() {
  return (
    <PageHeader
      title="Sequence Search"
      description="Find every occurrence of a digit sequence. Position 1 is the first digit after the decimal point."
    />
  );
}

function SearchForm({
  pattern,
  start,
  end,
  total,
  maxLength,
  busy,
  onSearch,
}: {
  pattern: string;
  start: number | null;
  end: number | null;
  total: number | null;
  maxLength: number;
  busy: boolean;
  onSearch: (next: { pattern: string; start: number | null; end: number | null }) => void;
}) {
  const [patternText, setPatternText] = useState(pattern);
  const [startText, setStartText] = useState(start === null ? "" : String(start));
  const [endText, setEndText] = useState(end === null ? "" : String(end));
  const [submitted, setSubmitted] = useState(false);

  const nextStart = startText.trim() === "" ? null : parsePositiveInteger(startText);
  const nextEnd = endText.trim() === "" ? null : parsePositiveInteger(endText);
  const firstPosition = nextStart ?? 1;
  const lastPosition = nextEnd ?? total;

  let patternError: string | null = null;
  if (patternText.length === 0) patternError = "Enter at least one digit.";
  else if (patternText.length > maxLength) {
    patternError = `Sequences can be at most ${formatInteger(maxLength)} digits long.`;
  }
  let startError: string | null = null;
  if (startText.trim() !== "" && nextStart === null)
    startError = "Enter a whole number of 1 or more.";
  else if (total !== null && firstPosition > total) {
    startError = `The last position is ${formatInteger(total)}.`;
  }
  let endError: string | null = null;
  if (endText.trim() !== "" && nextEnd === null) endError = "Enter a whole number of 1 or more.";
  else if (total !== null && nextEnd !== null && nextEnd > total) {
    endError = `The last position is ${formatInteger(total)}.`;
  } else if (lastPosition !== null && lastPosition < firstPosition) {
    endError = "The end must not be before the start.";
  }
  const valid = patternError === null && startError === null && endError === null;

  return (
    <form
      role="search"
      aria-label="Sequence search"
      className="flex flex-wrap items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        setSubmitted(true);
        if (valid) onSearch({ pattern: patternText, start: nextStart, end: nextEnd });
      }}
    >
      <Field
        id="search-pattern"
        label="Digit sequence"
        error={submitted || patternText.length > maxLength ? patternError : null}
        className="min-w-56 flex-1"
      >
        <Input
          id="search-pattern"
          inputMode="numeric"
          autoComplete="off"
          placeholder="e.g. 314159"
          value={patternText}
          onChange={(event) => setPatternText(sanitizePattern(event.target.value))}
          aria-invalid={submitted && patternError !== null}
          aria-describedby={patternError ? "search-pattern-error" : undefined}
          className="font-mono"
        />
      </Field>
      <Field id="search-start" label="From position" error={startError} className="w-36">
        <Input
          id="search-start"
          inputMode="numeric"
          placeholder="1"
          value={startText}
          onChange={(event) => setStartText(event.target.value)}
          aria-invalid={startError !== null}
          aria-describedby={startError ? "search-start-error" : undefined}
          className="font-mono"
        />
      </Field>
      <Field id="search-end" label="To position" error={endError} className="w-36">
        <Input
          id="search-end"
          inputMode="numeric"
          placeholder={total === null ? "last" : formatInteger(total)}
          value={endText}
          onChange={(event) => setEndText(event.target.value)}
          aria-invalid={endError !== null}
          aria-describedby={endError ? "search-end-error" : undefined}
          className="font-mono"
        />
      </Field>
      <div className="pt-[22px]">
        <Button type="submit" disabled={busy || startError !== null || endError !== null}>
          <Search aria-hidden /> {busy ? "Searching" : "Search"}
        </Button>
      </div>
    </form>
  );
}

function Results({
  result,
  stale,
  onPage,
}: {
  result: SearchResponse;
  stale: boolean;
  onPage: (offset: number) => void;
}) {
  const found = result.total_count > 0;
  const firstShown = result.offset + 1;
  const lastShown = result.offset + result.matches.length;

  return (
    <div
      className={stale ? "flex flex-col gap-6 opacity-60" : "flex flex-col gap-6"}
      aria-busy={stale}
    >
      <section aria-label="Search summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Occurrences"
          accent="cyan"
          testId="search-total"
          value={formatInteger(result.total_count)}
          detail={`about ${formatDecimal(result.expected_count, result.expected_count < 10 ? 3 : 1)} expected for uniform random digits`}
        />
        <Stat
          label="First occurrence"
          accent="purple"
          testId="search-first"
          value={result.first_position === null ? "none" : formatInteger(result.first_position)}
          detail={
            result.last_position !== null &&
            result.last_position !== undefined &&
            result.total_count > 1
              ? `last at ${formatInteger(result.last_position)}`
              : `in positions ${formatInteger(result.range_start)} to ${formatInteger(result.range_end)}`
          }
        />
        <Stat
          label="Mean gap"
          accent="blue"
          testId="search-mean-gap"
          value={result.gaps ? formatDecimal(result.gaps.mean, 1) : "n/a"}
          detail={
            result.gaps
              ? `min ${formatInteger(result.gaps.minimum)}, median ${formatDecimal(result.gaps.median, 1)}, max ${formatInteger(result.gaps.maximum)}`
              : "needs at least two occurrences"
          }
        />
        <Stat
          label="Search time"
          accent="blue"
          testId="search-time"
          value={formatMilliseconds(result.elapsed_ms)}
          detail={
            result.cached ? "scan time; this page came from the cache" : "time to scan the digits"
          }
        />
      </section>

      {!found ? (
        <EmptyState title={`${result.pattern} does not occur in this range`}>
          <p>
            Searched positions {formatInteger(result.range_start)} to{" "}
            {formatInteger(result.range_end)}. A sequence of {result.pattern_length} digits is
            expected about {formatDecimal(result.expected_count, 3)} times in a range this long, so
            an absence here says nothing about the rest of pi.
          </p>
        </EmptyState>
      ) : (
        <>
          <Panel
            title="Matching positions"
            description={`Showing ${formatInteger(firstShown)} to ${formatInteger(lastShown)} of ${formatInteger(result.pageable_count)}`}
            action={
              <nav aria-label="Result pages" className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={result.offset === 0}
                  onClick={() => onPage(Math.max(0, result.offset - result.limit))}
                >
                  <ChevronLeft aria-hidden /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!result.has_more}
                  onClick={() => onPage(result.offset + result.limit)}
                >
                  Next <ChevronRight aria-hidden />
                </Button>
              </nav>
            }
          >
            {result.positions_truncated ? (
              <Note>
                There are {formatInteger(result.total_count)} occurrences. The total is exact, but
                only the first {formatInteger(result.pageable_count)} positions are kept for paging.
              </Note>
            ) : null}
            <div className="max-h-[28rem] overflow-y-auto border">
              <Table data-testid="search-matches">
                <TableHeader className="sticky top-0 bg-card">
                  <TableRow>
                    <TableHead className="w-24 font-mono">#</TableHead>
                    <TableHead className="font-mono">Position</TableHead>
                    <TableHead className="font-mono">Gap from previous</TableHead>
                    <TableHead className="text-right font-mono">Digits</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.matches.map((match) => (
                    <TableRow key={match.index}>
                      <TableCell className="font-mono text-muted-foreground tabular-nums">
                        {formatInteger(match.index + 1)}
                      </TableCell>
                      <TableCell className="font-mono tabular-nums" data-testid="match-position">
                        {formatInteger(match.position)}
                      </TableCell>
                      <TableCell className="font-mono tabular-nums">
                        {match.gap_from_previous === null || match.gap_from_previous === undefined
                          ? "first"
                          : formatInteger(match.gap_from_previous)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/explorer?start=${Math.max(1, match.position - 100)}&select=${match.position}&length=${result.pattern_length}`}
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
          </Panel>

          {result.gaps ? (
            <Panel
              title="Distance between occurrences"
              description={`Gaps for the occurrences on this page. Independent uniform digits would give a mean gap of ${formatInteger(result.gaps.expected_mean)}.`}
            >
              <GapChart matches={result.matches} expectedMean={result.gaps.expected_mean} />
              <Note>
                Gaps vary widely by chance. The expected count and mean gap are reference values for
                comparison, not a statistical test.
              </Note>
            </Panel>
          ) : null}
        </>
      )}
    </div>
  );
}
