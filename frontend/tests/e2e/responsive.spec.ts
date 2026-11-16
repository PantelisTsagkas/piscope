import { expect, test } from "@playwright/test";

const PAGES = [
  { link: "Digit Explorer", path: "/explorer", heading: "Digit Explorer" },
  { link: "Sequence Search", path: "/search", heading: "Sequence Search" },
  { link: "Frequency Analysis", path: "/frequency", heading: "Frequency Analysis" },
  { link: "Statistical Lab", path: "/lab", heading: "Statistical Lab" },
  { link: "Experiments", path: "/experiments", heading: "Experiments" },
  { link: "About", path: "/about", heading: "About" },
  { link: "Overview", path: "/", heading: "Overview" },
];

test("navigation reaches every page at this screen size", async ({ page, isMobile }) => {
  await page.goto("/");
  for (const target of PAGES) {
    if (isMobile) {
      await page.getByRole("button", { name: "Open navigation menu" }).click();
      await page.getByRole("dialog").getByRole("link", { name: target.link }).click();
      await expect(page.getByRole("dialog")).toBeHidden();
    } else {
      await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: target.link }).click();
    }
    await expect(page.getByRole("heading", { level: 1, name: target.heading })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`${target.path.replace("/", "\\/")}$`));
  }
});

test("the layout switches between sidebar and menu button", async ({ page, isMobile }) => {
  await page.goto("/");
  const menuButton = page.getByRole("button", { name: "Open navigation menu" });
  if (isMobile) {
    await expect(menuButton).toBeVisible();
    await expect(page.locator("aside")).toBeHidden();
  } else {
    await expect(menuButton).toBeHidden();
    await expect(page.locator("aside")).toBeVisible();
  }
});

for (const path of ["/", "/explorer", "/search?q=14159", "/frequency", "/lab", "/about"]) {
  test(`${path} does not scroll sideways`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test("the active page is marked for assistive technology", async ({ page, isMobile }) => {
  test.skip(isMobile, "covered by the desktop project; the menu is closed on mobile");
  await page.goto("/search");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Sequence Search" })).toHaveAttribute("aria-current", "page");
  await expect(nav.getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current", "page");
});
