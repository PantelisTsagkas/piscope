"use client";

import { memo, useMemo } from "react";

import { formatInteger } from "@/lib/format";
import { cn } from "@/lib/utils";

const GROUP_SIZE = 10;

interface DigitGridProps {
  /** The digits to show; `digits[0]` is at position `start`. */
  digits: string;
  start: number;
  /** Position of the inspected digit, if any. */
  selected: number | null;
  /** 0-based offsets into `digits` that are part of a highlighted match. */
  highlighted: ReadonlySet<number>;
  onSelect: (position: number) => void;
}

/**
 * Digits in groups of ten, each group labelled with the position of its first digit.
 * Groups wrap to the available width, so the same markup works on any screen.
 *
 * The grid is one tab stop: arrow keys move the inspected digit, Home and End jump to
 * the ends of the displayed range. Clicks are handled by one delegated listener, which
 * keeps thousands of digits cheap to render.
 */
export const DigitGrid = memo(function DigitGrid({
  digits,
  start,
  selected,
  highlighted,
  onSelect,
}: DigitGridProps) {
  const groups = useMemo(() => {
    const result: { offset: number; text: string }[] = [];
    for (let offset = 0; offset < digits.length; offset += GROUP_SIZE) {
      result.push({ offset, text: digits.slice(offset, offset + GROUP_SIZE) });
    }
    return result;
  }, [digits]);

  const end = start + digits.length - 1;
  const selectedOffset =
    selected !== null && selected >= start && selected <= end ? selected - start : null;

  const move = (delta: number) => {
    const from = selectedOffset ?? (delta > 0 ? -1 : digits.length);
    const next = Math.min(Math.max(from + delta, 0), digits.length - 1);
    onSelect(start + next);
  };

  return (
    <div
      role="group"
      tabIndex={0}
      aria-label={`Digits at positions ${formatInteger(start)} to ${formatInteger(end)}. Use the arrow keys to inspect a digit.`}
      data-testid="digit-grid"
      className="flex flex-wrap gap-x-4 gap-y-3 font-mono outline-none focus-visible:outline-2"
      onClick={(event) => {
        const target = (event.target as HTMLElement).closest<HTMLElement>("[data-pos]");
        if (target?.dataset.pos) onSelect(Number(target.dataset.pos));
      }}
      onKeyDown={(event) => {
        const steps: Record<string, number> = {
          ArrowRight: 1,
          ArrowLeft: -1,
          ArrowDown: GROUP_SIZE,
          ArrowUp: -GROUP_SIZE,
        };
        if (event.key in steps) {
          event.preventDefault();
          move(steps[event.key] ?? 0);
        } else if (event.key === "Home") {
          event.preventDefault();
          onSelect(start);
        } else if (event.key === "End") {
          event.preventDefault();
          onSelect(end);
        }
      }}
    >
      {groups.map((group) => (
        <div key={group.offset} className="flex flex-col gap-0.5">
          <span className="text-[10px] leading-none text-muted-foreground tabular-nums select-none">
            {formatInteger(start + group.offset)}
          </span>
          <span className="flex text-[15px] leading-6">
            {Array.from(group.text, (digit, index) => {
              const offset = group.offset + index;
              const isSelected = offset === selectedOffset;
              return (
                <span
                  key={offset}
                  data-pos={start + offset}
                  data-selected={isSelected || undefined}
                  data-highlighted={highlighted.has(offset) || undefined}
                  className={cn(
                    "w-[1.05ch] cursor-pointer text-center hover:bg-accent hover:text-foreground",
                    highlighted.has(offset) && "bg-cyan/20 text-cyan",
                    isSelected && "bg-primary text-primary-foreground hover:bg-primary",
                  )}
                >
                  {digit}
                </span>
              );
            })}
          </span>
        </div>
      ))}
    </div>
  );
});
