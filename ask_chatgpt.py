import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def ask_chatgpt(question):
    state_path = "chatgpt_state.json"
    if not os.path.exists(state_path):
        print(f"❌ 找不到 {state_path}！")
        print("請先執行 python save_login.py 來登入並儲存狀態。")
        return

    async with async_playwright() as p:
        print("啟動背景瀏覽器中...")
        # 暫時先把 headless 改成 False，讓我們可以親眼看看畫面卡在哪裡
        browser = await p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # 載入我們儲存好的登入狀態
        context = await browser.new_context(storage_state=state_path)
        page = await context.new_page()
        
        print("前往 ChatGPT...")
        await page.goto("https://chatgpt.com")
        
        try:
            # 等待輸入框出現 (Playwright 會自動等待最多 15 秒)
            await page.wait_for_selector('#prompt-textarea', timeout=15000)
        except Exception:
            print("❌ 等不到輸入框！")
            print("可能有三個原因：")
            print("1. 網路太慢還沒載入完")
            print("2. 登入狀態 (Cookie) 已過期，請重新執行 save_login.py")
            print("3. ChatGPT 網頁改版了")
            await browser.close()
            return

        print(f"發送問題: {question}")
        await page.fill('#prompt-textarea', question)
        # 按下 Enter 送出
        await page.press('#prompt-textarea', 'Enter')
        
        print("等待 ChatGPT 回覆生成中... (大約需要 5-10 秒)")
        # 簡單粗暴地等待一段時間讓它打字，實務上可以寫得更精準去判斷生成結束
        await page.wait_for_timeout(8000) 
        
        # 抓取包含 assistant 回覆的元素
        reply_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
        
        if reply_elements:
            # 取最後一個元素 (也就是最新的一筆回覆)
            last_reply = reply_elements[-1]
            text = await last_reply.inner_text()
            print("\n============= ChatGPT 回覆 =============")
            print(text)
            print("========================================")
        else:
            print("❌ 找不到回覆文字，可能是網頁結構改變了！")

        await browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 允許從命令列帶入問題，例如: python ask_chatgpt.py "1+1等於多少"
        user_question = " ".join(sys.argv[1:])
    else:
        # 預設測試問題
        user_question = "請用繁體中文，用一句話形容寫程式的樂趣是什麼？"
        
    asyncio.run(ask_chatgpt(user_question))
