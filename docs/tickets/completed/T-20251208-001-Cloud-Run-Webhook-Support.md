# T-20251208-001: Cloud Run Webhook 支援

**狀態**: [x] 已完成  
**建立日期**: 2025-12-08  
**Story Points**: 3  
**分支**: `feature/cloud-run-support`

---

## Summary

將專案從 Render Polling 模式遷移至支援 Google Cloud Run Webhook 模式，實現 Scale-to-Zero 架構，並透過 Fail Fast 機制解決 Telegram 60 秒超時重試問題。

## Why

- **成本優化**: Cloud Run 支援 Scale-to-Zero，閒置時不收費
- **架構彈性**: 支援 Webhook 與 Polling 雙模式，可依部署平台切換
- **避免 Retry Storm**: Telegram Webhook 有 60 秒限制，超時會觸發重試，需主動截斷長時間任務

## Scope

### In Scope
- [x] Dockerfile 優化（python:3.10-slim、清理暫存、編譯優化）
- [x] 實作 `RUN_MODE` 環境變數切換 Webhook/Polling 模式
- [x] Webhook 模式下 FFmpeg timeout 縮減至 50 秒
- [x] 新增 `subprocess.TimeoutExpired` 錯誤處理與使用者提示
- [x] 更新 PROJECT_CONFIG.md 文件

### Out of Scope
- Cloud Run 實際部署與 CI/CD 設定
- 效能基準測試
- 分片處理（長影片分段轉檔）

## Acceptance Criteria

- [x] 不設定 `RUN_MODE` 時，使用 Polling 模式（向後相容 Render）
- [x] 設定 `RUN_MODE=webhook` 時，使用 Webhook 模式
- [x] Webhook 模式需設定 `WEBHOOK_URL` 否則報錯退出
- [x] Webhook 路徑包含 Token 確保安全性
- [x] Webhook 模式下啟用 `drop_pending_updates=True`
- [x] FFmpeg timeout 在 Webhook 模式為 50 秒，Polling 模式為 300 秒
- [x] 超時時顯示友善錯誤訊息給使用者
- [x] 語法檢查通過（`python -m py_compile app.py`）

## Implementation Steps

1. [x] 建立分支 `feature/cloud-run-support`
2. [x] 優化 Dockerfile
   - Base image: `python:3.10` → `python:3.10-slim`
   - 新增 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONUNBUFFERED=1`
   - 使用 `--no-install-recommends` 減少安裝體積
3. [x] 修改 app.py 支援雙模式
   - 讀取 `RUN_MODE` 環境變數
   - 新增 `FFMPEG_TIMEOUT` 動態設定
   - 重構 `if __name__ == '__main__'` 區塊
4. [x] 實作 Fail Fast 機制
   - 捕捉 `subprocess.TimeoutExpired` 例外
   - 回傳清晰的超時錯誤訊息
5. [x] 更新 PROJECT_CONFIG.md 文件
6. [x] 語法驗證與提交

## Test/Validation

- [x] `python -m py_compile app.py` 語法檢查通過
- [ ] 本地 Polling 模式啟動測試（需 TELEGRAM_TOKEN）
- [ ] Cloud Run 部署後 Webhook 模式測試

## Commit

```
feat: Add Cloud Run Webhook support with Fail Fast mechanism

- Dockerfile: Use python:3.10-slim, add PYTHONDONTWRITEBYTECODE/UNBUFFERED
- app.py: Implement RUN_MODE switch for webhook/polling dual mode
- app.py: Reduce FFmpeg timeout to 50s in webhook mode
- app.py: Add subprocess.TimeoutExpired handler with user-friendly message
- PROJECT_CONFIG.md: Document dual-mode configuration
```

## 相關文件

- `Dockerfile` - 容器映像檔配置
- `app.py` - 主程式（雙模式邏輯）
- `PROJECT_CONFIG.md` - 專案配置文件

---

**完成日期**: 2025-12-08
