import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { OverviewView } from "@/components/overview/overview-view";

import { errorBody, fixtures, mockApi, renderWithProviders } from "../helpers";
import { currentUrl, setUrl } from "../router-mock";

describe("OverviewView", () => {
  it("shows skeletons first, then values computed by the API", async () => {
    mockApi();
    renderWithProviders(<OverviewView />);
    expect(screen.getByTestId("stat-total-digits")).not.toHaveTextContent("1,000,000");

    await waitFor(() =>
      expect(screen.getByTestId("stat-total-digits")).toHaveTextContent("1,000,000"),
    );
    expect(screen.getByTestId("stat-analysed-digits")).toHaveTextContent("1,000,000");
    await waitFor(() =>
      expect(screen.getByTestId("stat-most-frequent")).toHaveTextContent(
        fixtures.frequency.most_frequent.join(", "),
      ),
    );
    expect(screen.getByTestId("stat-least-frequent")).toHaveTextContent(
      fixtures.frequency.least_frequent.join(", "),
    );
    expect(await screen.findByRole("img", { name: /how often each digit/i })).toBeInTheDocument();
  });

  it("renders every observation and the API's caveat", async () => {
    mockApi();
    renderWithProviders(<OverviewView />);
    for (const observation of fixtures.observations.observations) {
      const card = await screen.findByTestId(`observation-${observation.key}`);
      expect(card).toHaveTextContent(observation.value);
      expect(card).toHaveTextContent(observation.detail);
      expect(card).toHaveTextContent(observation.kind);
    }
    expect(screen.getByText(fixtures.observations.caveat)).toBeInTheDocument();
  });

  it("analyses the range given in the URL", async () => {
    setUrl("/?start=1001&count=5000");
    const requests = mockApi();
    renderWithProviders(<OverviewView />);
    await waitFor(() =>
      expect(screen.getByTestId("stat-analysed-digits")).toHaveTextContent("5,000"),
    );
    await waitFor(() => {
      const frequency = requests.find((request) => request.path === "/analysis/frequency");
      expect(frequency?.query.toString()).toBe("start=1001&count=5000");
    });
    const observations = requests.find((request) => request.path === "/analysis/observations");
    expect(observations?.query.toString()).toBe("start=1001&count=5000");
  });

  it("validates a new range before applying it", async () => {
    mockApi();
    renderWithProviders(<OverviewView />);
    const form = await screen.findByRole("form", { name: "Analysis range" });
    const digits = within(form).getByLabelText("Digits");
    await userEvent.clear(digits);
    await userEvent.type(digits, "2000000");
    expect(within(form).getByRole("alert")).toHaveTextContent("Only 1,000,000 digits remain");
    expect(within(form).getByRole("button", { name: "Apply range" })).toBeDisabled();

    await userEvent.clear(digits);
    await userEvent.type(digits, "250000");
    await userEvent.click(within(form).getByRole("button", { name: "Apply range" }));
    expect(currentUrl()).toBe("/?count=250000");
  });

  it("sends a quick search to the search page", async () => {
    mockApi();
    renderWithProviders(<OverviewView />);
    await userEvent.type(await screen.findByLabelText("Digit sequence to search for"), "2718x28");
    await userEvent.click(screen.getByRole("button", { name: /^search$/i }));
    expect(currentUrl()).toBe("/search?q=271828");
  });

  it("lists recent experiments, or says there are none", async () => {
    mockApi({ "GET /experiments": { body: { experiments: [] } } });
    renderWithProviders(<OverviewView />);
    expect(await screen.findByText("No experiments yet")).toBeInTheDocument();
  });

  it("replaces the dashboard with instructions when there is no dataset", async () => {
    mockApi({
      "GET /dataset/info": {
        status: 503,
        body: errorBody("dataset_unavailable", "no dataset found in data"),
      },
    });
    renderWithProviders(<OverviewView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("uv run piscope-digits generate");
    expect(screen.queryByTestId("stat-total-digits")).not.toBeInTheDocument();
  });

  it("keeps the rest of the page when one section fails", async () => {
    mockApi({
      "GET /analysis/observations": {
        status: 500,
        body: errorBody("internal_error", "unexpected server error"),
      },
    });
    renderWithProviders(<OverviewView />);
    expect(await screen.findByText("unexpected server error")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("stat-total-digits")).toHaveTextContent("1,000,000"),
    );
    expect(screen.getByTestId("experiment-list")).toBeInTheDocument();
  });
});
