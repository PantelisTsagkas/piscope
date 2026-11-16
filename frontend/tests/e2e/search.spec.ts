import { expect, test } from "@playwright/test";

import { REFERENCE_DIGITS, referencePositions, withSeparators } from "./reference";

/** Searches the first 10,000 digits, where the reference file gives the right answer. */
async function searchReferenceRange(page: import("@playwright/test").Page, pattern: string) {
  await page.goto("/search");
  await page.getByLabel("Digit sequence").fill(pattern);
  await page.getByLabel("To position").fill(String(REFERENCE_DIGITS.length));
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("search-total")).toBeVisible();
}

test.describe("sequence search", () => {
  // "00" includes overlapping matches wherever the digits contain 000.
  for (const pattern of ["999999", "14159", "00", "7"]) {
    test(`finds the correct positions of ${pattern}`, async ({ page }) => {
      const expected = referencePositions(pattern);
      expect(expected.length).toBeGreaterThan(0);
      await searchReferenceRange(page, pattern);

      await expect(page.getByTestId("search-total")).toHaveText(withSeparators(expected.length));
      await expect(page.getByTestId("search-first")).toHaveText(withSeparators(expected[0]!));
      const shown = await page.getByTestId("match-position").allTextContents();
      expect(shown.map((text) => Number(text.replaceAll(",", "")))).toEqual(expected.slice(0, 100));
      await expect(page.getByTestId("search-time")).toHaveText(/ms|s$/);
    });
  }

  test("reports gaps between consecutive occurrences", async ({ page }) => {
    const expected = referencePositions("123");
    expect(expected.length).toBeGreaterThan(2);
    await searchReferenceRange(page, "123");
    const rows = page.getByTestId("search-matches").locator("tbody tr");
    await expect(rows.nth(0).locator("td").nth(2)).toHaveText("first");
    await expect(rows.nth(1).locator("td").nth(2)).toHaveText(
      withSeparators(expected[1]! - expected[0]!),
    );
    await expect(rows.nth(2).locator("td").nth(2)).toHaveText(
      withSeparators(expected[2]! - expected[1]!),
    );
  });

  test("pages through a long result list", async ({ page }) => {
    const expected = referencePositions("7");
    expect(expected.length).toBeGreaterThan(200);
    await searchReferenceRange(page, "7");
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page).toHaveURL(/offset=100/);
    await expect(page.getByText(/Showing 101 to 200 of/)).toBeVisible();
    const shown = await page.getByTestId("match-position").allTextContents();
    expect(shown.map((text) => Number(text.replaceAll(",", "")))).toEqual(expected.slice(100, 200));
  });

  test("opens a match in the explorer with the sequence highlighted", async ({ page }) => {
    const pattern = "999999";
    const [first] = referencePositions(pattern);
    await searchReferenceRange(page, pattern);
    await page.getByRole("link", { name: "View in explorer" }).first().click();
    await expect(page).toHaveURL(/\/explorer\?/);
    await expect(page.getByTestId("inspector-position")).toHaveText(withSeparators(first!));
    const marked = await page
      .getByTestId("digit-grid")
      .locator("[data-highlighted]")
      .allTextContents();
    expect(marked.join("")).toBe(pattern);
  });

  test("handles a sequence that does not occur", async ({ page }) => {
    const pattern = "00000000";
    expect(referencePositions(pattern)).toHaveLength(0);
    await searchReferenceRange(page, pattern);
    await expect(page.getByTestId("search-total")).toHaveText("0");
    await expect(page.getByText(`${pattern} does not occur in this range`)).toBeVisible();
    await expect(page.getByText(/says nothing about the rest of pi/)).toBeVisible();
  });

  test("rejects input that is not a digit sequence", async ({ page }) => {
    await page.goto("/search");
    await page.getByLabel("Digit sequence").fill("abc");
    await expect(page.getByLabel("Digit sequence")).toHaveValue("");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByText("Enter at least one digit.")).toBeVisible();
    await expect(page).toHaveURL(/\/search$/);
  });
});
