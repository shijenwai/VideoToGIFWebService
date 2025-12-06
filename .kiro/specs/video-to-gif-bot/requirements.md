# Requirements Document

## Introduction

本專案在 Hugging Face Spaces (Free CPU Basic) 平台上實作一個 Telegram Bot。Bot 的核心功能是接收使用者傳送的影片檔案，使用 FFmpeg 將其轉換為 GIF 動圖，並回傳給使用者。

## Glossary

- **Bot**: Telegram Bot 應用程式，負責接收訊息、處理影片並回傳結果
- **FFmpeg**: 開源多媒體處理工具，用於影片轉 GIF 轉檔
- **HF Spaces**: Hugging Face Spaces 平台，提供免費 CPU 運算環境
- **Polling**: Telegram Bot 主動輪詢伺服器取得更新的運作模式
- **暫存區**: `/tmp` 目錄，用於暫時儲存下載的影片與生成的 GIF

## Requirements

### Requirement 1: 環境配置

**User Story:** As a 開發者, I want to 正確配置 HF Spaces 環境依賴, so that Bot 能在平台上正常運行。

#### Acceptance Criteria

1. WHEN HF Spaces 建置環境時, THE Bot SHALL 透過 `packages.txt` 安裝 FFmpeg 系統依賴
2. WHEN HF Spaces 建置環境時, THE Bot SHALL 透過 `requirements.txt` 安裝 `python-telegram-bot` v20+ 套件
3. WHEN Bot 啟動時, THE Bot SHALL 從環境變數 `TELEGRAM_TOKEN` 讀取 Telegram API Token

### Requirement 2: 影片接收

**User Story:** As a 使用者, I want to 傳送影片給 Bot, so that Bot 能接收並處理我的影片。

#### Acceptance Criteria

1. WHEN 使用者傳送影片訊息 (filters.VIDEO) 時, THE Bot SHALL 接收並開始處理該影片
2. WHEN 使用者傳送影片檔案 (filters.document.VIDEO) 時, THE Bot SHALL 接收並開始處理該檔案
3. WHEN Bot 收到影片時, THE Bot SHALL 回覆確認訊息告知使用者正在處理

### Requirement 3: 影片下載

**User Story:** As a Bot, I want to 下載使用者的影片到暫存區, so that 能進行後續轉檔處理。

#### Acceptance Criteria

1. WHEN Bot 接收到影片時, THE Bot SHALL 將影片下載至 `/tmp` 暫存目錄
2. WHEN 下載影片時, THE Bot SHALL 使用唯一檔名避免多使用者同時使用時的檔案衝突
3. IF 影片下載失敗, THEN THE Bot SHALL 回傳友善錯誤訊息給使用者

### Requirement 4: 影片轉 GIF

**User Story:** As a 使用者, I want to 將影片轉換為 GIF, so that 我能獲得方便分享的動圖格式。

#### Acceptance Criteria

1. WHEN Bot 執行轉檔時, THE Bot SHALL 呼叫 FFmpeg 將影片轉換為 GIF 格式
2. WHEN Bot 執行轉檔時, THE Bot SHALL 保持原始影片解析度不做縮放
3. WHEN Bot 執行轉檔時, THE Bot SHALL 優先使用 20fps 幀率以保持畫質
4. IF 轉檔後 GIF 超過 20MB, THEN THE Bot SHALL 依序降低幀率 (20→15→10fps) 重新轉檔直到符合大小限制
5. WHEN Bot 執行轉檔時, THE Bot SHALL 確保輸出 GIF 檔案大小不超過 20MB
6. WHEN Bot 執行轉檔時, THE Bot SHALL 使用速度優先的 FFmpeg 參數以適應 HF 免費 CPU 限制
7. IF 轉檔過程失敗, THEN THE Bot SHALL 回傳友善錯誤訊息說明轉檔失敗

### Requirement 5: GIF 回傳

**User Story:** As a 使用者, I want to 收到轉換完成的 GIF, so that 我能下載並使用該動圖。

#### Acceptance Criteria

1. WHEN 轉檔成功完成時, THE Bot SHALL 將生成的 GIF 檔案傳送給使用者
2. IF GIF 檔案過大無法傳送, THEN THE Bot SHALL 回傳友善錯誤訊息說明檔案過大
3. WHEN GIF 傳送完成後, THE Bot SHALL 刪除 `/tmp` 下的暫存檔案 (輸入影片與輸出 GIF)

### Requirement 6: 資源清理

**User Story:** As a 系統管理者, I want to Bot 自動清理暫存檔案, so that 避免 HF Spaces 儲存空間不足。

#### Acceptance Criteria

1. WHEN 處理流程結束時 (無論成功或失敗), THE Bot SHALL 刪除該次處理產生的所有暫存檔案
2. WHEN 刪除暫存檔案時, THE Bot SHALL 使用 try-finally 或類似機制確保清理必定執行

### Requirement 7: Bot 運行

**User Story:** As a 開發者, I want to Bot 使用 Polling 模式運行, so that 能在 HF Spaces 環境穩定運作。

#### Acceptance Criteria

1. WHEN Bot 啟動時, THE Bot SHALL 使用 `python-telegram-bot` v20+ 的 `ApplicationBuilder` 建立應用程式
2. WHEN Bot 啟動時, THE Bot SHALL 使用 `application.run_polling()` 啟動輪詢模式
3. WHEN Bot 運行時, THE Bot SHALL 使用 async/await 非同步寫法處理訊息
