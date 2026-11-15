import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const frontendDir = path.resolve(import.meta.dirname, "..");
const outputDir = path.resolve(frontendDir, "..", "docs", "demo");
const videoDir = path.join(outputDir, "raw");

await mkdir(videoDir, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: videoDir, size: { width: 1440, height: 900 } },
});

const page = await context.newPage();
const video = page.video();

try {
  await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded" });
  await page.locator("#email").fill("demo@shopagent.example.com");
  await page.locator("#password").fill("ShopAgent123!");
  await page.getByRole("button", { name: "Login", exact: true }).click();
  try {
    await page.waitForFunction(() => !location.pathname.endsWith("/login"), null, {
      timeout: 20_000,
    });
  } catch (error) {
    await page.screenshot({ path: path.join(outputDir, "login-failure.png") });
    throw new Error(`Login failed at ${page.url()}: ${await page.locator("body").innerText()}`, {
      cause: error,
    });
  }
  await page.waitForTimeout(5000);

  await page.goto("http://localhost:3000/shop", { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "售后 Agent 工作台" }).waitFor();
  await page.getByRole("button", { name: /completed/ }).first().click();
  await page.waitForTimeout(8000);

  const askButton = page.locator("button").filter({ hasText: "让 Agent 研判" }).first();
  await askButton.focus();
  await page.keyboard.press("Enter");
  await page.getByText(/完整售后研判/).waitFor({ timeout: 30_000 });
  await page.getByText(/诉求判断/).first().waitFor({ timeout: 180_000 });
  await page.waitForTimeout(18_000);

  await page.screenshot({
    path: path.join(outputDir, "shopagent-workbench.png"),
    fullPage: true,
  });
  await page.waitForTimeout(35_000);
} finally {
  await context.close();
  await browser.close();
}

if (!video) throw new Error("Playwright did not create a video handle");
const rawVideoPath = await video.path();
console.log(rawVideoPath);
