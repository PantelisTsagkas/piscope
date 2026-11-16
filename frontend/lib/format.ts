const integerFormat = new Intl.NumberFormat("en-GB");

/** 1234567 -> "1,234,567". */
export function formatInteger(value: number): string {
  return integerFormat.format(value);
}

/** Fixed number of decimals, with thousands separators. */
export function formatDecimal(value: number, digits = 2): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

/** 0.0999 -> "9.990%". */
export function formatPercent(fraction: number, digits = 3): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** A signed value: "+12.0" or "-3.5". Zero has no sign. */
export function formatSigned(value: number, digits = 2): string {
  const text = formatDecimal(Math.abs(value), digits);
  if (value > 0) return `+${text}`;
  if (value < 0) return `-${text}`;
  return text;
}

/**
 * A p-value for display. Very small values are shown as a bound instead of being
 * rounded to zero, because "p = 0.000" reads as "impossible".
 */
export function formatPValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return "n/a";
  if (value < 0.0001) return "< 0.0001";
  return value.toFixed(4);
}

/** A statistic with enough precision to be useful at any magnitude. */
export function formatStatistic(value: number): string {
  const magnitude = Math.abs(value);
  if (magnitude !== 0 && magnitude < 0.001) return value.toExponential(3);
  if (magnitude >= 1000) return formatDecimal(value, 1);
  return value.toPrecision(6).replace(/\.?0+$/, "");
}

export function formatMilliseconds(value: number): string {
  if (value < 1) return `${value.toFixed(2)} ms`;
  if (value < 1000) return `${value.toFixed(1)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

/** An ISO timestamp in the viewer's locale; the raw string if it cannot be parsed. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}
