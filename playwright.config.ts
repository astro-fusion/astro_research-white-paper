// Smoke test of the rendered website. Run `quarto render --to html` first;
// the test serves _site/ statically and opens every explorer.
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.SITE_PORT || 4173);
const OUT = process.env.SITE_SMOKE_OUT || join(tmpdir(), "astro-research-site-smoke");

export default defineConfig({
  testDir: "tests/site",
  outputDir: join(OUT, "results"),
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  workers: 2,
  reporter: process.env.CI ? [["list"], ["html", { open: "never", outputFolder: join(OUT, "report") }]] : "list",
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `node tests/site/serve.mjs _site ${PORT}`,
    url: `http://127.0.0.1:${PORT}/site/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
