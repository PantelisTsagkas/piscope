"use client";

import { useMemo } from "react";

import type { DigitFrequency } from "@/lib/api/types";
import { chartColors } from "@/lib/chart-theme";
import { formatDecimal, formatInteger, formatPercent, formatSigned } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/**
 * Observed digit counts with the uniform expectation as a reference line.
 *
 * The y-axis does not start at zero: on a million digits the counts differ by a fraction
 * of a percent and would look identical on a zero-based axis. The axis title says so.
 */
export function FrequencyChart({
  digits,
  className,
}: {
  digits: DigitFrequency[];
  className?: string;
}) {
  const option = useMemo<ChartOption>(() => {
    const counts = digits.map((item) => item.count);
    const expected = digits[0]?.expected_count ?? 0;
    const spread = Math.max(...counts.map((count) => Math.abs(count - expected)), 1);
    const padding = spread * 0.35;
    const low = Math.max(0, Math.floor(expected - spread - padding));
    const high = Math.ceil(expected + spread + padding);
    return {
      grid: { left: 8, right: 16, top: 36, bottom: 28, containLabel: true },
      tooltip: {
        ...tooltipStyle,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.04)" } },
        formatter: (raw) => {
          const index = (Array.isArray(raw) ? raw[0] : raw).dataIndex;
          const item = digits[index];
          if (!item) return "";
          return [
            `<b>Digit ${item.digit}</b>`,
            `Count: ${formatInteger(item.count)}`,
            `Expected: ${formatDecimal(item.expected_count, 1)}`,
            `Deviation: ${formatSigned(item.deviation, 1)} (${formatSigned(item.standardized_deviation)} sd)`,
            `Share: ${formatPercent(item.relative_frequency)}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: digits.map((item) => String(item.digit)),
        name: "digit",
        nameLocation: "middle",
        nameGap: 26,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        min: low,
        max: high,
        name: "count (axis truncated)",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => formatInteger(value) },
      },
      series: [
        {
          type: "bar",
          name: "Observed",
          data: counts,
          barMaxWidth: 36,
          itemStyle: { color: chartColors.cyan },
          emphasis: { itemStyle: { color: chartColors.purple } },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: chartColors.amber, type: "dashed", width: 1.5 },
            label: {
              formatter: "expected",
              color: chartColors.amber,
              position: "insideEndTop",
              fontSize: 11,
            },
            data: [{ yAxis: expected }],
          },
        },
      ],
    };
  }, [digits]);

  return (
    <EChart
      option={option}
      className={className}
      label="Bar chart of how often each digit 0 to 9 occurs, with the expected count as a dashed line. The same numbers are in the frequency table."
    />
  );
}
