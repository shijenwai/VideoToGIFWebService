# T-20251207-004-修復UptimeRobot健康檢查HEAD請求

## Summary
為 HealthCheckHandler 新增 `do_HEAD` 方法，讓 UptimeRobot 的 HEAD 請求能正確回傳 200 OK。

## Why
- UptimeRobot 預設使用 `HEAD` 請求檢查網站狀態
- 目前 `HealthCheckHandler` 只有 `do_GET`，沒有 `do_HEAD`
- Python `BaseHTTPRequestHandler` 對未定義的 method 回傳 `501 Not Implemented`
- 導致 UptimeRobot 判定網站 Down，但實際上 Bot 功能正常

## Scope

### In Scope
- [ ] 在 `HealthCheckHandler` 新增 `do_HEAD` 方法

### Out of Scope
- 不修改其他健康檢查邏輯
- 不變更現有 `do_GET` 行為

## Acceptance Criteria
- [ ] `HealthCheckHandler` 包含 `do_HEAD` 方法
- [ ] HEAD 請求回傳 HTTP 200 狀態碼
- [ ] UptimeRobot 顯示 Up 狀態

## Implementation Steps
1. 在 `app.py` 的 `HealthCheckHandler` class 中新增 `do_HEAD` 方法
2. 方法內容：回傳 200 狀態碼和 Content-type header（不需 body）
3. Push 到 GitHub 觸發 Render 重新部署
4. 等待 UptimeRobot 下次檢查確認狀態

## Code Change

```python
# 在 HealthCheckHandler class 中新增：
def do_HEAD(self):
    """處理 UptimeRobot 的 HEAD 請求"""
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()
```

## Test/Validation
- [ ] 本地測試：`curl -I http://localhost:10000` 回傳 200
- [ ] 部署後 UptimeRobot 狀態變為 Up

## Story Points
1

## Status
- [ ] 待處理
- [ ] 進行中
- [x] 待測試
- [ ] 待審核
- [ ] 已完成

## Notes
- 此問題由 Gemini 分析發現，經驗證確認分析正確
- 修改極小（僅新增 4 行程式碼），風險低
