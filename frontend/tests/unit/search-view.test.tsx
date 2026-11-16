import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SearchView } from "@/components/search/search-view";

import searchNone from "../fixtures/search-none.json";
import { errorBody, fixtures, mockApi, renderWithProviders } from "../helpers";
import { currentUrl, setUrl } from "../router-mock";

describe("SearchView", () => {
  it("prompts for a sequence before anything is searched", async () => {
    const requests = mockApi();
    renderWithProviders(<SearchView />);
    expect(await screen.findByText("Enter a sequence to search for")).toBeInTheDocument();
    expect(requests.some((request) => request.path === "/search")).toBe(false);
  });

  it("searches for the sequence in the URL and shows positions from the API", async () => {
    setUrl("/search?q=314159");
    const requests = mockApi();
    renderWithProviders(<SearchView />);

    expect(await screen.findByTestId("search-total")).toHaveTextContent("1");
    expect(screen.getByTestId("search-first")).toHaveTextContent("176,451");
    const table = screen.getByTestId("search-matches");
    expect(within(table).getByTestId("match-position")).toHaveTextContent("176,451");
    expect(within(table).getByText("first")).toBeInTheDocument();

    const search = requests.find((request) => request.path === "/search");
    expect(search?.body).toEqual({ pattern: "314159", start: 1, end: null, offset: 0, limit: 100 });
  });

  it("links each match to the explorer at that position", async () => {
    setUrl("/search?q=314159");
    mockApi();
    renderWithProviders(<SearchView />);
    const link = await screen.findByRole("link", { name: "View in explorer" });
    expect(link).toHaveAttribute("href", "/explorer?start=176351&select=176451&length=6");
  });

  it("strips non-digits as the user types and puts the search in the URL", async () => {
    setUrl("/search");
    mockApi();
    renderWithProviders(<SearchView />);
    const input = await screen.findByLabelText("Digit sequence");
    await userEvent.type(input, "3.14159");
    expect(input).toHaveValue("314159");
    await userEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(currentUrl()).toBe("/search?q=314159");
    expect(await screen.findByTestId("search-total")).toBeInTheDocument();
  });

  it("asks for a digit when the form is submitted empty", async () => {
    const requests = mockApi();
    renderWithProviders(<SearchView />);
    await userEvent.click(await screen.findByRole("button", { name: /search/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter at least one digit.");
    expect(requests.some((request) => request.path === "/search")).toBe(false);
  });

  it("rejects a range that ends before it starts", async () => {
    mockApi();
    renderWithProviders(<SearchView />);
    await userEvent.type(await screen.findByLabelText("Digit sequence"), "14");
    await userEvent.type(screen.getByLabelText("From position"), "500");
    await userEvent.type(screen.getByLabelText("To position"), "100");
    expect(screen.getByText("The end must not be before the start.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search/i })).toBeDisabled();
  });

  it("rejects a position beyond the dataset", async () => {
    mockApi();
    renderWithProviders(<SearchView />);
    await userEvent.type(await screen.findByLabelText("From position"), "2000000");
    await waitFor(() =>
      expect(screen.getByText("The last position is 1,000,000.")).toBeInTheDocument(),
    );
  });

  it("explains an absence without overstating it", async () => {
    setUrl("/search?q=99999999");
    mockApi({ "POST /search": { body: searchNone } });
    renderWithProviders(<SearchView />);
    expect(await screen.findByText("99999999 does not occur in this range")).toBeInTheDocument();
    expect(screen.getByText(/says nothing about the rest of pi/)).toBeInTheDocument();
    expect(screen.queryByTestId("search-matches")).not.toBeInTheDocument();
  });

  it("requests the next page with an offset", async () => {
    setUrl("/search?q=7");
    const page = {
      ...fixtures.search,
      pattern: "7",
      pattern_length: 1,
      total_count: 250,
      pageable_count: 250,
      limit: 100,
      has_more: true,
    };
    const requests = mockApi({ "POST /search": { body: page } });
    renderWithProviders(<SearchView />);
    await userEvent.click(await screen.findByRole("button", { name: /next/i }));
    expect(currentUrl()).toBe("/search?q=7&offset=100");
    await waitFor(() =>
      expect(requests.filter((request) => request.path === "/search").at(-1)?.body).toMatchObject({
        pattern: "7",
        offset: 100,
      }),
    );
  });

  it("says when stored positions were truncated", async () => {
    setUrl("/search?q=7");
    mockApi({
      "POST /search": {
        body: {
          ...fixtures.search,
          total_count: 9_000_000,
          pageable_count: 5_000_000,
          positions_truncated: true,
        },
      },
    });
    renderWithProviders(<SearchView />);
    expect(
      await screen.findByText(/The total is exact, but only the first 5,000,000/),
    ).toBeInTheDocument();
  });

  it("shows the API's message when the search is rejected", async () => {
    setUrl("/search?q=1");
    mockApi({
      "POST /search": {
        status: 422,
        body: errorBody("limit_exceeded", "pattern has 2000 digits; the limit is 1000"),
      },
    });
    renderWithProviders(<SearchView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("pattern has 2000 digits; the limit is 1000");
  });

  it("explains how to start the API when it cannot be reached", async () => {
    mockApi({ "GET /dataset/info": "network-error" });
    renderWithProviders(<SearchView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The API is not reachable");
    expect(alert).toHaveTextContent("uv run piscope-api");
  });

  it("explains how to generate digits when there is no dataset", async () => {
    mockApi({
      "GET /dataset/info": {
        status: 503,
        body: errorBody("dataset_unavailable", "no dataset found in data"),
      },
    });
    renderWithProviders(<SearchView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No digits are available");
    expect(alert).toHaveTextContent("uv run piscope-digits generate");
  });
});
