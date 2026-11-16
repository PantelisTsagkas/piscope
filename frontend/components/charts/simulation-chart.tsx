"use client";

import { useMemo } from "react";

import type { SimulatedStatistic } from "@/lib/api/types";
import { chartColors } from "@/lib/chart-theme";
import { formatStatistic } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/** Where pi's statistic falls among the same statistic for the simulated sequences. */
export function SimulationChart({ statistic }: { statistic: SimulatedStatistic }) {
  const option = useMemo<ChartOption>(() => {
    const all = [...statistic.simulated, statistic.observed];
    const low = Math.min(...all);
    const high = Math.max(...all);
    const padding = (high - low) * 0.08 || Math.abs(high) * 0.01 || 1;
    return {
      grid: { left: 12, right: 16, top: 30, bottom: 8, containLabel: true },
      legend: {
        top: 0,
        right: 0,
        textStyle: { color: chartColors.mutedText, fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      tooltip: {
        ...tooltipStyle,
        formatter: (raw) => {
          const params = Array.isArray(raw) ? raw[0] : raw;
          const value = Array.isArray(params.value) ? Number(params.value[0]) : Number.NaN;
          return `${params.seriesName}: ${formatStatistic(value)}`;
        },
      },
      xAxis: {
        type: "value",
        min: low - padding,
        max: high + padding,
        ...axisStyle,
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => formatStatistic(value) },
      },
      yAxis: { type: "value", min: -1, max: 1, show: false },
      series: [
        {
          type: "scatter",
          name: "Simulated",
          data: statistic.simulated.map((value) => [value, 0]),
          symbolSize: 9,
          itemStyle: { color: chartColors.blue, opacity: 0.55 },
        },
        {
          type: "scatter",
          name: "Pi",
          data: [[statistic.observed, 0]],
          symbol: "diamond",
          symbolSize: 16,
          itemStyle: {
            color: chartColors.amber,
            borderColor: chartColors.background,
            borderWidth: 1,
          },
          z: 3,
        },
      ],
    };
  }, [statistic]);

  return (
    <EChart
      option={option}
      className="h-28"
      label={`${statistic.name}: pi's ${statistic.statistic_name} of ${formatStatistic(statistic.observed)} shown among ${statistic.simulated.length} simulated values ranging from ${formatStatistic(statistic.simulated_min)} to ${formatStatistic(statistic.simulated_max)}.`}
    />
  );
}
