import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TestResultCard } from "@/components/analysis/test-result-card";
import type { TestResult } from "@/lib/api/types";
import { formatPValue } from "@/lib/format";

import { fixtures } from "../helpers";

const results = fixtures.statistics.results as TestResult[];
const byKey = (key: string) => {
  const result = results.find((item) => item.key === key);
  if (!result) throw new Error(`fixture has no ${key} result`);
  return result;
};

describe("TestResultCard", () => {
  it("shows every required field of a hypothesis test", () => {
    const chi = byKey("chi_square");
    render(<TestResultCard result={chi} />);
    const card = screen.getByRole("article", { name: chi.name });

    expect(within(card).getByText("hypothesis test")).toBeInTheDocument();
    expect(within(card).getByText(`Observed ${chi.statistic_name}`)).toBeInTheDocument();
    expect(within(card).getByText("5.50908")).toBeInTheDocument();
    expect(within(card).getByText(chi.expected_description)).toBeInTheDocument();
    expect(within(card).getByText(formatPValue(chi.p_value))).toBeInTheDocument();
    expect(within(card).getByText(formatPValue(chi.adjusted_p_value))).toBeInTheDocument();
    expect(within(card).getByText("1,000,000")).toBeInTheDocument();
    expect(within(card).getByText("9 degrees of freedom")).toBeInTheDocument();
    expect(within(card).getByTestId("test-interpretation")).toHaveTextContent(chi.interpretation);
  });

  it("lists the null model, assumptions and limitations from the engine", () => {
    const runs = byKey("runs");
    render(<TestResultCard result={runs} />);
    expect(screen.getByText(runs.null_hypothesis)).toBeInTheDocument();
    for (const text of [...runs.assumptions, ...runs.limitations]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });

  it("does not invent a p-value for a descriptive measure", () => {
    const entropy = byKey("shannon_entropy");
    expect(entropy.p_value).toBeNull();
    render(<TestResultCard result={entropy} />);
    expect(screen.getByText("descriptive measure")).toBeInTheDocument();
    expect(screen.getByText("No p-value: this is a description, not a test.")).toBeInTheDocument();
    expect(screen.getAllByText("n/a")).toHaveLength(2);
  });

  it("says when a single test has no correction applied", () => {
    render(<TestResultCard result={{ ...byKey("chi_square"), adjusted_p_value: null }} />);
    expect(screen.getByText("Single test, so nothing to correct for here.")).toBeInTheDocument();
  });
});
