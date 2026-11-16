"use client";

import { useMemo } from "react";

import { chartColors } from "@/lib/chart-theme";
import { formatSigned } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

export interface HeatCell {
  x: number;
  y: number;
  /** Standardized deviation shown by colour. */
  z: number;
  /** Lines shown in the tooltip. */
  lines: string[];
}

/**
 * A heatmap of standardized deviations on a fixed -3 to +3 diverging scale: blue below
 * expectation, amber above, neutral near zero. The fixed scale stops ordinary noise from
 * being stretched to look dramatic.
 */
export function ZHeatmap({
  cells,
  xLabels,
  yLabels,
  xName,
  yName,
  label,
  className,
  onCellClick,
}: {
  cells: HeatCell[];
  xLabels: string[];
  yLabels: string[];
  xName: string;
  yName: string;
  label: string;
  className?: string;
  onCellClick?: (cell: HeatCell) => void;
}) {
  const option = useMemo<ChartOption>(
    () => ({
      grid: { left: 8, right: 16, top: 16, bottom: 72, containLabel: true },
      tooltip: {
        ...tooltipStyle,
        formatter: (raw) => {
          const cell = cells[(Array.isArray(raw) ? raw[0] : raw).dataIndex];
          return cell ? cell.lines.join("<br/>") : "";
        },
      },
      xAxis: {
        type: "category",
        data: xLabels,
        name: xName,
        nameLocation: "middle",
        nameGap: 28,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "category",
        data: yLabels,
        name: yName,
        nameLocation: "middle",
        nameGap: 24,
        nameRotate: 90,
        inverse: true,
        ...axisStyle,
        splitLine: { show: false },
      },
      visualMap: {
        min: -3,
        max: 3,
        dimension: 2,
        calculable: false,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        itemWidth: 12,
        itemHeight: 160,
        text: ["+3 sd or more", "-3 sd or less"],
        textStyle: { color: chartColors.mutedText, fontSize: 11 },
        formatter: (value) => formatSigned(Number(value), 1),
        inRange: { color: [chartColors.blue, chartColors.surface, chartColors.amber] },
      },
      series: [
        {
          type: "heatmap",
          data: cells.map((cell) => [cell.x, cell.y, cell.z]),
          itemStyle: { borderColor: chartColors.background, borderWidth: 1 },
          emphasis: { itemStyle: { borderColor: chartColors.text, borderWidth: 1 } },
          progressive: 0,
        },
      ],
    }),
    [cells, xLabels, yLabels, xName, yName],
  );

  return (
    <EChart
      option={option}
      label={label}
      className={className}
      onDataClick={
        onCellClick
          ? ({ dataIndex }) => {
              const cell = cells[dataIndex];
              if (cell) onCellClick(cell);
            }
          : undefined
      }
    />
  );
}
