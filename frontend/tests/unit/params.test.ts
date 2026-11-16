import { describe, expect, it } from "vitest";

import {
  clamp,
  findOccurrences,
  parseNonNegativeInteger,
  parsePositiveInteger,
  sanitizePattern,
} from "@/lib/params";

describe("parsePositiveInteger", () => {
  it("accepts plain and separated numbers", () => {
    expect(parsePositiveInteger("1")).toBe(1);
    expect(parsePositiveInteger("1,000,000")).toBe(1_000_000);
    expect(parsePositiveInteger(" 250 000 ")).toBe(250_000);
  });

  it.each(["", "0", "-5", "1.5", "abc", "1e6", "99999999999999999999", null, undefined])(
    "rejects %s",
    (text) => {
      expect(parsePositiveInteger(text)).toBeNull();
    },
  );
});

describe("parseNonNegativeInteger", () => {
  it("allows zero but nothing negative or fractional", () => {
    expect(parseNonNegativeInteger("0")).toBe(0);
    expect(parseNonNegativeInteger("42")).toBe(42);
    expect(parseNonNegativeInteger("-1")).toBeNull();
    expect(parseNonNegativeInteger("4.2")).toBeNull();
  });

  it("rejects seeds a browser cannot represent exactly", () => {
    expect(parseNonNegativeInteger(String(Number.MAX_SAFE_INTEGER))).toBe(Number.MAX_SAFE_INTEGER);
    expect(parseNonNegativeInteger("9007199254740993")).toBeNull();
  });
});

describe("sanitizePattern", () => {
  it("keeps only digits", () => {
    expect(sanitizePattern("3.14159")).toBe("314159");
    expect(sanitizePattern(" 12 34x")).toBe("1234");
    expect(sanitizePattern("abc")).toBe("");
  });
});

describe("clamp", () => {
  it("limits a value to a range", () => {
    expect(clamp(5, 1, 10)).toBe(5);
    expect(clamp(0, 1, 10)).toBe(1);
    expect(clamp(11, 1, 10)).toBe(10);
  });
});

describe("findOccurrences", () => {
  it("finds every occurrence by its 0-based offset", () => {
    expect(findOccurrences("1415926535", "5")).toEqual([3, 7, 9]);
    expect(findOccurrences("1415926535", "14")).toEqual([0]);
  });

  it("counts overlapping occurrences, as the search engine does", () => {
    expect(findOccurrences("0000", "000")).toEqual([0, 1]);
    expect(findOccurrences("12121", "121")).toEqual([0, 2]);
  });

  it("returns nothing for an empty or over-long pattern", () => {
    expect(findOccurrences("123", "")).toEqual([]);
    expect(findOccurrences("123", "1234")).toEqual([]);
    expect(findOccurrences("123", "9")).toEqual([]);
  });
});
