// Every explorer renders its chart with its default filters and logs no
// console errors (ADR-001: "a Playwright smoke that loads each page and
// asserts the explorer renders with its default filter").
import { test, expect } from "@playwright/test";

const PAGES: Array<[string, string[]]> = [
  ["site/index.html", ["#study-status .af-status-item"]],
  ["site/explore/index.html", ["table"]],
  ["site/explore/sky-events.html", ["#sky-events-chart svg", "#sky-gauge svg"]],
  ["site/explore/effects.html", ["#effects-chart svg"]],
  ["site/explore/markets.html", ["#markets-price svg", "#markets-dist svg"]],
  ["site/explore/atlas.html", ["#atlas-map svg path", "#atlas-events svg", "#atlas-dasha svg"]],
  ["site/principles.html", ["#principles-chart svg", "#principles-drawer"]],
  ["site/explore/numerology.html", ["#numerology-chart svg"]],
];

for (const [path, selectors] of PAGES) {
  test(`${path} renders with its default filters`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
    page.on("response", (res) => {
      if (res.status() >= 400) errors.push(`${res.status()} ${res.url()}`);
    });
    await page.goto(path, { waitUntil: "networkidle" });
    for (const sel of selectors) {
      await expect(page.locator(sel).first()).toBeVisible({ timeout: 30_000 });
    }
    await expect(page.locator(".observablehq--error")).toHaveCount(0);
    if (!path.endsWith("explore/index.html")) {
      await expect(page.locator(".af-provenance").first()).toBeVisible();
    }
    expect(errors, errors.join("\n")).toEqual([]);
  });
}

test("brushing the event panel updates the readout", async ({ page }) => {
  await page.goto("site/explore/sky-events.html", { waitUntil: "networkidle" });
  const panel = page.locator("#sky-events-chart svg").last();
  await expect(panel).toBeVisible({ timeout: 30_000 });
  await panel.scrollIntoViewIfNeeded();
  const box = await panel.boundingBox();
  if (!box) throw new Error("no event panel");
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.5, { steps: 5 });
  await page.mouse.up();
  await expect(page.locator("p.af-caption", { hasText: "(brushed)" })).toBeVisible();
});
