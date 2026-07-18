"""
Тест: получение Qrator-кук через Playwright.
Запуск: python test_playwright.py

Успех = в выводе есть qrator_jsid2.
Тогда можно интегрировать автообновление в бот.
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        print("Открываем domclick.ru...")
        await page.goto("https://domclick.ru", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=20000)
        await asyncio.sleep(5)

        cookies = await context.cookies()
        print(f"\nПолучено кук: {len(cookies)}")
        for c in cookies:
            print(f"  {c['name']} = {c['value'][:80]}")

        qrator_jsid2 = next((c for c in cookies if c["name"] == "qrator_jsid2"), None)
        print()
        if qrator_jsid2:
            print("✅ qrator_jsid2 получен — Playwright работает, можно интегрировать в бот")
            # Собираем cookie-строку для /setcookie
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            print(f"\nCookie string для /setcookie:\n{cookie_str[:200]}...")
        else:
            print("❌ qrator_jsid2 не получен — Qrator всё ещё детектирует браузер")
            print("   Попробуй: headless=False + Xvfb на VPS")

        await browser.close()


asyncio.run(main())
