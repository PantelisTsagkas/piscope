import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, vi } from "vitest";

import { resetRouter } from "./router-mock";

// jsdom has no canvas, so charts are replaced by a labelled placeholder. What a chart
// draws is covered by the end-to-end tests, which run in a real browser.
vi.mock("@/components/charts/echart", () => ({
  EChart: ({ label }: { label: string }) =>
    createElement("div", { role: "img", "aria-label": label, "data-testid": "chart" }),
  axisStyle: {},
  tooltipStyle: {},
}));

vi.mock("next/navigation", async () => await import("./router-mock"));

afterEach(() => {
  cleanup();
  resetRouter();
  vi.unstubAllGlobals();
});
