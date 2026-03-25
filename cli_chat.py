import asyncio
from playwright.async_api import async_playwright
import os
import sys

async def interactive_chat():
    state_path = "chatgpt_state.json"
    if not os.path.exists(state_path):
        print(f"❌ 找不到登入狀態 {state_path}！請先執行 python save_login.py")
        return

    async with async_playwright() as p:
        print("🤖 啟動 ChatGPT 核心引擎中 (使用 Edge 繞過防護)...")
        # 既然前面測試出必須要 False，那我們為了連續對話，就保持它開啟
        # 你可以把它縮到最小 (Minimize) 不去管它
        browser = await p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(storage_state=state_path)
        page = await context.new_page()
        
        print("🌐 正在連線到 ChatGPT 伺服器...")
        await page.goto("https://chatgpt.com")
        
        try:
            await page.wait_for_selector('#prompt-textarea', timeout=15000)
            print("✅ 連線成功！你現在可以開始隨意聊天了。")
            print("   （如果要結束程式，請輸入 'exit' 或 'quit'）\n")
            print("-" * 50)
        except Exception:
            print("❌ 連線失敗！登入狀態可能過期了或網頁尚未載入。")
            await browser.close()
            return
            
        while True:
            # 在終端機等待使用者輸入
            user_input = await asyncio.to_thread(input, "\n😎 你：")
            
            # 判斷是否要退出
            if user_input.strip().lower() in ['exit', 'quit']:
                print("\n👋 結束對話，正在關閉系統...")
                break
                
            if not user_input.strip():
                continue
            
            # 將問題輸入對話框並送出
            await page.fill('#prompt-textarea', user_input)
            await page.press('#prompt-textarea', 'Enter')
            
            print("🤖 ChatGPT 腦力激盪中...\r", end="")
            
            # 給它 6 秒鐘時間生成文字 (如果問題很難，你可以把這個秒數調高)
            await page.wait_for_timeout(6000)
            
            # 抓取畫面上的 AI 回覆
            reply_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
            
            if reply_elements:
                last_reply = reply_elements[-1]
                text = await last_reply.inner_text()
                print("\n🤖 ChatGPT：")
                print(text)
            else:
                print("\n❌ 目前抓不到回覆，它可能還在想，或者是被 Cloudflare 截斷了。")
                
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 強制結束程式！")
