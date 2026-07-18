"""
Тест: получение Qrator-кук через patchright (патченый Playwright без маркеров автоматизации).
Запуск:
    pip install patchright
    patchright install chromium
    python test_playwright.py

Успех = в выводе есть qrator_jsid2.
"""
import asyncio
from patchright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        print("navigator.webdriver:", await page.evaluate("navigator.webdriver"))

        # Перехватываем запросы и ответы Qrator challenge
        async def on_response(response):
            if "qrator" in response.url:
                print(f"\n[RESPONSE] {response.url[:100]}")
                print(f"  status: {response.status}")
                print(f"  headers: {dict(response.headers)}")
                try:
                    body = await response.text()
                    print(f"  body: {body[:200]}")
                except Exception:
                    pass

        page.on("response", on_response)

        print("Открываем domclick.ru...")
        try:
            await page.goto("https://domclick.ru", timeout=30000)
        except Exception:
            pass

        await asyncio.sleep(10)

        cookies = await context.cookies()
        print(f"\nПолучено кук: {len(cookies)}")
        for c in cookies:
            print(f"  {c['name']} = {c['value'][:80]}")

        qrator_jsid2 = next((c for c in cookies if c["name"] == "qrator_jsid2"), None)
        print()
        if qrator_jsid2:
            print("✅ qrator_jsid2 получен — patchright работает, можно интегрировать в бот")
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            print(f"\nCookie string:\n{cookie_str}")
        else:
            print("❌ qrator_jsid2 не получен")

        await browser.close()


asyncio.run(main())
