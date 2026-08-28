import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const route of ["/", "/signup", "/signin"]) {
  test(
    `${route} is usable and has no serious accessibility violations`,
    async ({ page }) => {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      const results = await new AxeBuilder({ page })
        .disableRules(["color-contrast"])
        .analyze();
      expect(
        results.violations.filter((item) =>
          ["serious", "critical"].includes(item.impact ?? ""),
        ),
      ).toEqual([]);
    },
  );
}

test("landing navigation reaches account creation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/signup$/);
  await expect(
    page.getByRole("heading", { name: /create your workspace/i }),
  ).toBeVisible();
});
