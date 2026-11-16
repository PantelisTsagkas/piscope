import { expect, test } from "@playwright/test";

import { REFERENCE_DIGITS, referencePositions } from "./reference";

test.describe("digit explorer", () => {
  test("shows the reference digits at the right positions", async ({ page }) => {
    await page.goto("/explorer");
    const grid = page.getByTestId("digit-grid");
    await expect(grid.locator("[data-pos]")).toHaveCount(1000);
    const shown = (await grid.locator("[data-pos]").allTextContents()).join("");
    expect(shown).toBe(REFERENCE_DIGITS.slice(0, 1000));
    await expect(grid.locator('[data-pos="1"]')).toHaveText(REFERENCE_DIGITS[0]!);
    await expect(page.getByText(/the leading 3 is not counted/)).toBeVisible();
  });

  test("navigates between sections and jumps to a position", async ({ page }) => {
    await page.goto("/explorer");
    await expect(page.getByText("Positions 1 to 1,000")).toBeVisible();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Positions 1,001 to 2,000")).toBeVisible();
    const shown = (
      await page.getByTestId("digit-grid").locator("[data-pos]").allTextContents()
    ).join("");
    expect(shown).toBe(REFERENCE_DIGITS.slice(1000, 2000));

    await page.getByRole("button", { name: "Previous" }).click();
    await expect(page.getByText("Positions 1 to 1,000")).toBeVisible();

    await page.getByLabel("Start position").fill("9951");
    await page.getByLabel("Digits to show").fill("50");
    await page.getByRole("button", { name: "Show digits" }).click();
    await expect(page.getByText("Positions 9,951 to 10,000")).toBeVisible();
    const tail = (
      await page.getByTestId("digit-grid").locator("[data-pos]").allTextContents()
    ).join("");
    expect(tail).toBe(REFERENCE_DIGITS.slice(9950, 10_000));
  });

  test("inspects a digit by click and by keyboard", async ({ page }) => {
    await page.goto("/explorer?count=100");
    const grid = page.getByTestId("digit-grid");
    await grid.locator('[data-pos="42"]').click();
    await expect(page.getByTestId("inspector-position")).toHaveText("42");
    await expect(page.getByTestId("inspector-digit")).toHaveText(REFERENCE_DIGITS[41]!);

    await grid.focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByTestId("inspector-position")).toHaveText("43");
    await expect(page.getByTestId("inspector-digit")).toHaveText(REFERENCE_DIGITS[42]!);
    await page.keyboard.press("ArrowDown");
    await expect(page.getByTestId("inspector-position")).toHaveText("53");
  });

  test("highlights every match of a sequence on the page", async ({ page }) => {
    const pattern = "99";
    const expected = referencePositions(pattern, REFERENCE_DIGITS.slice(0, 1000));
    expect(expected.length).toBeGreaterThan(0);

    await page.goto("/explorer");
    await page.getByLabel("Highlight sequence").fill(pattern);
    await page.getByRole("button", { name: "Show digits" }).click();
    await expect(page.getByTestId("highlight-count")).toContainText(
      `occurs ${expected.length} time${expected.length === 1 ? "" : "s"}`,
    );
    const marked = await page
      .getByTestId("digit-grid")
      .locator("[data-highlighted]")
      .evaluateAll((cells) => cells.map((cell) => Number(cell.getAttribute("data-pos"))));
    const covered = new Set(expected.flatMap((position) => [position, position + 1]));
    expect(marked).toEqual([...covered].sort((a, b) => a - b));
  });
});
