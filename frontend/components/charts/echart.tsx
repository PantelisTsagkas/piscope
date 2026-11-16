"use client";

import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import type { ComposeOption } from "echarts/core";
import * as echarts from "echarts/core";
import type {
  BarSeriesOption,
  HeatmapSeriesOption,
  LineSeriesOption,
  ScatterSeriesOption,
} from "echarts/charts";
import type {
  GridComponentOption,
  LegendComponentOption,
  MarkLineComponentOption,
  TooltipComponentOption,
  VisualMapComponentOption,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

import { chartColors } from "@/lib/chart-theme";
import { cn } from "@/lib/utils";

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export type ChartOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | ScatterSeriesOption
  | HeatmapSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | LegendComponentOption
  | MarkLineComponentOption
  | VisualMapComponentOption
>;

/** Canvas text cannot read CSS variables, so resolve the font family once in the browser. */
function resolveFontFamily(): string {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue("--font-jetbrains-mono")
    .trim();
  return value ? `${value}, ui-monospace, monospace` : "ui-monospace, monospace";
}

interface EChartProps {
  option: ChartOption;
  /** Describes the chart for screen readers. Every chart also has a table or text equivalent. */
  label: string;
  className?: string;
  onDataClick?: (params: { dataIndex: number; value: unknown; seriesName?: string }) => void;
}

/** A thin, typed wrapper around an ECharts canvas that follows the size of its container. */
export function EChart({ option, label, className, onDataClick }: EChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const clickRef = useRef(onDataClick);

  useEffect(() => {
    clickRef.current = onDataClick;
  }, [onDataClick]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = echarts.init(container, null, { renderer: "canvas" });
    chartRef.current = chart;
    chart.on("click", (params) => {
      clickRef.current?.({
        dataIndex: params.dataIndex,
        value: params.value,
        seriesName: params.seriesName,
      });
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(
      {
        backgroundColor: "transparent",
        animationDuration: 250,
        textStyle: { fontFamily: resolveFontFamily(), color: chartColors.mutedText },
        ...option,
      },
      { notMerge: true },
    );
  }, [option]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={label}
      data-testid="chart"
      className={cn("h-72 w-full", className)}
    />
  );
}

/** Axis and tooltip styling shared by every chart. */
export const axisStyle = {
  axisLine: { lineStyle: { color: chartColors.axis } },
  axisTick: { lineStyle: { color: chartColors.axis } },
  axisLabel: { color: chartColors.mutedText, fontSize: 11 },
  splitLine: { lineStyle: { color: chartColors.grid } },
  nameTextStyle: { color: chartColors.mutedText, fontSize: 11 },
} as const;

export const tooltipStyle: TooltipComponentOption = {
  backgroundColor: chartColors.surface,
  borderColor: chartColors.axis,
  borderWidth: 1,
  padding: [8, 10],
  textStyle: { color: chartColors.text, fontSize: 12 },
  extraCssText: "border-radius:0;box-shadow:none;",
};
