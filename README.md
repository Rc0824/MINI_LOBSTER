# MINI_LOBSTER 🦞

這是一個基於 Python 與 Playwright 打造的「本機端自律型 AI 代理 (Autonomous Local AI Agent)」，靈感來自於爆紅的 OpenClaw (AI 龍蝦)。
它不僅是一個可以免 API Key 直接利用 ChatGPT 的聊天室，更是一隻能被授權執行 **Windows 本地終端機系統指令** 的迷你自動化蝦蝦！

## 核心亮點

1. **`mini_lobster.py` (主力 Agent)**
   - 搭載了 ReAct (Reason & Act 思考與行動) 循環邏輯。
   - 能夠接收使用者的任務，自主規劃並使用 `[ACTION:CMD]` 格式向系統索取終端機指令權限。
   - 具備「命令執行防呆審查機制」，所有終端機指令都需要經過使用者的手動同意 (`y` 鍵) 才會真正被執行，保障你的電腦存活率。
   - 電腦的執行輸出會自動抓取並回傳給大腦 (ChatGPT) 進行下一步推論，直到任務徹底宣告 `[ACTION:DONE]` 完成。

2. **`cli_chat.py` (純聊天模式)**
   - 簡單乾淨的終端機聊天室，讓你不用開啟網頁也能流暢地和 ChatGPT 連續對話。

3. **`save_login.py` (取得通行證)**
   - 負責建立初始的連線授權狀態。只需手動登入一次，將 Cookie 與 Session 打包成 `chatgpt_state.json`，後續所有自動化流程將完全免密碼靜默登入。

---

## 快速上手步驟

### 1. 安裝環境與相依套件
請確保你的電腦裡安裝了 Python，以及 Windows 內建的 Microsoft Edge 瀏覽器。
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
```

### 2. 登入並儲存狀態 (只需做一次)
```bash
python save_login.py
```
*在彈出的瀏覽器中完成手動登入 ChatGPT，看到底部對話框後，回到終端機點擊 Enter 鍵以儲存憑證。*

### 3. 起飛！召喚小龍蝦來幫你辦事
```bash
python mini_lobster.py
```
*這時候你可以開始給它派任務了，例如：*
* 👉 `"查一下我目前的本地 IP 位址"`
* 👉 `"在桌面上建立一個名為 Lobster_Project 的空資料夾"`
* 👉 `"看一下 D 槽根目錄有哪些檔案"`

---

## ⚠️ 免責與資安強烈聲明
- **請務必親自審查每一次的執行權限**：小龍蝦有能力對你的硬碟底層發號施令。如果它產生的刪除指令 (`del` 或 `rmdir`) 看起來有任何疑慮，請果斷輸入 `n` 拒絕，以免對電腦造成毀滅性的誤刪破壞。
- 本專案純屬自動化代理 (Agent) 的學習與技術交流，若因頻繁或不當存取導致相關服務帳號遭到封鎖，請使用者自行承擔風險。
