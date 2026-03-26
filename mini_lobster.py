import asyncio
import os
import sys
import re
import subprocess
from playwright.async_api import async_playwright

async def send_message(page, msg):
    await page.fill('#prompt-textarea', msg)
    await page.press('#prompt-textarea', 'Enter')
    
    print("🦞 小龍蝦推論中 (穩定抓取文字中)...\r", end="", flush=True)
    
    last_text = ""
    stable_time = 0
    wait_count = 0
    
    while True:
        await page.wait_for_timeout(1000) # 每 1 秒檢查一次畫面
        wait_count += 1
        
        reply_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
        
        if not reply_elements:
            if wait_count > 30:
                return "系統：等待過久無回應。"
            continue
            
        current_text = await reply_elements[-1].inner_text()
        
        # 只有在「抓到了字」並且「連續幾秒沒變」的情況下才當作完成
        if current_text == last_text and current_text.strip() != "":
            stable_time += 1
        else:
            stable_time = 0
            last_text = current_text
        
        # 只要連續 3 秒沒變，保證它 100% 已經生成完畢，且避開了前面的時間差陷阱
        if stable_time >= 3 or wait_count >= 300:
            return current_text

def extract_cmd(text):
    cmd_str = ""
    # 用正則表達式把 ChatGPT 輸出的 CMD 指令精準挖出來
    code_match = re.search(r'```(?:cmd|bat|bash|powershell|sh)?\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        cmd_str = code_match.group(1).strip()
    # 如果它沒加 Markdown 程式碼區塊，就粗暴切字串
    elif "[ACTION:CMD]" in text:
        cmd_str = text.split("[ACTION:CMD]")[1].split("[ACTION:DONE]")[0].strip()
        cmd_str = cmd_str.replace('```', '').strip()
        
    # 防呆過濾機制：避免 ChatGPT 雞婆加了語言前綴導致終端機開啟互動視窗卡死
    lines = cmd_str.split('\n')
    if lines and lines[0].strip().lower() in ['cmd', 'bat', 'bash', 'powershell', 'sh']:
        lines = lines[1:]
        
    # Windows 的 cmd 執行多行字串時容易發生讀取中斷，所以我們用 "&" 把它們串成一行
    clean_lines = [line.strip() for line in lines if line.strip()]
    return " & ".join(clean_lines)

async def mini_lobster():
    state_path = "chatgpt_state.json"
    if not os.path.exists(state_path):
        print("❌ 找不到登入狀態。請先跑 python save_login.py")
        return

    async with async_playwright() as p:
        print("🦞 喚醒桌面小龍蝦中...")
        browser = await p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(storage_state=state_path)
        page = await context.new_page()
        
        await page.goto("https://chatgpt.com")
        try:
            await page.wait_for_selector('#prompt-textarea', timeout=15000)
        except Exception:
            print("❌ 連線失敗！")
            await browser.close()
            return

        # 核心：給 ChatGPT 的系統大腦設定 (System Prompt)
        prompt_setup = """我們來玩一個遊戲。你現在是一個名為「小龍蝦」的本機自動化 Agent。
你可以控制我 Windows 的 Terminal (終端機)。我會給你任務。
你「每次」的回答都必須使用以下兩種規定好的格式之一，不要給多餘的解釋或廢話：

1. 如果你想執行指令來取得資訊、操作檔案：
[ACTION:CMD]
```cmd
你的 Windows 終端機指令 (例如 dir, echo 123 等)
```

2. 如果任務已經達成，或是你想問我問題確認：
[ACTION:DONE]
你要對我說的話、或是報告任務結果

了解請回覆 [ACTION:DONE] 收到。"""

        print("\n正在寫入 Agent 靈魂設定...")
        await send_message(page, prompt_setup)
        print("\n✅ 小龍蝦已就緒！\n")
        
        while True:
            # 這是你 (老闆) 給小龍蝦的任務
            goal = await asyncio.to_thread(input, "😎 請輸入你想交給小龍蝦的任務 (輸入 exit 離開)：")
            if goal.lower() in ['exit', 'quit']:
                break
            if not goal.strip():
                continue
                
            # 第一棒交給龍蝦開始推論
            prompt = f"任務來了：{goal}。請開始思考，並使用 [ACTION:CMD] 或 [ACTION:DONE] 格式。"
            
            # 開始 ReAct (推論與行動) 無限迴圈
            while True:
                response = await send_message(page, prompt)
                
                print("\n" + "="*40)
                print("🦞 龍蝦的大腦：")
                print(response)
                print("="*40)
                
                if "[ACTION:DONE]" in response:
                    print("\n🎉 任務環節結束。\n")
                    break
                
                # 若龍蝦想下指令
                cmd = extract_cmd(response)
                
                if not cmd:
                    prompt = "系統警告：你沒有正確輸出指令！請嚴格遵守 [ACTION:CMD] 與 markdown 格式。"
                    continue
                    
                print(f"\n⚠️ 龍蝦想要對你的電腦執行以下指令：\n{cmd}")
                confirm = await asyncio.to_thread(input, ">> 是否允許執行？ (y=允許 / n=拒絕 / q=放棄整個任務): ")
                
                if confirm.lower() == 'q':
                    print("已放棄當前任務。")
                    prompt = "任務已被使用者終止，請回覆 [ACTION:DONE] 結束任務。"
                    # 丟回去告訴龍蝦可以休息了
                elif confirm.lower() == 'n':
                    prompt = "系統：使用者拒絕了這個指令，請改用其他方法或回覆 [ACTION:DONE] 宣告無法完成。"
                else:
                    # 使用者選擇 'y'，真正執行指令！
                    try:
                        # 用 Windows 編碼來執行，避免中文亂碼
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, encoding='cp950', errors='replace')
                        output = result.stdout + result.stderr
                        if not output.strip():
                            output = "指令執行成功，沒有輸出任何文字。"
                    except Exception as e:
                        output = f"執行發生錯誤: {str(e)}"
                        
                    print(f"\n💻 電腦回傳執行結果給龍蝦中 (長度: {len(output)} 個字)...\n")
                    
                    # 避免指令輸出太長把 Token 吃到底，最多只餵給它前 1000 個字
                    prompt = f"這是剛剛指令執行後的終端機結果：\n```\n{output[:1000]}\n```\n請判斷是否已完成任務。若完成請回覆 [ACTION:DONE]，若需繼續搜集資訊請回覆 [ACTION:CMD]。"

        await browser.close()
        print("👋 小龍蝦已下線。")

if __name__ == "__main__":
    try:
        asyncio.run(mini_lobster())
    except KeyboardInterrupt:
        print("\n強制關閉程式！")
