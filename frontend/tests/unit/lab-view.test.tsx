import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { LabView } from "@/components/analysis/lab-view";

import { errorBody, fixtures, mockApi, renderWithProviders } from "../helpers";
import { setUrl } from "../router-mock";

describe("LabView test battery", () => {
  it("states the limits of testing before any result", async () => {
    mockApi();
    renderWithProviders(<LabView />);
    expect(screen.getByText(/does not show that pi is random or normal/)).toBeInTheDocument();
    expect(await screen.findByText("No tests run yet")).toBeInTheDocument();
  });

  it("does not run anything until asked", async () => {
    const requests = mockApi();
    renderWithProviders(<LabView />);
    await screen.findByRole("button", { name: "Run tests" });
    expect(requests.some((request) => request.method === "POST")).toBe(false);
  });

  it("runs the selected tests and shows each result with its interpretation", async () => {
    const requests = mockApi();
    renderWithProviders(<LabView />);
    await userEvent.click(await screen.findByRole("button", { name: "Run tests" }));

    const results = await screen.findByTestId("battery-results");
    for (const result of fixtures.statistics.results) {
      const card = within(results).getByTestId(`test-result-${result.key}`);
      expect(card).toHaveTextContent(result.name);
      expect(card).toHaveTextContent(result.interpretation);
    }
    expect(
      within(results).getByText(fixtures.statistics.multiple_testing_note),
    ).toBeInTheDocument();
    expect(within(results).getByText(fixtures.statistics.scope_note)).toBeInTheDocument();
    expect(
      within(results).getByRole("img", { name: /autocorrelation at each lag/i }),
    ).toBeInTheDocument();

    const post = requests.find((request) => request.path === "/analysis/statistics");
    expect(post?.body).toEqual({
      start: 1,
      count: 1_000_000,
      tests: ["chi_square", "shannon_entropy", "autocorrelation", "runs", "ngram_blocks"],
      max_lag: 20,
      ngram_length: 2,
      runs_dichotomy: "high_low",
      correction: "holm",
    });
  });

  it("sends only the tests that are ticked", async () => {
    const requests = mockApi();
    renderWithProviders(<LabView />);
    await userEvent.click(await screen.findByLabelText("Shannon entropy"));
    await userEvent.click(screen.getByLabelText("Runs test"));
    await userEvent.click(screen.getByRole("button", { name: "Run tests" }));
    await waitFor(() => {
      const post = requests.find((request) => request.path === "/analysis/statistics");
      expect(post?.body).toMatchObject({
        tests: ["chi_square", "autocorrelation", "ngram_blocks"],
      });
    });
  });

  it("requires at least one test", async () => {
    mockApi();
    renderWithProviders(<LabView />);
    const form = await screen.findByRole("form", { name: "Test battery" });
    for (const checkbox of within(form).getAllByRole("checkbox")) await userEvent.click(checkbox);
    expect(within(form).getByRole("alert")).toHaveTextContent("Select at least one test.");
    expect(screen.getByRole("button", { name: "Run tests" })).toBeDisabled();
  });

  it("enforces the server's lag limit", async () => {
    mockApi();
    renderWithProviders(<LabView />);
    const lag = await screen.findByLabelText("Largest lag");
    await userEvent.clear(lag);
    await userEvent.type(lag, "500");
    expect(screen.getByText("At most 100.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run tests" })).toBeDisabled();
  });

  it("shows the API's message when a run fails", async () => {
    mockApi({
      "POST /analysis/statistics": {
        status: 422,
        body: errorBody("invalid_request", "the runs test needs both symbols to occur"),
      },
    });
    renderWithProviders(<LabView />);
    await userEvent.click(await screen.findByRole("button", { name: "Run tests" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "the runs test needs both symbols to occur",
    );
  });

  it("prefills the form from a repeat link", async () => {
    setUrl(
      "/lab?tab=tests&start=1001&count=5000&tests=chi_square,runs&max_lag=7&correction=bonferroni&runs_dichotomy=parity",
    );
    mockApi();
    renderWithProviders(<LabView />);
    expect(await screen.findByLabelText("Start position")).toHaveValue("1001");
    expect(screen.getByLabelText("Digits")).toHaveValue("5000");
    expect(screen.getByLabelText("Chi-square goodness of fit")).toBeChecked();
    expect(screen.getByLabelText("Shannon entropy")).not.toBeChecked();
    expect(screen.getByLabelText("Multiple-testing correction")).toHaveValue("bonferroni");
    expect(screen.getByLabelText("Runs split")).toHaveValue("parity");
  });
});

describe("LabView random comparison", () => {
  it("runs a seeded comparison and reports how to reproduce it", async () => {
    setUrl("/lab?tab=compare");
    const requests = mockApi();
    renderWithProviders(<LabView />);
    await userEvent.type(await screen.findByLabelText("Seed"), "42");
    await userEvent.click(screen.getByRole("button", { name: "Run comparison" }));

    const results = await screen.findByTestId("compare-results");
    expect(within(results).getByTestId("compare-seed-used")).toHaveTextContent("42");
    expect(within(results).getByText(fixtures.compare.note)).toBeInTheDocument();
    expect(within(results).getByText(fixtures.compare.source.method)).toBeInTheDocument();
    for (const statistic of fixtures.compare.statistics) {
      expect(within(results).getByTestId(`simulated-${statistic.key}`)).toHaveTextContent(
        "not a p-value",
      );
    }
    const post = requests.find((request) => request.path === "/analysis/compare");
    expect(post?.body).toMatchObject({ start: 1, count: 100_000, seed: 42, simulations: 20 });
  });

  it("sends a null seed when none is given, so the server chooses one", async () => {
    setUrl("/lab?tab=compare");
    const requests = mockApi();
    renderWithProviders(<LabView />);
    await userEvent.click(await screen.findByRole("button", { name: "Run comparison" }));
    await waitFor(() => {
      const post = requests.find((request) => request.path === "/analysis/compare");
      expect(post?.body).toMatchObject({ seed: null });
    });
  });

  it("rejects a seed too large to repeat exactly", async () => {
    setUrl("/lab?tab=compare");
    mockApi();
    renderWithProviders(<LabView />);
    await userEvent.type(await screen.findByLabelText("Seed"), "9007199254740993");
    expect(
      screen.getByText(/Enter a whole number from 0 to 9,007,199,254,740,991/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run comparison" })).toBeDisabled();
  });

  it("enforces the total simulated digit budget", async () => {
    setUrl("/lab?tab=compare");
    mockApi();
    renderWithProviders(<LabView />);
    const count = await screen.findByLabelText("Digits per sequence");
    await userEvent.clear(count);
    await userEvent.type(count, "1000000");
    const simulations = screen.getByLabelText("Simulated sequences");
    await userEvent.clear(simulations);
    await userEvent.type(simulations, "100");
    expect(screen.getByText("At most 50,000,000 simulated digits in total.")).toBeInTheDocument();
  });
});
