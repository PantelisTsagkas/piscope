"use client";

import { useMemo } from "react";

import type { SearchMatch } from "@/lib/api/types";
import { chartColors } from "@/lib/chart-theme";
import { formatInteger } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/** Distance from each occurrence to the one before it, for the matches on the current page. */
export function GapChart({
  matches,
  expectedMean,
}: {
  matches: SearchMatch[];
  expectedMean: number;
}) {
  const withGaps = useMemo(
    () => matches.filter((match) => match.gap_from_previous !== null),
    [matches],
  );
  const option = useMemo<ChartOption>(
    () => ({
      grid: { left: 8, right: 24, top: 36, bottom: 28, containLabel: true },
      tooltip: {
        ...tooltipStyle,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.04)" } },
        formatter: (raw) => {
          const match = withGaps[(Array.isArray(raw) ? raw[0] : raw).dataIndex];
          if (!match) return "";
          return [
            `<b>Occurrence ${formatInteger(match.index + 1)}</b>`,
            `Position: ${formatInteger(match.position)}`,
            `Gap from previous: ${formatInteger(match.gap_from_previous ?? 0)}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: withGaps.map((match) => String(match.index + 1)),
        name: "occurrence",
        nameLocation: "middle",
        nameGap: 26,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: "digits since previous occurrence",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => formatInteger(value) },
      },
      series: [
        {
          type: "bar",
          name: "Gap",
          data: withGaps.map((match) => match.gap_from_previous ?? 0),
          barMaxWidth: 14,
          itemStyle: { color: chartColors.purple },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: chartColors.amber, type: "dashed", width: 1.5 },
            label: {
              formatter: "expected mean",
              color: chartColors.amber,
              position: "insideEndTop",
              fontSize: 11,
            },
            data: [{ yAxis: expectedMean }],
          },
        },
      ],
    }),
    [withGaps, expectedMean],
  );

  if (withGaps.length === 0) return null;
  return (
    <EChart
      option={option}
      className="h-64"
      label="Bar chart of the distance between consecutive occurrences on this page. The same numbers are in the gap column of the table."
    />
  );
}
