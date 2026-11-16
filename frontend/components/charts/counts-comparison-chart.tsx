"use client";

import { useMemo } from "react";

import { chartColors } from "@/lib/chart-theme";
import { formatInteger } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/** Digit counts of pi beside the counts of one simulated sequence of the same length. */
export function CountsComparisonChart({
  piCounts,
  randomCounts,
}: {
  piCounts: number[];
  randomCounts: number[];
}) {
  const option = useMemo<ChartOption>(() => {
    const all = [...piCounts, ...randomCounts];
    const expected = piCounts.reduce((sum, value) => sum + value, 0) / 10;
    const spread = Math.max(...all.map((value) => Math.abs(value - expected)), 1);
    return {
      grid: { left: 8, right: 16, top: 40, bottom: 28, containLabel: true },
      legend: {
        top: 0,
        right: 0,
        textStyle: { color: chartColors.mutedText, fontSize: 11 },
        itemWidth: 12,
        itemHeight: 8,
      },
      tooltip: {
        ...tooltipStyle,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.04)" } },
        valueFormatter: (value) => formatInteger(Number(value)),
      },
      xAxis: {
        type: "category",
        data: piCounts.map((_, digit) => String(digit)),
        name: "digit",
        nameLocation: "middle",
        nameGap: 26,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        min: Math.max(0, Math.floor(expected - spread * 1.35)),
        max: Math.ceil(expected + spread * 1.35),
        name: "count (axis truncated)",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => formatInteger(value) },
      },
      series: [
        {
          type: "bar",
          name: "Pi",
          data: piCounts,
          barMaxWidth: 18,
          itemStyle: { color: chartColors.cyan },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: chartColors.amber, type: "dashed", width: 1.5 },
            label: {
              formatter: "expected",
              color: chartColors.amber,
              fontSize: 11,
              position: "insideEndTop",
            },
            data: [{ yAxis: expected }],
          },
        },
        {
          type: "bar",
          name: "First simulated sequence",
          data: randomCounts,
          barMaxWidth: 18,
          itemStyle: { color: chartColors.purple },
        },
      ],
    };
  }, [piCounts, randomCounts]);

  return (
    <EChart
      option={option}
      label="Grouped bar chart comparing how often each digit occurs in the chosen range of pi and in the first simulated random sequence."
    />
  );
}
