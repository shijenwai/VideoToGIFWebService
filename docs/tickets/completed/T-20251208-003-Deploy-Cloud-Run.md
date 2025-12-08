# T-20251208-003: 部署至 Google Cloud Run

**狀態**: [ ] 待處理  
**建立日期**: 2025-12-08  
**Story Points**: 2  
**相依**: T-20251208-001（已完成）、T-20251208-002（部分完成）  
**分支**: `feature/cloud-run-support`

---

## Summary

將 Video to GIF Bot 部署至 Google Cloud Run，驗證 Webhook 模式在 Serverless 環境下的完整運作。

## Why

- 驗證 Webhook 模式在實際生產環境的運作
- 確認 Scale-to-Zero 與冷啟動行為
- 完成 T-20251208-002 剩餘的 Webhook URL Token 路徑驗證

## Scope

### In Scope
- [ ] 安裝與配置 Google Cloud CLI
- [ ] 建立 Cloud Run 服務
- [ ] 設定環境變數
- [ ] 驗證 Webhook 功能
- [ ] 驗證 Fail Fast 機制（長影片超時處理）

### Out of Scope
- CI/CD 自動化部署
- 自訂網域設定
- 監控與告警設定

## Acceptance Criteria

- [ ] Cloud Run 服務成功部署
- [ ] Bot 能接收 Telegram 訊息
- [ ] 短影片（< 15 秒）能成功轉檔回傳 GIF
- [ ] 長影片觸發 Fail Fast，顯示超時訊息
- [ ] 閒置後 Scale-to-Zero 正常運作

## 前置條件

- [ ] Google Cloud 帳號
- [ ] Google Cloud 專案（需計費帳戶）
- [ ] 安裝 Google Cloud CLI

## Implementation Steps

### 1. 安裝 Google Cloud CLI

**Windows（PowerShell）**:
```powershell
# 下載安裝程式
# https://cloud.google.com/sdk/docs/install

# 或使用 winget
winget install Google.CloudSDK
```

### 2. 初始化 gcloud

```bash
# 登入 Google Cloud
gcloud auth login

# 設定專案（替換成你的專案 ID）
gcloud config set project YOUR_PROJECT_ID

# 啟用必要服務
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 3. 推送程式碼

```bash
cd d:\project\VideoToGIFWebService
git push origin feature/cloud-run-support
```

### 4. 部署至 Cloud Run（最終成功配置）

```bash
# 部署並設定所有必要參數
# 注意：必須開啟 --no-cpu-throttling，否則背景轉檔時 CPU 會被降速導致超時
gcloud run deploy video-to-gif-bot \
  --source . \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "TELEGRAM_TOKEN=你的Bot Token" \
  --set-env-vars "RUN_MODE=webhook" \
  --set-env-vars "MAX_CONCURRENT=1" \
  --set-env-vars "WEBHOOK_URL=https://placeholder.run.app" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60s \
  --no-cpu-throttling
```

**更新真實 WEBHOOK_URL**：
```bash
# 部署後取得 URL，再更新一次
gcloud run services update video-to-gif-bot \
  --region asia-east1 \
  --update-env-vars "WEBHOOK_URL=https://video-to-gif-bot-xxxxx.asia-east1.run.app"
```

## 問題排查紀錄 (Troubleshooting)

### 1. 容器啟動失敗 (RuntimeError)
- **錯誤**: `RuntimeError: To use start_webhook, PTB must be installed via pip install "python-telegram-bot[webhooks]"`
- **原因**: 缺少 `tornado` 等 Webhook 依賴
- **解法**: 修改 `requirements.txt` 為 `python-telegram-bot[webhooks]>=20.0`

### 2. 容器啟動後立即退出
- **原因**: `start_webhook()` 後程式執行完畢退出
- **解法**: 在 `app.py` 增加 `await stop_event.wait()` 保持 Event Loop 運行

### 3. 無法取得影片時長 / 轉檔超時
- **錯誤**: `ffprobe timed out` / `FFmpeg 轉檔超時`
- **原因**: Cloud Run 預設開啟 CPU Throttling。當 Webhook 回應 200 OK 後，CPU 算力被降至 0，導致背景轉檔任務卡死。
- **解法**: 
  1. 啟用 `--no-cpu-throttling`（關鍵！）
  2. 升級資源至 `2 CPU / 2 GiB`
  3. `ffprobe` 增加 `-analyzeduration` 與 `-probesize` 限制

### 4. 取得檔案超時 (Timed out)
- **原因**: Cloud Run 冷啟動網路延遲
- **解法**: 增加 `Application.builder().connect_timeout(30.0)` 設定

## Test Test Results

- [x] Cloud Run 服務成功部署
- [x] Bot 能接收 Telegram 訊息
- [x] 短影片能成功轉檔回傳 GIF（包含影片時長分析正常）
- [x] Fail Fast 機制運作正常（超時任務被主動截斷）
- [x] Scale-to-Zero 正常運作

## 環境變數參考

| 變數 | 值 | 說明 |
|------|-----|------|
| `TELEGRAM_TOKEN` | `8535...tuQ` | Bot Token |
| `RUN_MODE` | `webhook` | 啟用 Webhook 模式 |
| `WEBHOOK_URL` | `https://video-to-gif-bot-xxx.run.app` | 服務 URL |
| `MAX_CONCURRENT` | `1` | 並發限制 |

## 資源配置建議

| 項目 | 建議值 | 說明 |
|------|--------|------|
| Memory | `1Gi` | FFmpeg 需要足夠記憶體 |
| CPU | `1` | 預設即可 |
| Timeout | `60s` | 對應 Telegram 限制 |
| Min Instances | `0` | Scale-to-Zero |
| Max Instances | `3` | 避免意外爆量 |

## Rollback Plan

如果部署失敗或出現問題：

```bash
# 刪除 Cloud Run 服務
gcloud run services delete video-to-gif-bot --region asia-east1

# 繼續使用 Render Polling 模式
```

## 費用估算

Cloud Run 免費額度（每月）：
- 200 萬次請求
- 360,000 GB-秒 記憶體
- 180,000 vCPU-秒

預估使用量極低，應在免費額度內。

---

**備註**: 完成後請更新 T-20251208-002 的最後一項驗證項目。
