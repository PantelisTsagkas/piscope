import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { Locator, Page } from "@playwright/test";

/**
 * The first 10,000 decimals of pi from a published file (see
 * engine/tests/fixtures/README.md). Expected values in these tests are computed from
 * this text, never typed in, so the UI is checked against an independent source.
 */
export const REFERENCE_DIGITS = readFileSync(
  join(__dirname, "../../../engine/tests/fixtures/pi_first_10000_decimals.txt"),
  "utf-8",
).trim();

/** 1-based positions of every occurrence of `pattern`, overlaps included. */
export function referencePositions(pattern: string, digits = REFERENCE_DIGITS): number[] {
  const positions: number[] = [];
  let from = digits.indexOf(pattern);
  while (from !== -1) {
    positions.push(from + 1);
    from = digits.indexOf(pattern, from + 1);
  }
  return positions;
}

/** Count of each digit 0-9 in the first `length` reference digits. */
export function referenceCounts(length: number): number[] {
  const counts = Array.from({ length: 10 }, () => 0);
  for (const digit of REFERENCE_DIGITS.slice(0, length)) counts[Number(digit)]! += 1;
  return counts;
}

export function withSeparators(value: number): string {
  return value.toLocaleString("en-GB");
}

/** The drawing surface of the chart whose accessible name matches. ECharts stacks layers. */
export function chartCanvas(scope: Page | Locator, name: RegExp): Locator {
  return scope.getByRole("img", { name }).locator("canvas").first();
}
