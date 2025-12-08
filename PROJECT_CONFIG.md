# PROJECT_CONFIG.md - 專案配置

本文件為專案的核心配置檔，所有 AI 工具（Claude、Codex、Gemini）皆參考此檔案。

## 專案資訊

- **專案名稱**: Video to GIF Telegram Bot
- **專案描述**: 將 Telegram 影片轉換為 GIF 的機器人，支援 Render 與 Google Cloud Run 部署
- **技術棧**: Python 3.10+, python-telegram-bot, FFmpeg

## 專案特定注意事項

- 此專案使用 async/await 模式 (python-telegram-bot v20+)
- FFmpeg 命令需在 `run_in_executor` 中執行以避免阻塞
- 暫存檔案需確保清理 (使用 try/finally)
- 並發控制透過 `MAX_CONCURRENT` 環境變數調整
- **Webhook 模式下，FFmpeg timeout 為 50 秒**（Fail Fast 機制，避免 Telegram 60 秒限制觸發重試風暴）

## 執行模式

本專案支援兩種執行模式，透過 `RUN_MODE` 環境變數切換：

### Polling 模式（預設，適用 Render）
- **模式**: Long Polling + HTTP Health Check Server
- **適用場景**: Render 免費方案、本地開發
- **FFmpeg Timeout**: 300 秒

### Webhook 模式（適用 Cloud Run）
- **模式**: HTTP Webhook Server（Serverless）
- **適用場景**: Google Cloud Run、支援 Scale-to-Zero
- **FFmpeg Timeout**: 50 秒（Fail Fast 機制）
- **額外需求**: 需設定 `WEBHOOK_URL` 環境變數

## 環境變數

| 變數名稱 | 說明 | 預設值 | 備註 |
|---------|------|--------|------|
| `TELEGRAM_TOKEN` | Telegram Bot Token | 必填 | 從 @BotFather 取得 |
| `RUN_MODE` | 執行模式 | `polling` | `polling` 或 `webhook` |
| `PORT` | 監聽埠號 | `10000`(Polling) / `8080`(Webhook) | Cloud Run 自動注入 |
| `WEBHOOK_URL` | Webhook 完整 URL | - | Webhook 模式必填，如 `https://xxx.run.app` |
| `MAX_CONCURRENT` | 同時處理任務數 | `1` | 依資源調整 |

## 部署配置

### Render 部署（Polling 模式）
- **平台**: Render.com 免費方案
- **資源限制**: 0.1 CPU / 512MB RAM
- **預設並發**: `MAX_CONCURRENT=1`（完全排隊模式）
- **環境變數**: `TELEGRAM_TOKEN`（RUN_MODE 不設定或設為 `polling`）

### Cloud Run 部署（Webhook 模式）
- **平台**: Google Cloud Run
- **區域**: `us-central1` (北美，以獲得每個月 1GB 免費流量)
- **特性**: Scale-to-Zero、按需付費
- **配置**:
    - **CPU/RAM**: `2 vCPU / 2 GiB Memory`（優化轉檔速度）
    - **CPU Allocation**: `--no-cpu-throttling`（關鍵！背景轉檔不降速）
    - **Timeout**: `60s`
- **部署指令**:
  > **注意**：首次部署因 URL 尚未生成，需分兩步：
  > 1. 先用 `WEBHOOK_URL=placeholder` 部署取得 Service URL
  > ```bash
  > gcloud run deploy video-to-gif-bot \
  >   --source . \
  >   --region us-central1 \
  >   --platform managed \
  >   --allow-unauthenticated \
  >   --set-env-vars "TELEGRAM_TOKEN=你的Token" \
  >   --set-env-vars "RUN_MODE=webhook" \
  >   --set-env-vars "MAX_CONCURRENT=1" \
  >   --set-env-vars "WEBHOOK_URL=https://placeholder.run.app" \
  >   --memory 2Gi --cpu 2 --timeout 60s --no-cpu-throttling
  > ```
  > 2. 再用 `gcloud run services update` 更新正確的 URL
  > ```bash
  > gcloud run services update video-to-gif-bot \
  >   --region us-central1 \
  >   --update-env-vars "WEBHOOK_URL=https://(你的服務URL)"
  > ```

  ```bash
  # 日常更新程式碼/配置使用此指令
  gcloud run deploy video-to-gif-bot `
    --source . `
    --region us-central1 `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars "TELEGRAM_TOKEN=你的Token" `
    --set-env-vars "RUN_MODE=webhook" \
    --set-env-vars "MAX_CONCURRENT=1" \
    --set-env-vars "WEBHOOK_URL=https://(你的服務URL)" \
    --memory 2Gi --cpu 2 --timeout 60s --no-cpu-throttling
  ```
- **環境變數**:
  - `TELEGRAM_TOKEN`
  - `RUN_MODE=webhook`
  - `WEBHOOK_URL=https://video-to-gif-bot-xxxxx.us-central1.run.app`

### 並發配置建議

| 伺服器規格 | MAX_CONCURRENT | 說明 |
|-----------|----------------|------|
| 0.1 CPU / 512MB | `1` | 完全排隊（Render 免費方案） |
| 0.5 CPU / 1GB | `2` | 輕度並發 |
| 1 CPU / 2GB | `3-4` | 中度並發 |
| 2+ CPU / 4GB+ | `5-8` | 高並發 |

詳細說明請參考 `docs/CONCURRENCY_CONFIG.md`

## 常用命令

```bash
# 安裝依賴
pip install -r requirements.txt

# 本地執行
python app.py

# 檢查 FFmpeg 版本
ffmpeg -version
```

## TICKET 系統開發流程

### 核心原則
- **每次任務都需要建立 TICKET**，無論大小
- **一個 TICKET 只處理一個具體任務**
- **TICKET scope 必須在 1-2 分鐘內可以 review 完畢**
- **遵循 spec → tickets → review → implement → test → commit → update ticket 流程**

### 何時需要建立 TICKET
偵測到以下情況時，必須建立 TICKET：
- 新功能需求: 使用者提出新的功能要求
- 錯誤修復: 發現程式錯誤需要修復
- 技術改進: 程式重構、效能優化、技術債務清理
- 文件更新: API 文件、使用指南、開發文件更新
- 測試建立: 單元測試、整合測試、E2E 測試
- 安全相關: 權限設定、安全漏洞修復
- 部署相關: 部署腳本、環境設定、CI/CD 改進

### TICKET 結構
每個 TICKET 必須包含：
1. **Summary**: 1-2 句話摘要
2. **Why**: 為什麼要做這個任務
3. **Scope**: 範圍和 Out-of-Scope
4. **Acceptance Criteria**: 具體、可測試的驗收標準
5. **Implementation Steps**: 詳細實作步驟
6. **Test/Validation**: 測試計劃和驗證方法

### TICKET 命名規則
- **檔案格式**: `T-YYYYMMDD-NNN-[簡短標題].md`
- **範例**: `T-20251022-001-建立用戶登入功能.md`
- **存放位置**:
  - `docs/tickets/active/` - 進行中的 tickets
  - `docs/tickets/completed/` - 已完成的 tickets
  - `docs/tickets/archive/` - 已封存的 tickets

### AI 提示詞參考
```bash
# 建立 tickets
Please break the plan down into small, easy-to-test, actionable tickets in markdown format and put them in the `docs/tickets/active` folder.

# 執行 ticket
請根據這個 ticket 的需求，實作對應的功能。請確保：
1. 遵循專案的編碼標準和慣例
2. 完成所有 Acceptance Criteria
3. 通過所有測試案例
4. 更新相關文件
```

### Story Points 估計標準
- **1**: 非常簡單，30分鐘內完成
- **2**: 簡單，1小時內完成
- **3**: 中等複雜度，2-4小時完成
- **5**: 複雜，需要1天時間
- **8**: 非常複雜，需要2天以上

### TICKET 狀態管理
- `[ ]` 待處理 → `[ ]` 進行中 → `[ ]` 待測試 → `[ ]` 待審核 → `[x]` 已完成

## 開發優先級

### 必須（每次都要）
- 繁體中文回應
- 錯誤時先查詢再修改
- 遵循 TICKET 系統開發流程

### 重要（特定情況）
- 查閱錯誤案例庫
- 執行測試驗證
- 更新相關文件

### 參考（需要時）
- 詳細實作範例
- 環境配置細節
- 測試腳本模板

---

**更新記錄**:
- 2025-12-07: 初始建立 AI 協作架構
- 2025-12-09: 更新 Cloud Run 部署配置 (US-Central1, 預算監控)

## 成本監控與預算管理 (Cost Management)

由於 Cloud Run 是按需付費，建議定期檢查使用量並設定預算警告。

### 1. 查看免費額度使用詳細報表
1. 進入 [Google Cloud Console Billing](https://console.cloud.google.com/billing)
2. 選擇專案 (`tgbot-videotogif`)
3. 點選左側 **"Reports" (報表)**
4. 右側圖表預設顯示費用 (Cost)。將 **"Metric"** 改為 **"Usage"** 即可看到具體使用量（vCPU-秒、GiB-秒）。
   - **免費額度參考**:
     - vCPU: 每月 180,000 vCPU-秒
     - Mameory: 每月 360,000 GiB-秒
     - Requests: 每月 200 萬次
     - Network Egress (流量): 若在 `us-central1`，每月首 1GB 免費

### 2. 設定預算警告 (Budget Alerts)
強烈建議設定小額預算通知，避免意外爆量。

1. 進入 Billing > **"Budgets & alerts"**
2. 點選 **"Create Budget"**
3. 設定：
   - **Name**: `Cloud Run Safety Net`
   - **Amount**: `$1.00` (設定為 1 美金)
   - **Actions**: 勾選 "Email alerts to billing admins"
4. 當每月費用預估超過 $0.5 或 $1.0 時，Google 就會寄信通知你。
