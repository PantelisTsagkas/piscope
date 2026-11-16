"use client";

import { useMemo } from "react";

import { chartColors } from "@/lib/chart-theme";
import { formatPValue } from "@/lib/format";

import { axisStyle, EChart, tooltipStyle, type ChartOption } from "./echart";

export interface LagPoint {
  lag: number;
  autocorrelation: number;
  p_value: number;
  p_value_holm: number;
}

/** Reads the per-lag values the engine attaches to an autocorrelation result. */
export function parseLagDetails(details: Record<string, unknown>): {
  lags: LagPoint[];
  band: number | null;
} {
  const raw = Array.isArray(details.lags) ? details.lags : [];
  const lags: LagPoint[] = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) continue;
    const record = item as Record<string, unknown>;
    if (typeof record.lag === "number" && typeof record.autocorrelation === "number") {
      lags.push({
        lag: record.lag,
        autocorrelation: record.autocorrelation,
        p_value: typeof record.p_value === "number" ? record.p_value : Number.NaN,
        p_value_holm: typeof record.p_value_holm === "number" ? record.p_value_holm : Number.NaN,
      });
    }
  }
  const band = typeof details.confidence_band_95 === "number" ? details.confidence_band_95 : null;
  return { lags, band };
}

/** Autocorrelation at each lag with the 95% band expected for independent digits. */
export function AutocorrelationChart({ lags, band }: { lags: LagPoint[]; band: number | null }) {
  const option = useMemo<ChartOption>(() => {
    const largest = Math.max(...lags.map((point) => Math.abs(point.autocorrelation)), band ?? 0);
    const bound = largest * 1.4 || 1;
    return {
      grid: { left: 8, right: 16, top: 36, bottom: 28, containLabel: true },
      tooltip: {
        ...tooltipStyle,
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.04)" } },
        formatter: (raw) => {
          const point = lags[(Array.isArray(raw) ? raw[0] : raw).dataIndex];
          if (!point) return "";
          return [
            `<b>Lag ${point.lag}</b>`,
            `Autocorrelation: ${point.autocorrelation.toFixed(5)}`,
            `p-value: ${formatPValue(point.p_value)}`,
            `Holm-adjusted across lags: ${formatPValue(point.p_value_holm)}`,
          ].join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: lags.map((point) => String(point.lag)),
        name: "lag",
        nameLocation: "middle",
        nameGap: 26,
        ...axisStyle,
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        min: -bound,
        max: bound,
        name: "autocorrelation",
        nameLocation: "end",
        ...axisStyle,
        nameTextStyle: { ...axisStyle.nameTextStyle, align: "left" },
        axisLabel: { ...axisStyle.axisLabel, formatter: (value: number) => value.toFixed(4) },
      },
      series: [
        {
          type: "bar",
          name: "Autocorrelation",
          barMaxWidth: 18,
          data: lags.map((point) => point.autocorrelation),
          itemStyle: { color: chartColors.cyan },
          markLine:
            band === null
              ? undefined
              : {
                  silent: true,
                  symbol: "none",
                  lineStyle: { color: chartColors.amber, type: "dashed", width: 1 },
                  label: { color: chartColors.amber, fontSize: 11, position: "insideEndTop" },
                  data: [
                    { yAxis: band, label: { formatter: "95% band" } },
                    { yAxis: -band, label: { show: false } },
                  ],
                },
        },
      ],
    };
  }, [lags, band]);

  return (
    <EChart
      option={option}
      className="h-64"
      label="Bar chart of the autocorrelation at each lag, with dashed lines marking the band that independent digits stay inside about 95% of the time."
    />
  );
}
