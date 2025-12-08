# TICKET: Support Local .env Configuration

## Description
為了方便本地開發與測試，並避免將機密資訊（如 Telegram Token）提交至版本控制系統，需要引入環境變數管理機制。
同時，為避免與線上 Cloud Run 環境衝突，本機開發應使用獨立的測試 Bot Token。

## Acceptance Criteria
- [x] 專案引入 `python-dotenv` 套件
- [x] `app.py` 啟動時能自動載入 `.env` 檔案中的環境變數
- [x] `.env` 檔案被加入 `.gitignore`，確保不會被提交
- [x] 本機開發能透過設置新的 Token 獨立運作，不影響線上服務

## Implementation Plan
1. 修改 `requirements.txt` 加入 `python-dotenv`
2. 修改 `app.py` 在程式入口載入 dotenv
3. 更新 `.gitignore`
4. 建立 `.env` 範本（僅在本地生成，不提交）

## Verification
- [x] 本地執行 `python app.py` 能成功讀取 .env 中的設定
- [x] 若無 .env 檔案（如線上環境），程式仍能正常透過系統環境變數運作
