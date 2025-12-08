# T-20251208-002: 驗證 Cloud Run Webhook 支援功能

**狀態**: [ ] 待處理  
**建立日期**: 2025-12-08  
**Story Points**: 2  
**相依**: T-20251208-001（已完成）  
**分支**: `feature/cloud-run-support`

---

## Summary

驗證 T-20251208-001 實作的 Cloud Run Webhook 支援功能，確保 Polling 與 Webhook 雙模式皆能正常運作。

## Why

確保程式碼改動符合預期行為，避免部署後才發現問題。

## Scope

### In Scope
- [ ] 本地 Polling 模式啟動測試
- [ ] 本地 Polling 模式轉檔功能測試
- [ ] Webhook 模式語法與邏輯檢查
- [ ] Cloud Run 部署後 Webhook 測試（選用）

### Out of Scope
- 效能壓力測試
- 長時間穩定性測試

## Acceptance Criteria

### Polling 模式驗證
- [x] 不設定 `RUN_MODE` 時，顯示 `執行模式: polling`
- [x] 顯示 `FFmpeg 超時設定: 300 秒`
- [x] 假網頁伺服器正常監聽 Port 10000
- [x] 能接收 Telegram 影片訊息
- [x] 能成功轉檔並回傳 GIF

### Webhook 模式驗證
- [ ] 設定 `RUN_MODE=webhook` 但未設 `WEBHOOK_URL` 時，程式報錯退出
- [ ] 正確設定所有環境變數後，顯示 `執行模式: webhook`
- [ ] 顯示 `FFmpeg 超時設定: 50 秒`
- [ ] Webhook URL 包含 Token 路徑

## Test Steps

### 1. Polling 模式本地測試

```powershell
# Windows PowerShell
cd d:\project\VideoToGIFWebService

# 設定 Token
$env:TELEGRAM_TOKEN="<你的 Bot Token>"

# 確保不設定 RUN_MODE（使用預設）
Remove-Item Env:RUN_MODE -ErrorAction SilentlyContinue

# 啟動 Bot
python app.py
```

**預期輸出**:
```
🔧 執行模式: polling
🔧 並發控制：最多同時處理 1 個轉檔任務
🔧 FFmpeg 超時設定: 300 秒
啟動假網頁伺服器監聽 Port: 10000
✅ Bot 已啟動 (Polling Mode - Render)
```

**功能測試**:
1. 開啟 Telegram，找到你的 Bot
2. 傳送一個短影片（< 15 秒）
3. 確認收到轉檔後的 GIF

### 2. Webhook 模式錯誤處理測試

```powershell
# 設定 Webhook 模式但不設 WEBHOOK_URL
$env:RUN_MODE="webhook"
Remove-Item Env:WEBHOOK_URL -ErrorAction SilentlyContinue

python app.py
```

**預期輸出**:
```
🔧 執行模式: webhook
CRITICAL - Webhook 模式需設定 WEBHOOK_URL 環境變數
```
程式應以錯誤碼退出。

### 3. Webhook 模式完整設定測試（選用 - 需 ngrok 或 Cloud Run）

```powershell
$env:RUN_MODE="webhook"
$env:WEBHOOK_URL="https://your-url.run.app"
$env:TELEGRAM_TOKEN="<你的 Bot Token>"

python app.py
```

**預期輸出**:
```
🔧 執行模式: webhook
🔧 FFmpeg 超時設定: 50 秒
✅ Bot 啟動 (Webhook Mode)
📡 Webhook URL: https://your-url.run.app/***
🌐 監聽 Port: 8080
```

## Validation Checklist

- [ ] Polling 模式啟動成功
- [ ] Polling 模式轉檔功能正常
- [ ] Webhook 模式缺少 WEBHOOK_URL 時正確報錯
- [ ] Webhook 模式環境變數正確顯示
- [ ] 日誌輸出清晰易讀

---

**備註**: Cloud Run 實際部署測試可在 PR 合併後進行，或建立獨立的部署 TICKET。
