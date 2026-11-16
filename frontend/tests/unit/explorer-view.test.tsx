import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ExplorerView } from "@/components/explorer/explorer-view";

import { fixtures, mockApi, renderWithProviders, type RecordedRequest } from "../helpers";
import { currentUrl, setUrl } from "../router-mock";

const FIRST_500 = fixtures.digitsRange.digits;

/** Serves slices of the recorded first 500 digits, like the real endpoint. */
function digitsRoute(request: RecordedRequest) {
  const start = Number(request.query.get("start"));
  const count = Number(request.query.get("count"));
  const digits = FIRST_500.slice(start - 1, start - 1 + count);
  return {
    body: {
      start,
      end: start + digits.length - 1,
      count: digits.length,
      digits,
      total_digits: 1_000_000,
      has_previous: start > 1,
      has_next: true,
    },
  };
}

describe("ExplorerView", () => {
  it("loads the first digits and states the indexing convention", async () => {
    setUrl("/explorer?count=50");
    const requests = mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);

    const grid = await screen.findByTestId("digit-grid");
    expect(grid.querySelectorAll("[data-pos]")).toHaveLength(50);
    expect(grid).toHaveTextContent(FIRST_500.slice(0, 10));
    expect(
      screen.getByText(/Position 1 is the first digit after the decimal point/),
    ).toBeInTheDocument();
    expect(screen.getByText("Positions 1 to 50")).toBeInTheDocument();
    const range = requests.find((request) => request.path === "/digits/range");
    expect(range?.query.toString()).toBe("start=1&count=50");
  });

  it("pages forwards and backwards", async () => {
    setUrl("/explorer?count=50");
    mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);
    await screen.findByText("Positions 1 to 50");
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(currentUrl()).toBe("/explorer?count=50&start=51");
    expect(await screen.findByText("Positions 51 to 100")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /previous/i }));
    expect(await screen.findByText("Positions 1 to 50")).toBeInTheDocument();
  });

  it("inspects a clicked digit", async () => {
    setUrl("/explorer?count=50");
    mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);
    const grid = await screen.findByTestId("digit-grid");
    await userEvent.click(grid.querySelector('[data-pos="6"]') as Element);

    expect(await screen.findByTestId("inspector-position")).toHaveTextContent("6");
    expect(screen.getByTestId("inspector-digit")).toHaveTextContent(FIRST_500[5] as string);
    expect(screen.getByText(/6th digit after the decimal point/)).toBeInTheDocument();
  });

  it("highlights a sequence and counts its matches on the page", async () => {
    setUrl("/explorer?count=100&highlight=5");
    mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);
    const grid = await screen.findByTestId("digit-grid");
    const expected = [...FIRST_500.slice(0, 100)].filter((digit) => digit === "5").length;
    expect(grid.querySelectorAll("[data-highlighted]")).toHaveLength(expected);
    expect(screen.getByTestId("highlight-count")).toHaveTextContent(`occurs ${expected} times`);
  });

  it("highlights the whole sequence opened from a search result", async () => {
    setUrl("/explorer?count=50&select=3&length=4");
    mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);
    const grid = await screen.findByTestId("digit-grid");
    const marked = [...grid.querySelectorAll("[data-highlighted]")].map((cell) =>
      cell.getAttribute("data-pos"),
    );
    expect(marked).toEqual(["3", "4", "5", "6"]);
  });

  it("clamps a start beyond the dataset and a count beyond the limit", async () => {
    setUrl("/explorer?start=5000000&count=999999");
    const requests = mockApi({
      "GET /digits/range": { body: { ...fixtures.digitsRange, digits: "5" } },
    });
    renderWithProviders(<ExplorerView />);
    await waitFor(() => {
      const range = requests.find((request) => request.path === "/digits/range");
      expect(range?.query.toString()).toBe("start=1000000&count=1");
    });
  });

  it("refuses to request more digits than the server allows", async () => {
    mockApi({ "GET /digits/range": digitsRoute });
    renderWithProviders(<ExplorerView />);
    const input = await screen.findByLabelText("Digits to show");
    await userEvent.clear(input);
    await userEvent.type(input, "50000");
    expect(screen.getByRole("alert")).toHaveTextContent("At most 10,000 digits per page.");
    expect(screen.getByRole("button", { name: "Show digits" })).toBeDisabled();
  });
});
