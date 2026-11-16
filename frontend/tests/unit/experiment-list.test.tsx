import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExperimentList, repeatHref, summarize } from "@/components/analysis/experiment-list";
import type { Experiment } from "@/lib/api/types";

import { fixtures } from "../helpers";

const experiments = fixtures.experiments.experiments as Experiment[];
const ofKind = (kind: string) => {
  const found = experiments.find((item) => item.kind === kind);
  if (!found) throw new Error(`fixture has no ${kind} experiment`);
  return found;
};

describe("repeatHref", () => {
  it("reopens a search with its pattern and range", () => {
    const search = ofKind("search");
    const url = new URL(repeatHref(search) ?? "", "http://localhost");
    expect(url.pathname).toBe("/search");
    expect(url.searchParams.get("q")).toBe(search.parameters.pattern);
    expect(url.searchParams.get("end")).toBe(String(search.parameters.end));
  });

  it("reopens a comparison with the recorded seed so it can be repeated exactly", () => {
    const comparison = ofKind("comparison");
    const url = new URL(repeatHref(comparison) ?? "", "http://localhost");
    expect(url.pathname).toBe("/lab");
    expect(url.searchParams.get("tab")).toBe("compare");
    expect(url.searchParams.get("seed")).toBe(String(comparison.parameters.seed));
    expect(url.searchParams.get("simulations")).toBe(String(comparison.parameters.simulations));
    expect(url.searchParams.get("count")).toBe(String(comparison.parameters.count));
  });

  it("reopens a test battery with its tests and correction", () => {
    const url = new URL(repeatHref(ofKind("statistics")) ?? "", "http://localhost");
    expect(url.searchParams.get("tab")).toBe("tests");
    expect(url.searchParams.get("correction")).toBe("holm");
    expect(url.searchParams.get("tests")?.split(",")).toContain("chi_square");
  });

  it("offers no link for an unknown kind", () => {
    expect(repeatHref({ ...ofKind("search"), kind: "future-kind" })).toBeNull();
  });
});

describe("summarize", () => {
  it("describes search results", () => {
    const search = ofKind("search");
    expect(summarize({ ...search, summary: { total_count: 1, first_position: 176451 } })).toBe(
      "1 occurrence, first at position 176,451",
    );
    expect(summarize({ ...search, summary: { total_count: 0, first_position: null } })).toBe(
      "No occurrences",
    );
  });

  it("reports the smallest adjusted p-value of a battery", () => {
    expect(summarize(ofKind("statistics"))).toMatch(/^4 tests, smallest adjusted p 0\.\d{4}$/);
  });

  it("reports the seed of a comparison", () => {
    expect(summarize(ofKind("comparison"))).toBe("5 simulations, seed 42");
  });
});

describe("ExperimentList", () => {
  it("renders each experiment with a repeat link", () => {
    render(<ExperimentList experiments={experiments} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(experiments.length);
    for (const experiment of experiments) {
      expect(screen.getAllByText(experiment.title).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByRole("link", { name: "Repeat" })).toHaveLength(experiments.length);
    expect(screen.getAllByText("Parameters and recorded results")).toHaveLength(experiments.length);
  });

  it("hides the raw parameters in compact mode", () => {
    render(<ExperimentList experiments={experiments} compact />);
    expect(screen.queryByText("Parameters and recorded results")).not.toBeInTheDocument();
  });
});
