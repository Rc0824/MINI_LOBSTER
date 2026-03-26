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
            
            print("🤖 ChatGPT 腦力激盪中 (自動等待輸出直到完成)...\r", end="", flush=True)
            
            # 建立動態等待機制：當回覆文字超過 2 秒沒變時，當作它生成完畢
            last_text = ""
            stable_time = 0
            wait_count = 0
            
            while True:
                await page.wait_for_timeout(1000) # 每 1 秒檢查一次畫面
                wait_count += 1
                
                reply_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
                
                if not reply_elements:
                    if wait_count > 15: # 如果等了 15 秒連黑對話框都沒生出來
                        print("\n❌ 等待太久，可能連線卡住了。")
                        break
                    continue
                    
                current_text = await reply_elements[-1].inner_text()
                
                # 如果有抓到文字，且目前的文字長度與 1 秒前一樣
                if current_text == last_text and current_text.strip() != "":
                    stable_time += 1
                else:
                    stable_time = 0      # 文字還在改變，重置穩定計時器
                    last_text = current_text
                
                # 如果連續 2 秒都沒有新文字蹦出來，就認定它打完字了
                if stable_time >= 2:
                    print("\n🤖 ChatGPT：")
                    print(current_text)
                    print("-" * 50)
                    break
                    
                # 防呆：最多只等 2 分鐘，避免因為奇怪的 bug 無限卡住
                if wait_count >= 120:
                    print("\n❌ 生成時間過長 (超過兩分鐘)，強制中斷。")
                    print("目前輸出的片段：")
                    print(current_text)
                    break
                
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 強制結束程式！")
