"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AnalysisRange } from "@/hooks/use-analysis-range";
import { formatInteger } from "@/lib/format";
import { parsePositiveInteger } from "@/lib/params";

import { Field } from "./field";

/**
 * Start position and digit count for an analysis. Validation happens here, against the
 * dataset size and the server limit, so an invalid range never reaches the API.
 */
export function RangeControls({
  range,
  onChange,
}: {
  range: AnalysisRange;
  onChange: (start: number, count: number | null) => void;
}) {
  // Remount the form when the applied range changes so the inputs always show it.
  return <RangeForm key={`${range.start}-${range.count}`} range={range} onChange={onChange} />;
}

function RangeForm({
  range,
  onChange,
}: {
  range: AnalysisRange;
  onChange: (start: number, count: number | null) => void;
}) {
  const [startText, setStartText] = useState(String(range.start));
  const [countText, setCountText] = useState(String(range.count));

  const start = parsePositiveInteger(startText);
  const count = parsePositiveInteger(countText);

  let startError: string | null = null;
  let countError: string | null = null;
  if (start === null) startError = "Enter a whole number of 1 or more.";
  else if (start > range.total) startError = `The last position is ${formatInteger(range.total)}.`;
  if (count === null) countError = "Enter a whole number of 1 or more.";
  else if (start !== null && startError === null) {
    const available = range.total - start + 1;
    const limit = Math.min(available, Math.max(range.maxCount, 1));
    if (count > available) {
      countError = `Only ${formatInteger(available)} digits remain from that position.`;
    } else if (count > limit) {
      countError = `The server analyses at most ${formatInteger(limit)} digits here.`;
    }
  }
  const valid = startError === null && countError === null;
  const isWhole = range.start === 1 && range.count === range.total;

  return (
    <form
      className="flex flex-wrap items-start gap-3"
      aria-label="Analysis range"
      onSubmit={(event) => {
        event.preventDefault();
        if (valid && start !== null && count !== null) onChange(start, count);
      }}
    >
      <Field id="range-start" label="Start position" error={startError} className="w-36">
        <Input
          id="range-start"
          inputMode="numeric"
          value={startText}
          onChange={(event) => setStartText(event.target.value)}
          aria-invalid={startError !== null}
          aria-describedby={startError ? "range-start-error" : undefined}
          className="font-mono"
        />
      </Field>
      <Field id="range-count" label="Digits" error={countError} className="w-36">
        <Input
          id="range-count"
          inputMode="numeric"
          value={countText}
          onChange={(event) => setCountText(event.target.value)}
          aria-invalid={countError !== null}
          aria-describedby={countError ? "range-count-error" : undefined}
          className="font-mono"
        />
      </Field>
      <div className="flex gap-2 pt-[22px]">
        <Button type="submit" disabled={!valid}>
          Apply range
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={isWhole}
          onClick={() => onChange(1, null)}
        >
          All digits
        </Button>
      </div>
    </form>
  );
}

/** "positions 1 to 1,000,000 (1,000,000 digits)". */
export function describeRange(start: number, end: number): string {
  return `positions ${formatInteger(start)} to ${formatInteger(end)} (${formatInteger(end - start + 1)} digits)`;
}
