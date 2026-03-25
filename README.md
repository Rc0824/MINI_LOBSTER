# Free ChatGPT Automation

這是一個用 Python 和 Playwright 實作的簡單專案，用來展示如何透過自動化瀏覽器來「免 API Key」使用 ChatGPT。

## 使用步驟

### 1. 安裝環境
此專案使用 Python，建議在虛擬環境中執行。
```bash
# 建立虛擬環境 (如果還沒做的話)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安裝套件
pip install -r requirements.txt
playwright install
```

### 2. 登入並儲存狀態
先執行登入程式，它會開一個瀏覽器讓你手動登入 ChatGPT。請完成登入並且看到對話框後，在終端機按下 Enter。
這會產生一個 `chatgpt_state.json` 檔案。
```bash
python save_login.py
```

### 3. 自動詢問 ChatGPT
有了狀態檔之後，就可以讓程式自動去問問題了。
```bash
# 執行預設問題
python ask_chatgpt.py

# 或是問自己想問的問題
python ask_chatgpt.py "幫我寫一個 Python 的 Hello World"
```

## 注意事項
* 使用自動化指令碼違反 ChatGPT 的服務條款，**請僅用於個人測試與學習用途**，不要拿去大量請求或商用，否則帳號可能會被鎖。
* Session (Cookie) 會有過期的一天，如果發現不能用了，只要再跑一次 `python save_login.py` 重新覆蓋舊的 JSON 即可。
