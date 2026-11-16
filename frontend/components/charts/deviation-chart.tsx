"use client";

import { useMemo } from "react";

import type { DigitFrequency } from "@/lib/api/types";
import { chartColors } from "@/lib/chart-theme";
import { formatInteger, formatSigned } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

/** Each digit's deviation from the uniform expectation, in standard deviations. */
export function DeviationChart({ digits }: { digits: DigitFrequency[] }) {
  const option = useMemo<ChartOption>(() => {
    const values = digits.map((item) => item.standardized_deviation);
    const bound = Math.max(3, Math.ceil(Math.max(...values.map(Math.abs))));
    return {
      grid: { left: 8, right: 16, top: 36, bottom: 28, containLabel: true },
      tooltip: {
        ...tooltipStyle,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.04)" } },
        formatter: (raw) => {
          const item = digits[(Array.isArray(raw) ? raw[0] : raw).dataIndex];
          if (!item) return "";
          return [
            `<b>Digit ${item.digit}</b>`,
            `${formatSigned(item.standardized_deviation)} standard deviations`,
            `${formatSigned(item.deviation, 1)} against ${formatInteger(item.count)} observed`,
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
        min: -bound,
        max: bound,
        name: "deviation (standard deviations)",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
      },
      series: [
        {
          type: "bar",
          name: "Deviation",
          barMaxWidth: 36,
          data: values.map((value) => ({
            value,
            itemStyle: { color: value >= 0 ? chartColors.purple : chartColors.blue },
          })),
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: chartColors.amber, type: "dashed", width: 1 },
            label: { color: chartColors.amber, fontSize: 11, position: "insideEndTop" },
            data: [
              { yAxis: 2, label: { formatter: "+2 sd" } },
              { yAxis: -2, label: { formatter: "-2 sd", position: "insideEndBottom" } },
            ],
          },
        },
      ],
    };
  }, [digits]);

  return (
    <EChart
      option={option}
      label="Bar chart of each digit's deviation from the expected count in standard deviations, with reference lines at plus and minus two. The same numbers are in the frequency table."
    />
  );
}
