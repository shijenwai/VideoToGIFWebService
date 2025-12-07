# Video to GIF Telegram Bot - Kiro

本文件為 Kiro IDE 提供此代碼庫的核心工作指引。

## 專案配置

請參考 [PROJECT_CONFIG.md](../../PROJECT_CONFIG.md) 獲取完整的環境資訊和操作指引。

## 通用準則

請參考 [AGENTS.md](../../AGENTS.md) 獲取所有 AI Agent 的通用規則。

## Kiro 專屬設定

### 工具使用偏好

- 優先使用 Kiro 內建工具而非 shell 命令
- 檔案操作使用 fsWrite/strReplace/readFile 工具
- 搜尋使用 grepSearch/fileSearch 工具
- 診斷使用 getDiagnostics 工具檢查程式碼問題

---

**提醒**: AI 輔助開發需要人工驗證和批判性思維確保品質
