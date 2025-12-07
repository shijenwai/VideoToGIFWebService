# Video to GIF Telegram Bot - OpenAI Codex

本文件為 OpenAI Codex 提供此代碼庫的核心工作指引。

## 專案配置

請參考 [PROJECT_CONFIG.md](./PROJECT_CONFIG.md) 獲取完整的環境資訊和操作指引。

## 通用準則

請參考 [AGENTS.md](./AGENTS.md) 獲取所有 AI Agent 的通用規則。

## Codex 專屬設定

### 專案特定注意事項

- 此專案使用 async/await 模式 (python-telegram-bot v20+)
- FFmpeg 命令需在 `run_in_executor` 中執行以避免阻塞
- 暫存檔案需確保清理 (使用 try/finally)

---

**提醒**: AI 輔助開發需要人工驗證和批判性思維確保品質
