/** Parsing of user-supplied numbers and digit sequences, from inputs and from the URL. */

/** A positive integer, or null when the text is not one. Accepts "1,000,000" and "1 000". */
export function parsePositiveInteger(text: string | null | undefined): number | null {
  if (text === null || text === undefined) return null;
  const cleaned = text.replace(/[\s,_]/g, "");
  if (!/^\d+$/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isSafeInteger(value) && value >= 1 ? value : null;
}

/** A non-negative integer (0 allowed), or null. */
export function parseNonNegativeInteger(text: string | null | undefined): number | null {
  if (text === null || text === undefined) return null;
  const cleaned = text.replace(/[\s,_]/g, "");
  if (!/^\d+$/.test(cleaned)) return null;
  const value = Number(cleaned);
  return Number.isSafeInteger(value) ? value : null;
}

/** Keep only the digits of a search pattern typed or pasted by a user ("3.14159" -> "314159"). */
export function sanitizePattern(text: string): string {
  return text.replace(/[^0-9]/g, "");
}

export function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

/**
 * Starting positions of every occurrence of `pattern` in `digits`, overlaps included.
 * Positions are 0-based offsets into `digits`.
 */
export function findOccurrences(digits: string, pattern: string): number[] {
  if (pattern.length === 0 || pattern.length > digits.length) return [];
  const found: number[] = [];
  let from = digits.indexOf(pattern);
  while (from !== -1) {
    found.push(from);
    from = digits.indexOf(pattern, from + 1);
  }
  return found;
}
