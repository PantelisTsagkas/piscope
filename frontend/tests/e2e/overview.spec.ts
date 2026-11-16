import { expect, test } from "@playwright/test";

import { chartCanvas, referenceCounts, withSeparators } from "./reference";

test.describe("overview dashboard", () => {
  test("loads real dataset information and computed results", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();

    const total = page.getByTestId("stat-total-digits");
    await expect(total).toHaveText(/^[\d,]+$/);
    const digits = Number((await total.textContent())?.replaceAll(",", ""));
    expect(digits).toBeGreaterThanOrEqual(1_000_000);

    await expect(page.getByTestId("stat-most-frequent")).toHaveText(/^\d(, \d)*$/);
    await expect(page.getByTestId("stat-least-frequent")).toHaveText(/^\d(, \d)*$/);
    await expect(page.getByTestId("observation-chi_square")).toContainText("p = ");
    await expect(page.getByTestId("observation-longest_run")).toBeVisible();
    await expect(page.getByText(/not evidence of hidden structure in pi/)).toBeVisible();
    await expect(chartCanvas(page, /how often each digit/i)).toBeVisible();
  });

  test("most and least frequent digits match an independent count", async ({ page }) => {
    const counts = referenceCounts(10_000);
    const most = counts.indexOf(Math.max(...counts));
    const least = counts.indexOf(Math.min(...counts));
    // The comparison below is only meaningful if the reference has no ties.
    expect(counts.filter((count) => count === counts[most])).toHaveLength(1);
    expect(counts.filter((count) => count === counts[least])).toHaveLength(1);

    await page.goto("/?count=10000");
    await expect(page.getByTestId("stat-analysed-digits")).toHaveText("10,000");
    await expect(page.getByTestId("stat-most-frequent")).toHaveText(String(most));
    await expect(page.getByTestId("stat-least-frequent")).toHaveText(String(least));
    await expect(page.getByText(`${withSeparators(counts[most]!)} occurrences`)).toBeVisible();
  });

  test("quick search opens the search page with results", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Digit sequence to search for").fill("14159");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page).toHaveURL(/\/search\?q=14159$/);
    await expect(page.getByTestId("search-first")).toHaveText("1");
  });

  test("a search appears under recent experiments", async ({ page }) => {
    // Unique to this test so a cached result cannot hide the new log entry.
    await page.goto("/search?q=8675309");
    await expect(page.getByTestId("search-total")).toBeVisible();
    await page.goto("/");
    await expect(page.getByTestId("experiment-list")).toContainText("Search for 8675309");
  });
});
