import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ExperimentsView } from "@/components/analysis/experiments-view";
import { DatasetStatus } from "@/components/layout/dataset-status";

import { errorBody, fixtures, mockApi, renderWithProviders } from "../helpers";

describe("ExperimentsView", () => {
  it("lists the recorded experiments", async () => {
    mockApi();
    renderWithProviders(<ExperimentsView />);
    expect(await screen.findByTestId("experiment-list")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Repeat" })).toHaveLength(
      fixtures.experiments.experiments.length,
    );
  });

  it("filters by kind on the server", async () => {
    const requests = mockApi();
    renderWithProviders(<ExperimentsView />);
    await screen.findByTestId("experiment-list");
    await userEvent.selectOptions(screen.getByLabelText("Kind"), "search");
    await waitFor(() =>
      expect(
        requests
          .filter((item) => item.path === "/experiments")
          .at(-1)
          ?.query.get("kind"),
      ).toBe("search"),
    );
  });

  it("asks for confirmation before clearing the log", async () => {
    const requests = mockApi();
    renderWithProviders(<ExperimentsView />);
    await screen.findByTestId("experiment-list");

    await userEvent.click(screen.getByRole("button", { name: /clear log/i }));
    expect(requests.some((item) => item.method === "DELETE")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(requests.some((item) => item.method === "DELETE")).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: /clear log/i }));
    await userEvent.click(screen.getByRole("button", { name: "Delete all" }));
    await waitFor(() => expect(requests.some((item) => item.method === "DELETE")).toBe(true));
  });

  it("shows an empty state when nothing has been run", async () => {
    mockApi({ "GET /experiments": { body: { experiments: [] } } });
    renderWithProviders(<ExperimentsView />);
    expect(await screen.findByText("No experiments yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /clear log/i })).toBeDisabled();
  });
});

describe("DatasetStatus", () => {
  it("shows the dataset size once loaded", async () => {
    mockApi();
    renderWithProviders(<DatasetStatus />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking dataset");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("1,000,000 digits"));
    expect(screen.getByRole("status")).toHaveTextContent("Checksums verified");
  });

  it("distinguishes a missing dataset from an unreachable API", async () => {
    mockApi({
      "GET /dataset/info": { status: 503, body: errorBody("dataset_unavailable", "no dataset") },
    });
    const first = renderWithProviders(<DatasetStatus />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("No dataset"));
    first.unmount();

    mockApi({ "GET /dataset/info": "network-error" });
    renderWithProviders(<DatasetStatus />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("API unreachable"));
  });
});
