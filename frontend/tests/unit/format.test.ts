import { describe, expect, it } from "vitest";

import {
  formatDecimal,
  formatInteger,
  formatMilliseconds,
  formatPercent,
  formatPValue,
  formatSigned,
  formatStatistic,
} from "@/lib/format";

describe("formatInteger", () => {
  it("adds thousands separators", () => {
    expect(formatInteger(1_000_000)).toBe("1,000,000");
    expect(formatInteger(762)).toBe("762");
  });
});

describe("formatSigned", () => {
  it("always shows the direction of a deviation", () => {
    expect(formatSigned(242, 1)).toBe("+242.0");
    expect(formatSigned(-41, 1)).toBe("-41.0");
    expect(formatSigned(0)).toBe("0.00");
  });
});

describe("formatPValue", () => {
  it("shows four decimals", () => {
    expect(formatPValue(0.7878669)).toBe("0.7879");
    expect(formatPValue(1)).toBe("1.0000");
  });

  it("reports tiny values as a bound instead of rounding them to zero", () => {
    expect(formatPValue(0.00001)).toBe("< 0.0001");
    expect(formatPValue(0)).toBe("< 0.0001");
  });

  it("marks a missing p-value as not applicable", () => {
    expect(formatPValue(null)).toBe("n/a");
    expect(formatPValue(undefined)).toBe("n/a");
  });
});

describe("formatStatistic", () => {
  it("keeps useful precision at every magnitude", () => {
    expect(formatStatistic(5.50908)).toBe("5.50908");
    expect(formatStatistic(3.3219241198854284)).toBe("3.32192");
    expect(formatStatistic(99)).toBe("99");
    expect(formatStatistic(0)).toBe("0");
    expect(formatStatistic(-0.000215)).toBe("-2.150e-4");
    expect(formatStatistic(123456.78)).toBe("123,456.8");
  });
});

describe("other formatters", () => {
  it("formats percentages, decimals and durations", () => {
    expect(formatPercent(0.099959, 4)).toBe("9.9959%");
    expect(formatDecimal(192272, 1)).toBe("192,272.0");
    expect(formatMilliseconds(0.894)).toBe("0.89 ms");
    expect(formatMilliseconds(111.2)).toBe("111.2 ms");
    expect(formatMilliseconds(2200)).toBe("2.20 s");
  });
});
