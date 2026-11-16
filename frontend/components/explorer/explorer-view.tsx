"use client";

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel } from "@/components/shared/panel";
import { ErrorState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useUrlState } from "@/hooks/use-url-state";
import { useDatasetInfo, useDigitRange } from "@/lib/api/hooks";
import { formatInteger } from "@/lib/format";
import { clamp, findOccurrences, parsePositiveInteger, sanitizePattern } from "@/lib/params";

import { DigitGrid } from "./digit-grid";

const DEFAULT_COUNT = 1000;
const FALLBACK_MAX_COUNT = 10_000;

export function ExplorerView() {
  const { searchParams, update } = useUrlState();
  const dataset = useDatasetInfo();

  const total = dataset.data?.total_digits ?? null;
  const maxCount = dataset.data?.limits.max_range_digits ?? FALLBACK_MAX_COUNT;

  const requestedStart = parsePositiveInteger(searchParams.get("start")) ?? 1;
  const requestedCount = parsePositiveInteger(searchParams.get("count")) ?? DEFAULT_COUNT;
  const start = total === null ? requestedStart : clamp(requestedStart, 1, total);
  const count =
    total === null
      ? Math.min(requestedCount, maxCount)
      : clamp(requestedCount, 1, Math.min(maxCount, total - start + 1));
  const highlight = sanitizePattern(searchParams.get("highlight") ?? "");
  const selected = parsePositiveInteger(searchParams.get("select"));
  const selectedLength = parsePositiveInteger(searchParams.get("length")) ?? 1;

  const range = useDigitRange(start, count, total !== null);
  const digits = range.data?.digits ?? "";
  const shownStart = range.data?.start ?? start;

  const { highlighted, matchCount } = useMemo(() => {
    const offsets = new Set<number>();
    const matches = findOccurrences(digits, highlight);
    for (const match of matches) {
      for (let index = 0; index < highlight.length; index += 1) offsets.add(match + index);
    }
    // A sequence opened from a search result or an observation is highlighted too.
    if (selected !== null && selectedLength > 1) {
      for (let index = 0; index < selectedLength; index += 1) {
        const offset = selected - shownStart + index;
        if (offset >= 0 && offset < digits.length) offsets.add(offset);
      }
    }
    return { highlighted: offsets, matchCount: matches.length };
  }, [digits, highlight, selected, selectedLength, shownStart]);

  if (dataset.error) {
    return (
      <>
        <Header />
        <ErrorState error={dataset.error} onRetry={() => void dataset.refetch()} />
      </>
    );
  }

  const goTo = (nextStart: number) =>
    update(
      { start: nextStart === 1 ? null : nextStart, select: null, length: null },
      { push: true },
    );
  const lastStart = total === null ? 1 : Math.max(1, total - count + 1);

  return (
    <>
      <Header />

      <Panel
        title="Position"
        description={
          total === null
            ? "Loading dataset"
            : `${formatInteger(total)} digits available. Position 1 is the first digit after the decimal point; the leading 3 is not counted.`
        }
      >
        {total === null ? (
          <Skeleton className="h-14 w-full max-w-xl" />
        ) : (
          <PositionForm
            key={`${start}-${count}-${highlight}`}
            start={start}
            count={count}
            highlight={highlight}
            total={total}
            maxCount={maxCount}
            onApply={(next) =>
              update(
                {
                  start: next.start === 1 ? null : next.start,
                  count: next.count === DEFAULT_COUNT ? null : next.count,
                  highlight: next.highlight || null,
                  select: null,
                  length: null,
                },
                { push: true },
              )
            }
          />
        )}
      </Panel>

      <div className="grid gap-6 xl:grid-cols-4">
        <Panel
          title="Digits"
          className="xl:col-span-3"
          description={
            range.data
              ? `Positions ${formatInteger(range.data.start)} to ${formatInteger(range.data.end)}`
              : "Loading digits"
          }
          action={
            <nav aria-label="Digit pages" className="flex gap-1">
              <Button
                variant="outline"
                size="icon-sm"
                aria-label="First digits"
                disabled={start === 1}
                onClick={() => goTo(1)}
              >
                <ChevronsLeft aria-hidden />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={start === 1}
                onClick={() => goTo(Math.max(1, start - count))}
              >
                <ChevronLeft aria-hidden /> Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={total === null || start + count > total}
                onClick={() => goTo(start + count)}
              >
                Next <ChevronRight aria-hidden />
              </Button>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label="Last digits"
                disabled={total === null || start >= lastStart}
                onClick={() => goTo(lastStart)}
              >
                <ChevronsRight aria-hidden />
              </Button>
            </nav>
          }
        >
          {range.error ? (
            <ErrorState error={range.error} onRetry={() => void range.refetch()} />
          ) : range.data ? (
            <>
              {start === 1 ? (
                <p className="font-mono text-xs text-muted-foreground">
                  <span className="text-foreground">3.</span> followed by:
                </p>
              ) : null}
              <div className={range.isPlaceholderData ? "opacity-50" : undefined}>
                <DigitGrid
                  digits={digits}
                  start={shownStart}
                  selected={selected}
                  highlighted={highlighted}
                  onSelect={(position) => update({ select: position, length: null })}
                />
              </div>
              {highlight ? (
                <p
                  className="text-xs text-muted-foreground"
                  role="status"
                  data-testid="highlight-count"
                >
                  <span className="font-mono text-cyan">{highlight}</span> occurs{" "}
                  {formatInteger(matchCount)} time{matchCount === 1 ? "" : "s"} in the digits shown.
                  Matches that cross the edge of this page are not marked.{" "}
                  <Link
                    href={`/search?q=${highlight}`}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    Search all digits
                  </Link>
                </p>
              ) : null}
            </>
          ) : (
            <Skeleton className="h-96 w-full" />
          )}
        </Panel>

        <Panel
          title="Inspector"
          description="Click a digit, or focus the grid and use the arrow keys."
        >
          <Inspector
            selected={selected}
            digits={digits}
            shownStart={shownStart}
            onJump={(position) =>
              update(
                { start: Math.max(1, position - Math.floor(count / 2)), select: position },
                { push: true },
              )
            }
          />
        </Panel>
      </div>
    </>
  );
}

function Header() {
  return (
    <PageHeader
      title="Digit Explorer"
      description="Read the digits directly. Jump to any position, page through the expansion and inspect individual digits."
    />
  );
}

function PositionForm({
  start,
  count,
  highlight,
  total,
  maxCount,
  onApply,
}: {
  start: number;
  count: number;
  highlight: string;
  total: number;
  maxCount: number;
  onApply: (next: { start: number; count: number; highlight: string }) => void;
}) {
  const [startText, setStartText] = useState(String(start));
  const [countText, setCountText] = useState(String(count));
  const [highlightText, setHighlightText] = useState(highlight);

  const nextStart = parsePositiveInteger(startText);
  const nextCount = parsePositiveInteger(countText);
  let startError: string | null = null;
  let countError: string | null = null;
  if (nextStart === null) startError = "Enter a whole number of 1 or more.";
  else if (nextStart > total) startError = `The last position is ${formatInteger(total)}.`;
  if (nextCount === null) countError = "Enter a whole number of 1 or more.";
  else if (nextCount > maxCount) countError = `At most ${formatInteger(maxCount)} digits per page.`;
  const valid = startError === null && countError === null;

  return (
    <form
      aria-label="Digit range"
      className="flex flex-wrap items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (valid && nextStart !== null && nextCount !== null) {
          onApply({ start: nextStart, count: nextCount, highlight: highlightText });
        }
      }}
    >
      <Field id="explorer-start" label="Start position" error={startError} className="w-36">
        <Input
          id="explorer-start"
          inputMode="numeric"
          value={startText}
          onChange={(event) => setStartText(event.target.value)}
          aria-invalid={startError !== null}
          aria-describedby={startError ? "explorer-start-error" : undefined}
          className="font-mono"
        />
      </Field>
      <Field id="explorer-count" label="Digits to show" error={countError} className="w-36">
        <Input
          id="explorer-count"
          inputMode="numeric"
          value={countText}
          onChange={(event) => setCountText(event.target.value)}
          aria-invalid={countError !== null}
          aria-describedby={countError ? "explorer-count-error" : undefined}
          className="font-mono"
        />
      </Field>
      <Field
        id="explorer-highlight"
        label="Highlight sequence"
        hint="Optional. Marks matches in the digits shown."
        className="w-56"
      >
        <Input
          id="explorer-highlight"
          inputMode="numeric"
          placeholder="e.g. 999999"
          value={highlightText}
          onChange={(event) => setHighlightText(sanitizePattern(event.target.value))}
          aria-describedby="explorer-highlight-hint"
          className="font-mono"
        />
      </Field>
      <div className="pt-[22px]">
        <Button type="submit" disabled={!valid}>
          Show digits
        </Button>
      </div>
    </form>
  );
}

function Inspector({
  selected,
  digits,
  shownStart,
  onJump,
}: {
  selected: number | null;
  digits: string;
  shownStart: number;
  onJump: (position: number) => void;
}) {
  if (selected === null) {
    return <p className="text-sm text-muted-foreground">No digit selected.</p>;
  }
  const offset = selected - shownStart;
  const visible = offset >= 0 && offset < digits.length;
  if (!visible) {
    return (
      <div className="flex flex-col items-start gap-3 text-sm text-muted-foreground">
        <p>Position {formatInteger(selected)} is not on this page.</p>
        <Button variant="outline" size="sm" onClick={() => onJump(selected)}>
          Go to position {formatInteger(selected)}
        </Button>
      </div>
    );
  }
  const digit = digits[offset];
  const before = digits.slice(Math.max(0, offset - 8), offset);
  const after = digits.slice(offset + 1, offset + 9);
  return (
    <div className="flex flex-col gap-4" aria-live="polite" data-testid="inspector">
      <div className="flex items-baseline gap-4">
        <span
          className="font-mono text-5xl leading-none text-primary"
          data-testid="inspector-digit"
        >
          {digit}
        </span>
        <div className="flex flex-col font-mono text-xs">
          <span className="text-muted-foreground uppercase">Position</span>
          <span className="text-base tabular-nums" data-testid="inspector-position">
            {formatInteger(selected)}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          Context
        </span>
        <p className="font-mono text-sm break-all">
          <span className="text-muted-foreground">{before}</span>
          <span className="bg-primary px-0.5 text-primary-foreground">{digit}</span>
          <span className="text-muted-foreground">{after}</span>
        </p>
      </div>
      <Note>This is the {ordinal(selected)} digit after the decimal point of pi.</Note>
    </div>
  );
}

/** 1 -> "1st", 22 -> "22nd", 113 -> "113th", with thousands separators. */
export function ordinal(value: number): string {
  const lastTwo = value % 100;
  const last = value % 10;
  let suffix = "th";
  if (lastTwo < 11 || lastTwo > 13) {
    if (last === 1) suffix = "st";
    else if (last === 2) suffix = "nd";
    else if (last === 3) suffix = "rd";
  }
  return `${formatInteger(value)}${suffix}`;
}
