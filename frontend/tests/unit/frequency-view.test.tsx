import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FrequencyView } from "@/components/analysis/frequency-view";
import { formatInteger } from "@/lib/format";

import { errorBody, fixtures, mockApi, renderWithProviders } from "../helpers";
import { setUrl } from "../router-mock";

describe("FrequencyView", () => {
  it("shows the count of every digit exactly as the API reports it", async () => {
    mockApi();
    renderWithProviders(<FrequencyView />);
    const table = await screen.findByTestId("frequency-table");
    for (const item of fixtures.frequency.digits) {
      const row = within(table).getByTestId(`frequency-row-${item.digit}`);
      expect(row).toHaveTextContent(formatInteger(item.count));
    }
    expect(screen.getByText(fixtures.frequency.note)).toBeInTheDocument();
  });

  it("uses the range from the URL for every section", async () => {
    setUrl("/frequency?start=501&count=20000");
    const requests = mockApi();
    renderWithProviders(<FrequencyView />);
    await screen.findByTestId("frequency-table");
    await screen.findByTestId("longest-runs");
    for (const path of [
      "/analysis/frequency",
      "/analysis/ngrams",
      "/analysis/windows",
      "/analysis/runs",
    ]) {
      const request = requests.find((item) => item.path === path);
      expect(request?.query.get("start"), path).toBe("501");
      expect(request?.query.get("count"), path).toBe("20000");
    }
  });

  it("requests a different n-gram length and order", async () => {
    const requests = mockApi();
    renderWithProviders(<FrequencyView />);
    await screen.findByTestId("ngram-table");
    await userEvent.selectOptions(screen.getByLabelText("Length (n)"), "4");
    await userEvent.selectOptions(screen.getByLabelText("Order"), "count_asc");
    await waitFor(() => {
      const last = requests.filter((item) => item.path === "/analysis/ngrams").at(-1);
      expect(last?.query.get("n")).toBe("4");
      expect(last?.query.get("sort")).toBe("count_asc");
      expect(last?.query.get("offset")).toBe("0");
    });
  });

  it("offers only n-gram lengths the server allows", async () => {
    mockApi();
    renderWithProviders(<FrequencyView />);
    const select = await screen.findByLabelText("Length (n)");
    const values = within(select)
      .getAllByRole("option")
      .map((option) => option.getAttribute("value"));
    expect(values).toEqual(["1", "2", "3", "4", "5", "6"]);
  });

  it("shows the block test with its caveats next to the n-gram table", async () => {
    mockApi();
    renderWithProviders(<FrequencyView />);
    expect(await screen.findByText(fixtures.ngrams.note)).toBeInTheDocument();
    expect(screen.getByTestId("test-result-ngram_blocks")).toHaveTextContent(
      fixtures.ngrams.block_test.interpretation,
    );
  });

  it("puts extreme window cells next to the number expected by chance", async () => {
    mockApi();
    renderWithProviders(<FrequencyView />);
    const stat = await screen.findByTestId("cells-beyond-two");
    expect(stat).toHaveTextContent(
      `${fixtures.windows.cells_beyond_two} of ${fixtures.windows.cells}`,
    );
    expect(screen.getByText(fixtures.windows.note)).toBeInTheDocument();
  });

  it("lists the longest runs with links into the explorer", async () => {
    mockApi();
    renderWithProviders(<FrequencyView />);
    const table = await screen.findByTestId("longest-runs");
    const longest = fixtures.runs.longest[0];
    if (!longest) throw new Error("fixture has no runs");
    expect(
      within(table).getByText(String(longest.digit).repeat(longest.length)),
    ).toBeInTheDocument();
    expect(within(table).getAllByRole("link", { name: "View in explorer" })[0]).toHaveAttribute(
      "href",
      `/explorer?start=${longest.position - 100}&select=${longest.position}&length=${longest.length}`,
    );
  });

  it("reports a failed section without hiding the others", async () => {
    mockApi({
      "GET /analysis/windows": {
        status: 422,
        body: errorBody("limit_exceeded", "windows 500 exceeds the limit of 200"),
      },
    });
    renderWithProviders(<FrequencyView />);
    expect(await screen.findByText("windows 500 exceeds the limit of 200")).toBeInTheDocument();
    expect(await screen.findByTestId("frequency-table")).toBeInTheDocument();
  });
});
