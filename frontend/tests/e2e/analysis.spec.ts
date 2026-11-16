import { expect, test } from "@playwright/test";

import { chartCanvas, referenceCounts, withSeparators } from "./reference";

test.describe("frequency analysis", () => {
  test("digit counts match an independent count", async ({ page }) => {
    const counts = referenceCounts(10_000);
    await page.goto("/frequency?count=10000");
    const table = page.getByTestId("frequency-table");
    for (const [digit, count] of counts.entries()) {
      await expect(table.getByTestId(`frequency-row-${digit}`).locator("td").nth(1)).toHaveText(
        withSeparators(count),
      );
    }
  });

  test("draws its charts and lists n-grams", async ({ page }) => {
    await page.goto("/frequency");
    await expect(chartCanvas(page, /how often each digit/i)).toBeVisible();
    await expect(chartCanvas(page, /100 two-digit sequences/i)).toBeVisible();
    await expect(chartCanvas(page, /digit counts by window/i)).toBeVisible();
    await expect(page.getByTestId("ngram-table").locator("tbody tr")).toHaveCount(25);

    await page.getByLabel("Length (n)").selectOption("3");
    await expect(page.getByText(/of 1,000$/)).toBeVisible();
    await expect(
      page.getByTestId("ngram-table").locator("tbody tr").first().locator("td").nth(1),
    ).toHaveText(/^\d{3}$/);
    await expect(page.getByTestId("longest-runs").locator("tbody tr")).toHaveCount(10);
  });
});

test.describe("statistical lab", () => {
  test("runs the test battery and explains each result", async ({ page }) => {
    await page.goto("/lab");
    await expect(page.getByText(/does not show that pi is random or normal/)).toBeVisible();
    await page.getByRole("button", { name: "Run tests" }).click();

    const results = page.getByTestId("battery-results");
    await expect(results).toBeVisible();
    for (const key of [
      "chi_square",
      "shannon_entropy",
      "autocorrelation",
      "runs",
      "ngram_blocks",
    ]) {
      const card = results.getByTestId(`test-result-${key}`);
      await expect(card).toBeVisible();
      await expect(card.getByTestId("test-interpretation")).not.toBeEmpty();
      await expect(card.getByText("Sample size", { exact: true })).toBeVisible();
    }
    // Entropy is a description, so it must not be given a p-value.
    await expect(results.getByTestId("test-result-shannon_entropy")).toContainText(
      "descriptive measure",
    );
    await expect(results.getByText(/passing statistical tests does not establish/i)).toBeVisible();
    await expect(chartCanvas(results, /autocorrelation at each lag/i)).toBeVisible();
  });

  test("a seeded random comparison is reproducible", async ({ page }) => {
    const run = async () => {
      await page.goto("/lab?tab=compare");
      await page.getByLabel("Digits per sequence").fill("20000");
      await page.getByLabel("Simulated sequences").fill("10");
      await page.getByLabel("Seed").fill("20261116");
      await page.getByRole("button", { name: "Run comparison" }).click();
      const results = page.getByTestId("compare-results");
      await expect(results.getByTestId("compare-seed-used")).toHaveText("20261116");
      await expect(results.getByText(/not that pi is random/)).toBeVisible();
      return results.getByTestId("compare-table").locator("tbody").innerText();
    };
    const first = await run();
    const second = await run();
    expect(second).toBe(first);
  });

  test("experiments are logged and can be repeated", async ({ page }) => {
    await page.goto("/lab?tab=compare");
    await page.getByLabel("Digits per sequence").fill("5000");
    await page.getByLabel("Simulated sequences").fill("3");
    await page.getByLabel("Seed").fill("777123");
    await page.getByRole("button", { name: "Run comparison" }).click();
    await expect(page.getByTestId("compare-results")).toBeVisible();

    await page.goto("/experiments");
    await page.getByLabel("Kind").selectOption("comparison");
    const entry = page
      .getByTestId("experiment-list")
      .locator("li")
      .filter({ hasText: "seed 777123" })
      .first();
    await expect(entry).toBeVisible();
    await entry.getByRole("link", { name: "Repeat" }).click();
    await expect(page).toHaveURL(/\/lab\?tab=compare/);
    await expect(page.getByLabel("Seed")).toHaveValue("777123");
    await expect(page.getByLabel("Digits per sequence")).toHaveValue("5000");
  });
});

test("about page reports provenance from the dataset", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText(/has not been proven/)).toBeVisible();
  await expect(page.getByTestId("about-provenance")).toContainText("chudnovsky-binary-splitting");
  await expect(page.getByText("gauss-legendre", { exact: true })).toBeVisible();
  await expect(page.getByTestId("about-indexing")).toContainText(
    "position 1 is the first digit after the decimal point",
  );
});
