import asyncio
from playwright.async_api import async_playwright
import os

async def save_login_state():
    print("啟動瀏覽器中...")
    async with async_playwright() as p:
        # 改用 Windows 內建真實的 Edge 瀏覽器，並隱藏自動化機器人特徵以繞過 Cloudflare
        browser = await p.chromium.launch(
            headless=False,
            channel="msedge", # 或改成 "chrome" (如果你想用 Google Chrome)
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        print("前往 ChatGPT 登入頁面...")
        await page.goto("https://chatgpt.com")
        print("\n=======================================================")
        print("請在彈出的瀏覽器中【手動登入 ChatGPT】。")
        print("登入完成，且看到出現對話輸入框後，請回到此終端機按下 Enter 鍵。")
        print("=======================================================\n")
        
        # 等待使用者確認
        await asyncio.to_thread(input, "按下 Enter 鍵以儲存登入狀態...")
        
        # 儲存登入狀態至 JSON 檔案中，下次就能免登入直接使用
        state_path = "chatgpt_state.json"
        await context.storage_state(path=state_path)
        print(f"\n✅ 登入狀態已成功儲存到 {os.path.abspath(state_path)}！")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_login_state())
