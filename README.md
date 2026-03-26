# MINI_LOBSTER 🦞

這是一個基於 Python 與 Playwright 打造的「本機端自律型 AI 代理 (Autonomous Local AI Agent)」，靈感來自於爆紅的 OpenClaw (AI 龍蝦)。
它不僅是一個可以免 API Key 直接利用 ChatGPT 的聊天室，更是一隻能被授權執行 **Windows 本地終端機系統指令** 以及自行撰寫 **Python 腳本控制滑鼠** 的無敵自動化蝦蝦！

## 🌟 全新亮點與功能模組

### 1. `gui_lobster.py` (旗艦圖形化介面)
   - 搭載完整的 Tkinter 暗色系 UI 介面，讓你擁有和官方 ChatGPT APP 一樣的操作體驗。
   - **支援強大視覺能力 (Vision)**：直接點擊底部的 `📎` 按鈕，或是使用 Windows 截圖後在輸入框按下 `Ctrl + V` 貼上，立刻將畫面傳給龍蝦讓它幫你看圖做事！(貼上的圖片會在 UI 中即時呈現縮圖預覽)。
   - **彈出式安全審查**：當 AI 發動高危險性的本機操作時，採用獨立視窗讓你按下 Yes/No 進行授權，資安滴水不漏。
   - 內建 `o1` 與 `o3` 等思考型模型 (Reasoning Models) 解碼相容性技術，保證執行過程絕對不會提早斷線。

### 2. `mini_lobster.py` (硬核終端機 Agent)
   - 搭載了 ReAct (Reason & Act 思考與行動) 循環邏輯的底層版本。
   - 能夠接收使用者的任務，自主規劃並使用 `[ACTION:CMD]` 格式向系統索取終端機指令權限，或是使用 `[ACTION:PYTHON]` 調用 `pyautogui` 與 `opencv` 產出物理控制外掛。
   - 電腦的執行輸出會自動抓取並回傳給大腦 (ChatGPT) 進行下一步推論，直到任務徹底宣告 `[ACTION:DONE]` 完成。

### 3. `save_login.py` (取得通行證)
   - 負責建立初始的連線授權狀態。只需手動登入一次，將 Cookie 與 Session 打包成 `chatgpt_state.json`，後續所有自動化流程將完全免密碼靜默登入。

---

## 🚀 快速上手步驟

### 1. 安裝環境與相依套件
請確保你已經下載了最新的 GitHub 原始碼，並且有 Microsoft Edge 瀏覽器。
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
*在彈出的瀏覽器中完成手動登入 ChatGPT，看到底部對話框後，回到終端機點擊 Enter 鍵以儲存憑證 `chatgpt_state.json`。*

### 3. 起飛！召喚小龍蝦來幫你辦事
```bash
python gui_lobster.py
```
*這時候你可以開始給它派任務了，例如：*
* 👉 `"查一下我目前的本地 IP 位址"`
* 👉 `"用 pyautogui 幫我把滑鼠移到螢幕正中央點右鍵"`
* 👉 *(按 Ctrl+V 貼上一張遊戲截圖)* `"幫我分析畫面上血量條的座標在哪裡"`

---

## ⚠️ 免責與資安強烈聲明
- **請務必親自審查每一次的執行權限**：小龍蝦有能力對你的硬碟底層發號施令。如果它產生的腳本看起來有任何疑慮，請果斷在彈窗點選 `No` 拒絕，以免對電腦造成毀滅性的誤刪破壞。
- 本專案純屬自動化代理 (Agent) 的學習與技術交流，若因頻繁或不當存取導致相關服務帳號遭到封鎖，請使用者自行承擔風險。
