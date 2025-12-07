# PROJECT_CONFIG.md - 專案配置

本文件為專案的核心配置檔，所有 AI 工具（Claude、Codex、Gemini）皆參考此檔案。

## 專案資訊

- **專案名稱**: Video to GIF Telegram Bot
- **專案描述**: 將 Telegram 影片轉換為 GIF 的機器人，部署於 Render
- **技術棧**: Python 3.10+, python-telegram-bot, FFmpeg

## 環境資訊

- **開發環境**: 本地執行 `python app.py`
- **部署平台**: Render (Free Tier)
- **執行模式**: Hybrid Mode (Polling + HTTP Health Check)

### 環境變數

| 變數名稱 | 說明 |
|---------|------|
| `TELEGRAM_TOKEN` | Telegram Bot Token (從 @BotFather 取得) |

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
