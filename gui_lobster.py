import asyncio
import os
import re
import subprocess
import threading
import atexit
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from PIL import ImageGrab
from playwright.async_api import async_playwright

import glob
def cleanup_temp_files():
    files = ["temp_lobster.py", "temp_out.txt", "temp_lobster.ps1"] + glob.glob("temp_clipboard*.png")
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

atexit.register(cleanup_temp_files)

# ========================== 顏色主題 ==========================
BG_DARK     = "#1a1b2e"
BG_PANEL    = "#252640"
BG_INPUT    = "#2e2f4a"
FG_TEXT     = "#e0e0f0"
FG_DIM      = "#8888aa"
ACCENT_RED  = "#ff4d6a"
ACCENT_BLUE = "#5b8aff"
ACCENT_GREEN= "#44cc77"
ACCENT_GOLD = "#ffcc44"

# ========================== 核心 AI 邏輯 ==========================
async def send_message_to_chatgpt(page, msg, image_path=None):
    if image_path and os.path.exists(image_path):
        try:
            # 觸發 ChatGPT 原生的圖片上傳功能 (加上 .first 避免網頁後期多出其他的上傳點導致嚴格模式報錯)
            await page.locator('input[type="file"]').first.set_input_files(image_path)
            # 等待圖片上傳，根據硬碟速度與網路狀態給予 3 秒寬衝
            await page.wait_for_timeout(3000)
        except Exception as e:
            print("附加圖片發生錯誤:", e)

    await page.fill('#prompt-textarea', msg)
    await page.press('#prompt-textarea', 'Enter')
    
    last_text = ""
    stable_time = 0
    wait_count = 0
    
    while True:
        await page.wait_for_timeout(1000)
        wait_count += 1
        
        reply_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
        if not reply_elements:
            if wait_count > 30:
                return "系統：等待過久無回應。"
            continue
            
        current_text = await reply_elements[-1].inner_text()
        
        # 使用雙層保險來確認是否文字產生完畢
        stop_btn = await page.query_selector('button[data-testid="stop-button"]')
        if stop_btn:
            stable_time = 0
            last_text = current_text
        else:
            if current_text == last_text and current_text.strip() != "":
                stable_time += 1
            else:
                stable_time = 0
                last_text = current_text
        
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
            if lines and lines[0].strip().lower() in ['cmd', 'bat', 'bash', 'powershell', 'sh', 'ps1']:
                lines = lines[1:]
            return "\n".join([line for line in lines])
            
        return code_str
    return ""

# ========================== GUI 主程式 ==========================
class LobsterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🦞 Mini Lobster Agent")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("780x620")
        self.root.minsize(600, 400)
        
        self.page = None
        self.browser = None
        self.loop = None
        self.connected = False
        self.image_path = None
        
        self._build_ui()
        self._start_connection_thread()
    
    def _build_ui(self):
        header = tk.Frame(self.root, bg=ACCENT_RED, height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🦞 Mini Lobster Agent", font=("Segoe UI", 14, "bold"),
                 bg=ACCENT_RED, fg="white").pack(side=tk.LEFT, padx=14)
        
        self.status_label = tk.Label(header, text="⏳ 連線中...", font=("Segoe UI", 10),
                                     bg=ACCENT_RED, fg="#dddddd")
        self.status_label.pack(side=tk.RIGHT, padx=14)
        
        chat_frame = tk.Frame(self.root, bg=BG_DARK)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,0))
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg=BG_PANEL, fg=FG_TEXT, font=("Consolas", 11),
            insertbackground=FG_TEXT, relief=tk.FLAT, borderwidth=0,
            padx=12, pady=10, selectbackground=ACCENT_BLUE
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        self.chat_area.tag_configure("user",       foreground=ACCENT_BLUE, font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_configure("lobster",     foreground=ACCENT_RED,  font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_configure("system",      foreground=ACCENT_GREEN, font=("Segoe UI", 10, "italic"))
        self.chat_area.tag_configure("code",        foreground=ACCENT_GOLD, font=("Consolas", 10))
        self.chat_area.tag_configure("normal",      foreground=FG_TEXT,     font=("Segoe UI", 11))
        self.chat_area.tag_configure("dim",         foreground=FG_DIM,     font=("Segoe UI", 10))
        
        input_frame = tk.Frame(self.root, bg=BG_DARK, height=50)
        input_frame.pack(fill=tk.X, padx=8, pady=8)
        
        # 📎 附加圖片按鈕
        self.attach_btn = tk.Button(
            input_frame, text="📎", font=("Segoe UI", 12),
            bg=BG_PANEL, fg="white", activebackground="#444466",
            relief=tk.FLAT, padx=10, pady=4, command=self._attach_image,
            state=tk.DISABLED
        )
        self.attach_btn.pack(side=tk.LEFT, padx=(0,8))

        self.cancel_img_btn = tk.Button(
            input_frame, text="✖ 取消", font=("Segoe UI", 10, "bold"),
            bg=BG_PANEL, fg=ACCENT_RED, activebackground="#444466",
            relief=tk.FLAT, padx=8, pady=4, command=self._cancel_image
        )
        # 初始不顯示

        self.input_entry = tk.Entry(
            input_frame, font=("Segoe UI", 12), bg=BG_INPUT, fg=FG_TEXT,
            insertbackground=FG_TEXT, relief=tk.FLAT, borderwidth=0
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=10, padx=(0,8))
        self.input_entry.bind("<Return>", lambda e: self._on_send())
        
        # 攔截 Ctrl+V 操作來支援本地剪貼簿圖片
        self.input_entry.bind("<Control-v>", self._on_paste)
        self.input_entry.configure(state=tk.DISABLED)
        
        self.send_btn = tk.Button(
            input_frame, text="發送 🦞", font=("Segoe UI", 11, "bold"),
            bg=ACCENT_RED, fg="white", activebackground="#cc3355",
            relief=tk.FLAT, padx=18, pady=6, command=self._on_send,
            state=tk.DISABLED
        )
        self.send_btn.pack(side=tk.RIGHT)
    
    def _cancel_image(self):
        if self.image_path:
            self.image_path = None
            self._append("\n🗑️ 您已取消剛剛附加的圖片！", "dim")
            self.cancel_img_btn.pack_forget()

    def _attach_image(self):
        file_path = filedialog.askopenfilename(
            title="選擇圖片",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.webp")]
        )
        if file_path:
            self.image_path = file_path
            self._append(f"\n📎 已成功載入圖片: {os.path.basename(file_path)} (這張圖片將會跟著下一次對話發送出去)", "dim")
            self._append_image(file_path)
            self.cancel_img_btn.pack(before=self.input_entry, side=tk.LEFT, padx=(0,8))
            
    def _on_paste(self, event):
        import uuid
        try:
            # 支援從剪貼簿直接抓取截圖貼上
            img = ImageGrab.grabclipboard()
            if img:
                # 為了避免連續貼上時前一張圖被系統鎖死，每次都給它亂數檔名
                temp_path = os.path.abspath(f"temp_clipboard_{uuid.uuid4().hex[:6]}.png")
                # 如果是複製檔案本身 (清單)
                if isinstance(img, list):
                    temp_path = img[0]
                else:    
                    # 如果是複製螢幕截圖
                    img.save(temp_path, "PNG")
                    
                self.image_path = temp_path
                self._append(f"\n📎 您已直接從剪貼簿截取圖片！(將會跟著下一次對話發送出去)", "dim")
                self._append_image(temp_path)
                self.cancel_img_btn.pack(before=self.input_entry, side=tk.LEFT, padx=(0,8))
                return "break" # 取消預設的文字貼上行爲
        except Exception as e:
            self._append(f"\n❌ 從剪貼簿讀取圖片失敗: {e}", "system")

    def _append_image(self, img_path):
        from PIL import Image, ImageTk
        try:
            img = Image.open(img_path)
            # 讓縮圖保持原始比例並限制在最大 250x250 以內
            img.thumbnail((250, 250))
            photo = ImageTk.PhotoImage(img)
            
            # 把 PhotoImage 物件存起來避免被 Python 的垃圾回收機制清掉而變成死圖/透明
            if not hasattr(self, 'rendered_images'):
                self.rendered_images = []
            self.rendered_images.append(photo)
            
            self.chat_area.configure(state=tk.NORMAL)
            # 將圖片塞入對話日誌
            self.chat_area.image_create(tk.END, image=photo, padx=10, pady=5)
            self.chat_area.insert(tk.END, "\n\n")
            self.chat_area.configure(state=tk.DISABLED)
            self.chat_area.see(tk.END)
        except Exception as e:
            self._append(f"[無法顯示圖片預覽: {e}]", "dim")

    def _append(self, text, tag="normal"):
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.insert(tk.END, text + "\n", tag)
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)
        
    def _start_connection_thread(self):
        t = threading.Thread(target=self._run_async_loop, daemon=True)
        t.start()
    
    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_setup())
    
    async def _connect_and_setup(self):
        state_path = "chatgpt_state.json"
        if not os.path.exists(state_path):
            self.root.after(0, lambda: self._append("❌ 找不到 chatgpt_state.json！請先執行 python save_login.py", "system"))
            return
        
        self.root.after(0, lambda: self._append("🌐 正在啟動瀏覽器並連線到 ChatGPT...", "system"))
        
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(
                headless=False, channel="msedge",
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await self.browser.new_context(storage_state=state_path)
            self.page = await context.new_page()
            await self.page.goto("https://chatgpt.com")
            
            try:
                await self.page.wait_for_selector('#prompt-textarea', timeout=15000)
            except Exception:
                self.root.after(0, lambda: self._append("❌ 連線失敗！Cookie 可能過期了。", "system"))
                await self.browser.close()
                return
            
            prompt_setup = """我們來玩一個遊戲。你現在是一個名為「小龍蝦」的 Windows 自動化 Agent。
你的核心本領是使用 PowerShell 控制我的電腦。我會給你任務。
你「每次」的回答都「必須」使用以下三種規定好的格式之一，不要給多餘的解釋：

1. 預設且優先使用 PowerShell 指令 (用來尋找檔案、啟動程式、取得系統資訊等)：
[ACTION:CMD]
```powershell
你要執行的 PowerShell 指令
```

2. 只有當使用者「明確要求」控制滑鼠、模擬鍵盤輸入時，才允許使用 Python 腳本：
[ACTION:PYTHON]
```python
你要執行的完整 Python 程式碼 (請自行確認變數與 import)
```

3. 如果任務已經達成，或是你想問我問題確認：
[ACTION:DONE]
你要對我說的話

了解請回覆 [ACTION:DONE] 收到。"""
            
            await send_message_to_chatgpt(self.page, prompt_setup)
            
            self.connected = True
            self.root.after(0, self._on_connected)
            
            while self.connected:
                await asyncio.sleep(0.5)
            
            await self.browser.close()
    
    def _on_connected(self):
        self.status_label.config(text="✅ 已連線", fg=ACCENT_GREEN)
        self.input_entry.configure(state=tk.NORMAL)
        self.send_btn.configure(state=tk.NORMAL)
        self.attach_btn.configure(state=tk.NORMAL)
        self._append("✅ 小龍蝦已連線就緒！請輸入你的任務，或按左側迴紋針及 Ctrl+V 直接貼上圖片給它看。", "system")
        self.input_entry.focus_set()
    
    def _on_send(self):
        if not self.connected or not self.page:
            return
        msg = self.input_entry.get().strip()
        
        # 如果沒輸入文字也沒放圖片，就不理他
        if not msg and not self.image_path:
            return
            
        self.input_entry.delete(0, tk.END)
        self.input_entry.configure(state=tk.DISABLED)
        self.send_btn.configure(state=tk.DISABLED)
        self.attach_btn.configure(state=tk.DISABLED)
        self.cancel_img_btn.pack_forget()
        
        img_path = self.image_path
        self.image_path = None
        
        if img_path:
            self._append(f"\n🖼️ [你傳送了一張圖片: {os.path.basename(img_path)}]", "user")
            
        if msg:
            self._append(f"\n😎 你：{msg}", "user")
        else:
            msg = "請根據這張圖片進行分析，或是等待我的下一步指示。"
            
        # 把帶有圖片的訊息丟進背景處理
        threading.Thread(target=self._react_loop, args=(msg, img_path), daemon=True).start()
    
    def _react_loop(self, goal, img_path):
        prompt = f"任務來了：{goal}。請開始思考，並根據任務難度自由使用 [ACTION:CMD]、[ACTION:PYTHON] 或 [ACTION:DONE] 格式。"
        
        is_first_turn = True
        
        while True:
            self.root.after(0, lambda: self._append("🦞 小龍蝦推論中...", "dim"))
            
            # 只有用戶指派任務的第一回合才把圖片送進去，避免每一回合死循環傳圖
            if is_first_turn and img_path:
                future = asyncio.run_coroutine_threadsafe(send_message_to_chatgpt(self.page, prompt, img_path), self.loop)
                is_first_turn = False
            else:
                future = asyncio.run_coroutine_threadsafe(send_message_to_chatgpt(self.page, prompt), self.loop)
                
            response = future.result()
            self.root.after(0, lambda r=response: self._append(f"\n🦞 龍蝦大腦：\n{r}", "lobster"))
            
            if "[ACTION:DONE]" in response:
                self.root.after(0, lambda: self._append("🎉 任務環節結束。", "system"))
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
                prompt = "系統警告：你沒有正確輸出指令！請嚴格遵守格式。"
                continue
            
            self.root.after(0, lambda c=code, a=action_type: self._append(f"\n⚠️ 龍蝦想要執行 {a}：\n{c}", "code"))
            
            confirm_result = [None]
            confirm_event = threading.Event()
            
            def ask_confirm():
                result = messagebox.askyesnocancel(
                    "🦞 執行確認",
                    f"龍蝦想要執行以下 {action_type}：\n\n{code[:300]}{'...' if len(code)>300 else ''}\n\n是否允許？\n(Yes=允許 / No=拒絕 / Cancel=放棄任務)",
                    parent=self.root
                )
                confirm_result[0] = result
                confirm_event.set()
            
            self.root.after(0, ask_confirm)
            confirm_event.wait()
            
            if confirm_result[0] is None:
                self.root.after(0, lambda: self._append("❌ 已放棄當前任務。", "system"))
                prompt = "任務已被終止，請回覆 [ACTION:DONE] 結束任務。"
            elif confirm_result[0] is False:
                self.root.after(0, lambda: self._append("🚫 使用者拒絕執行。", "system"))
                prompt = f"系統：使用者拒絕了這個 {action_type}，請改用其他方法或 [ACTION:DONE]。"
            else:
                self.root.after(0, lambda: self._append("⚙️ 執行中...", "dim"))
                try:
                    if is_py:
                        with open("temp_lobster.py", "w", encoding="utf-8") as f:
                            f.write(code)
                        cmd_list = ["python", "temp_lobster.py"]
                        with open("temp_out.txt", "w", encoding="utf-8") as out_f:
                            subprocess.run(cmd_list, stdout=out_f, stderr=subprocess.STDOUT, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        with open("temp_lobster.ps1", "w", encoding="utf-8-sig") as f:
                            f.write(code)
                        cmd_list = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "temp_lobster.ps1"]
                        with open("temp_out.txt", "w", encoding="utf-8") as out_f:
                            subprocess.run(cmd_list, stdout=out_f, stderr=subprocess.STDOUT, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
                            
                    with open("temp_out.txt", "r", encoding="utf-8", errors="replace") as f:
                        output = f.read()
                        
                    if not output.strip():
                        output = "執行成功，沒有輸出任何文字。"
                except subprocess.TimeoutExpired:
                    try:
                        with open("temp_out.txt", "r", encoding="cp950", errors="replace") as f:
                            output = f.read()
                        output += "\n[系統警告：執行逾時]"
                    except Exception:
                        output = "[系統警告：執行逾時]"
                except Exception as e:
                    output = f"執行發生錯誤: {str(e)}"
                
                self.root.after(0, lambda o=output: self._append(f"\n💻 執行結果：\n{o[:500]}", "normal"))
                prompt = f"這是剛剛 {action_type} 執行後的結果：\n```\n{output[:1500]}\n```\n請判斷是否已完成任務。繼續動作請用對應的 ACTION，完成任務請用 [ACTION:DONE]。"
        
        self.root.after(0, self._unlock_input)
    
    def _unlock_input(self):
        self.input_entry.configure(state=tk.NORMAL)
        self.send_btn.configure(state=tk.NORMAL)
        self.attach_btn.configure(state=tk.NORMAL)
        self.input_entry.focus_set()

if __name__ == "__main__":
    root = tk.Tk()
    app = LobsterGUI(root)
    root.mainloop()
