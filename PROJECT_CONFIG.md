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
- **特性**: Scale-to-Zero、按需付費
- **預設並發**: 建議 `MAX_CONCURRENT=1`（避免冷啟動衝突）
- **環境變數**:
  - `TELEGRAM_TOKEN`
  - `RUN_MODE=webhook`
  - `WEBHOOK_URL=https://your-service-xxx.run.app`

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
