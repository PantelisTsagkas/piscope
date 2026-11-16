import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DigitGrid } from "@/components/explorer/digit-grid";
import { ordinal } from "@/components/explorer/explorer-view";

const DIGITS = "14159265358979323846264338327950";

function setup(props: Partial<React.ComponentProps<typeof DigitGrid>> = {}) {
  const onSelect = vi.fn();
  render(
    <DigitGrid
      digits={DIGITS}
      start={1}
      selected={null}
      highlighted={new Set()}
      onSelect={onSelect}
      {...props}
    />,
  );
  return { onSelect, grid: screen.getByTestId("digit-grid") };
}

describe("DigitGrid", () => {
  it("renders every digit with its 1-based position", () => {
    const { grid } = setup();
    const cells = grid.querySelectorAll("[data-pos]");
    expect(cells).toHaveLength(DIGITS.length);
    expect(cells[0]).toHaveAttribute("data-pos", "1");
    expect(cells[0]).toHaveTextContent("1");
    expect(cells[5]).toHaveAttribute("data-pos", "6");
    expect(cells[5]).toHaveTextContent("2");
  });

  it("labels each group of ten with the position of its first digit", () => {
    setup({ start: 710_091 });
    expect(screen.getByText("710,091")).toBeInTheDocument();
    expect(screen.getByText("710,101")).toBeInTheDocument();
    expect(screen.getByText("710,121")).toBeInTheDocument();
  });

  it("reports the position of a clicked digit", async () => {
    const { onSelect, grid } = setup({ start: 101 });
    const cell = grid.querySelector('[data-pos="104"]');
    await userEvent.click(cell as Element);
    expect(onSelect).toHaveBeenCalledWith(104);
  });

  it("marks the selected and highlighted digits", () => {
    const { grid } = setup({ selected: 3, highlighted: new Set([0, 1]) });
    expect(grid.querySelector('[data-pos="3"]')).toHaveAttribute("data-selected", "true");
    expect(grid.querySelectorAll("[data-highlighted]")).toHaveLength(2);
    expect(grid.querySelectorAll("[data-selected]")).toHaveLength(1);
  });

  it("moves the selection with the arrow keys and stays inside the page", () => {
    const { onSelect, grid } = setup({ selected: 5 });
    fireEvent.keyDown(grid, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenLastCalledWith(6);
    fireEvent.keyDown(grid, { key: "ArrowDown" });
    expect(onSelect).toHaveBeenLastCalledWith(15);
    fireEvent.keyDown(grid, { key: "ArrowUp" });
    expect(onSelect).toHaveBeenLastCalledWith(1);
    fireEvent.keyDown(grid, { key: "End" });
    expect(onSelect).toHaveBeenLastCalledWith(DIGITS.length);
    fireEvent.keyDown(grid, { key: "Home" });
    expect(onSelect).toHaveBeenLastCalledWith(1);
  });

  it("starts from the first digit when nothing is selected", () => {
    const { onSelect, grid } = setup({ start: 501 });
    fireEvent.keyDown(grid, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenLastCalledWith(501);
  });
});

describe("ordinal", () => {
  it.each([
    [1, "1st"],
    [2, "2nd"],
    [3, "3rd"],
    [4, "4th"],
    [11, "11th"],
    [12, "12th"],
    [13, "13th"],
    [22, "22nd"],
    [113, "113th"],
    [762, "762nd"],
    [710_101, "710,101st"],
  ])("%i -> %s", (value, expected) => {
    expect(ordinal(value)).toBe(expected);
  });
});
