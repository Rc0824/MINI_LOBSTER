import asyncio
import os
import sys
import re
import subprocess
import atexit
from playwright.async_api import async_playwright

def cleanup_temp_files():
    for f in ["temp_lobster.py", "temp_out.txt"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

atexit.register(cleanup_temp_files)

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
        
        # 雙重鎖定：檢查畫面上的「停止生成」按鈕是否還存在
        stop_btn = await page.query_selector('button[data-testid="stop-button"]')
        
        if stop_btn:
            # 如果停止按鈕存在，代表 ChatGPT (尤其是 o1 這種思考型模型) 還在深度運算中
            # 絕對不能中斷，強制將穩定時間鎖定歸零
            stable_time = 0
            last_text = current_text
        else:
            # 停止按鈕消失了，代表它聲稱自己做完了，我們再用 3 秒防網路抖動來確認
            if current_text == last_text and current_text.strip() != "":
                stable_time += 1
            else:
                stable_time = 0
                last_text = current_text
        
        # 只要按鈕不見且字面連續 3 秒沒變，即保證 100% 完成
        if stable_time >= 3 or wait_count >= 300:
            return current_text

def extract_action(text, tag):
    if tag not in text:
        return ""
    
    parts = text.split(tag)
    if len(parts) > 1:
        code_str = parts[1].split("[ACTION:DONE]")[0].split("[ACTION:CMD]")[0].split("[ACTION:PYTHON]")[0].strip()
        
        # 挖出 Markdown 內的程式碼
        code_match = re.search(r'```(?:cmd|bat|bash|powershell|sh|python)?\n(.*?)\n```', code_str, re.DOTALL)
        if code_match:
            code_str = code_match.group(1).strip()
        else:
            code_str = code_str.replace('```', '').strip()
            
        if tag == "[ACTION:CMD]":
            lines = code_str.split('\n')
            if lines and lines[0].strip().lower() in ['cmd', 'bat', 'bash', 'powershell', 'sh']:
                lines = lines[1:]
            return " & ".join([line.strip() for line in lines if line.strip()])
            
        return code_str
    return ""

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
你可以控制我 Windows 的 Terminal (終端機) 以及執行 Python 程式碼。我會給你任務。
你「每次」的回答都「必須」使用以下三種規定好的格式之一，不要給多餘的解釋或廢話：

1. 如果你想執行簡單的終端機指令（讀寫檔案、呼叫內建工具等）：
[ACTION:CMD]
```cmd
你的 Windows 指令
```

2. 如果你需要執行複雜邏輯、控制滑鼠鍵盤 (pyautogui)、影像處理 (opencv/pillow)：
[ACTION:PYTHON]
```python
你要執行的完整 Python 程式碼 (請把結果用 print 印出來)
```
★ 極度重要警告 ★：如果你遇到需要控制滑鼠、打開軟體、截圖的任務，請絕對「不要」拒絕我說你做不到，也「不要」建議我自己手動寫腳本！我已經授權給你了！請直接在第一時間霸氣地使用 [ACTION:PYTHON] 把 pyautogui 的爬蟲或控制腳本產出給我，我的電腦會自動去跑你的程式碼！

3. 如果任務已經達成，或是你想問我問題確認：
[ACTION:DONE]
你要對我說的話

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
            prompt = f"任務來了：{goal}。請開始思考，並根據任務難度自由使用 [ACTION:CMD]、[ACTION:PYTHON] 或 [ACTION:DONE] 格式。"
            
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
                
                is_py = "[ACTION:PYTHON]" in response
                is_cmd = "[ACTION:CMD]" in response
                
                if is_py:
                    code = extract_action(response, "[ACTION:PYTHON]")
                    action_type = "Python 腳本"
                elif is_cmd:
                    code = extract_action(response, "[ACTION:CMD]")
                    action_type = "終端機指令"
                else:
                    code = ""
                
                if not code:
                    prompt = "系統警告：你沒有正確輸出指令！請嚴格遵守 [ACTION:CMD] 或 [ACTION:PYTHON] 格式。"
                    continue
                    
                print(f"\n⚠️ 龍蝦想要執行以下 {action_type}：\n{code}")
                confirm = await asyncio.to_thread(input, ">> 是否允許執行？ (y=允許 / n=拒絕 / q=放棄整個任務): ")
                
                if confirm.lower() == 'q':
                    print("已放棄當前任務。")
                    prompt = "任務已被終止，請回覆 [ACTION:DONE] 結束任務。"
                elif confirm.lower() == 'n':
                    prompt = f"系統：使用者拒絕了這個 {action_type}，請改用其他方法或回覆 [ACTION:DONE]。"
                else:
                    try:
                        # 避免 Windows Pipe 繼承導致開啟 GUI 程式 (如 mspaint) 時永久卡死
                        # 我們改用檔案重導向 (> temp_out.txt) 來捕捉輸出
                        if is_py:
                            with open("temp_lobster.py", "w", encoding="utf-8") as f:
                                f.write(code)
                            cmd_to_run = "python temp_lobster.py > temp_out.txt 2>&1"
                            subprocess.run(cmd_to_run, shell=True, timeout=30)
                            with open("temp_out.txt", "r", encoding="utf-8", errors="replace") as f:
                                output = f.read()
                        else:
                            cmd_to_run = f"{code} > temp_out.txt 2>&1"
                            subprocess.run(cmd_to_run, shell=True, timeout=15)
                            with open("temp_out.txt", "r", encoding="cp950", errors="replace") as f:
                                output = f.read()
                                
                        if not output.strip():
                            output = "執行成功，沒有輸出任何文字。"
                    except subprocess.TimeoutExpired:
                        try:
                            # 即使逾時，也嘗試讀取已經產生的輸出
                            with open("temp_out.txt", "r", encoding="cp950", errors="replace") as f:
                                output = f.read()
                            output += "\n\n[系統警告：執行逾時 (可能是開啟了常駐視窗或背景程式)]"
                        except Exception:
                            output = "[系統警告：執行逾時]"
                    except Exception as e:
                        output = f"執行發生錯誤: {str(e)}"
                        
                    print(f"\n💻 電腦回傳執行結果給龍蝦中 (長度: {len(output)} 個字)...\n")
                    
                    # 最多截取 1500 字，避免撐爆 Token
                    prompt = f"這是剛剛 {action_type} 執行後的結果：\n```\n{output[:1500]}\n```\n請判斷是否已完成任務。繼續動作請用對應的 ACTION，完成任務請用 [ACTION:DONE]。"

        await browser.close()
        print("👋 小龍蝦已下線。")

if __name__ == "__main__":
    try:
        asyncio.run(mini_lobster())
    except KeyboardInterrupt:
        print("\n強制關閉程式！")
