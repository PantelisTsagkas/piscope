"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { useDatasetInfo } from "@/lib/api/hooks";
import { clamp, parsePositiveInteger } from "@/lib/params";

export interface AnalysisRange {
  /** First position analysed (1-based). */
  start: number;
  /** Number of digits analysed. */
  count: number;
  /** Last position analysed, inclusive. */
  end: number;
  /** Digits available in the dataset. */
  total: number;
  /** Largest count the server accepts for this kind of analysis. */
  maxCount: number;
  /** True when the range was shortened to respect the server limit. */
  limited: boolean;
}

/**
 * The analysis range shared by the dashboard and analysis pages, kept in the URL as
 * `start` and `count` so a view can be bookmarked and repeated. Returns null until the
 * dataset size and limits are known.
 */
export function useAnalysisRange(limitKey: "max_analysis_digits" | "max_statistics_digits") {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const dataset = useDatasetInfo();

  const requestedStart = parsePositiveInteger(searchParams.get("start"));
  const requestedCount = parsePositiveInteger(searchParams.get("count"));

  const range = useMemo<AnalysisRange | null>(() => {
    if (!dataset.data) return null;
    const total = dataset.data.total_digits;
    const limit = dataset.data.limits[limitKey] ?? total;
    const start = clamp(requestedStart ?? 1, 1, total);
    const available = total - start + 1;
    const maxCount = Math.min(available, limit);
    const count = clamp(requestedCount ?? maxCount, 1, maxCount);
    return {
      start,
      count,
      end: start + count - 1,
      total,
      maxCount,
      limited: requestedCount === null && available > limit,
    };
  }, [dataset.data, limitKey, requestedStart, requestedCount]);

  const setRange = useCallback(
    (start: number, count: number | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (start === 1) params.delete("start");
      else params.set("start", String(start));
      if (count === null) params.delete("count");
      else params.set("count", String(count));
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return { range, setRange, dataset };
}
