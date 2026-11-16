"use client";

import { useMemo } from "react";

import type { RunsResponse } from "@/lib/api/types";
import { chartColors } from "@/lib/chart-theme";
import { formatDecimal, formatInteger } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/** Observed and expected number of runs of each length, on a logarithmic axis. */
export function RunLengthChart({ distribution }: { distribution: RunsResponse["distribution"] }) {
  const option = useMemo<ChartOption>(
    () => ({
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
        axisPointer: { type: "line", lineStyle: { color: chartColors.axis } },
        formatter: (raw) => {
          const row = distribution[(Array.isArray(raw) ? raw[0] : raw).dataIndex];
          if (!row) return "";
          return [
            `<b>Runs of length ${row.length}</b>`,
            `Observed: ${formatInteger(row.observed)}`,
            `Expected: ${formatDecimal(row.expected, row.expected < 10 ? 2 : 0)}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: distribution.map((row) => String(row.length)),
        name: "run length",
        nameLocation: "middle",
        nameGap: 26,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "log",
        name: "number of runs (log scale)",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => formatInteger(value) },
      },
      series: [
        {
          // Points, not bars: a bar has no meaningful baseline on a logarithmic axis.
          type: "scatter",
          name: "Observed",
          symbolSize: 12,
          // A log axis cannot draw zero; a length with no runs is left empty.
          data: distribution.map((row) => (row.observed > 0 ? row.observed : null)),
          itemStyle: { color: chartColors.cyan },
          z: 3,
        },
        {
          type: "line",
          name: "Expected",
          data: distribution.map((row) => row.expected),
          symbol: "circle",
          symbolSize: 6,
          lineStyle: { color: chartColors.amber, type: "dashed", width: 1.5 },
          itemStyle: { color: chartColors.amber },
        },
      ],
    }),
    [distribution],
  );

  return (
    <EChart
      option={option}
      className="h-64"
      label="Chart of how many runs of each length occur, compared with the number expected for independent uniform digits."
    />
  );
}
