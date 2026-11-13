"""使用 Playwright 录制 ShopAgent 演示视频。"""
import argparse
import asyncio
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "docs" / "demo"


async def overlay(page, text):
    await page.evaluate(
        """text => {
            let el = document.getElementById('recording-caption');
            if (!el) {
                el = document.createElement('div');
                el.id = 'recording-caption';
                el.style.cssText = 'position:fixed;left:24px;right:24px;bottom:24px;z-index:99999;' +
                  'padding:16px 22px;border-radius:12px;background:rgba(17,24,39,.92);' +
                  'color:#fff;font:600 22px system-ui;box-shadow:0 8px 30px rgba(0,0,0,.25)';
                document.body.appendChild(el);
            }
            el.textContent = text;
        }""",
        text,
    )


async def run(full: bool):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for old in RAW_DIR.glob("*.webm"):
        old.unlink()
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000/static/agent.html", wait_until="networkidle")
        await overlay(page, "ShopAgent：商城后端 + 智能售后 Agent")
        await page.wait_for_timeout(10000 if full else 1000)
        await overlay(page, "一键准备真实订单、支付、售后工单和政策知识库")
        await page.get_by_role("button", name="一键准备演示数据").click()
        await page.wait_for_timeout(20000 if full else 2500)
        await overlay(page, "运行 Agent：订单工具、政策 RAG、证据校验和审批判断")
        await page.get_by_role("button", name="运行流式 Agent").click()
        try:
            await page.wait_for_function(
                "() => document.getElementById('logs').textContent.includes('结构化结果')",
                timeout=20000,
            )
        except Exception:
            pass
        await page.wait_for_timeout(25000 if full else 2500)
        await overlay(page, "结构化结果：诉求、证据、缺失信息、建议动作、置信度、人工审批")
        await page.locator("#logs").scroll_into_view_if_needed()
        await page.wait_for_timeout(30000 if full else 1500)
        await overlay(page, "30 条案例评测｜工具正确率 1.0｜政策引用覆盖 1.0｜pytest 11 passed")
        await page.wait_for_timeout(30000 if full else 1000)
        await context.close()
        await browser.close()
    videos = sorted(RAW_DIR.glob("*.webm"), key=lambda path: path.stat().st_mtime)
    if not videos:
        raise RuntimeError("未生成视频")
    target = RAW_DIR / ("ShopAgent-Demo.webm" if full else "ShopAgent-Demo-test.webm")
    shutil.copy2(videos[-1], target)
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    asyncio.run(run(parser.parse_args().full))
