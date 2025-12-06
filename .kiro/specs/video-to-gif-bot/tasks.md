# Implementation Plan

- [x] 1. 建立專案配置檔案

  - [x] 1.1 建立 `packages.txt` 系統依賴檔案


    - 加入 `ffmpeg` 依賴
    - 加入中文註解說明 HF Spaces 特有機制


    - _Requirements: 1.1_

  - [x] 1.2 建立 `requirements.txt` Python 依賴檔案


    - 加入 `python-telegram-bot` 套件
    - _Requirements: 1.2_

- [ ] 2. 實作核心工具函式
  - [x] 2.1 建立 `app.py` 並實作檔名生成函式


    - 實作 `generate_unique_filename(user_id: int, extension: str) -> str`
    - 使用 user_id + 時間戳確保唯一性
    - _Requirements: 3.2_
  - [ ]* 2.2 撰寫 Property Test: 唯一檔名生成
    - **Property 1: 唯一檔名生成**

    - **Validates: Requirements 3.2**


  - [ ] 2.3 實作暫存檔清理函式
    - 實作 `cleanup_files(*file_paths: str) -> None`
    - 使用 try-except 確保不因檔案不存在而拋錯
    - _Requirements: 6.1, 6.2_
  - [x]* 2.4 撰寫 Property Test: 暫存檔清理保證

    - **Property 3: 暫存檔清理保證**
    - **Validates: Requirements 5.3, 6.1**

- [ ] 3. 實作 FFmpeg 轉檔邏輯
  - [ ] 3.1 實作 FFmpeg 轉檔函式 (漸進式 FPS 策略)
    - 實作 `convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool`

    - 使用 subprocess 呼叫 FFmpeg


    - 漸進式嘗試 FPS: 20→15→10 (優先保持高畫質)
    - 每次轉檔後檢查檔案大小，超過 20MB 則降低 FPS 重試


    - 保持原始解析度不縮放
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  - [x] 3.2 實作檔案大小檢查函式


    - 實作 `check_file_size(file_path: str, max_mb: int = 20) -> bool`


    - 檢查 GIF 是否超過 20MB 限制
    - _Requirements: 4.4_
  - [ ]* 3.3 撰寫 Property Test: GIF 檔案大小限制
    - **Property 2: GIF 檔案大小限制**
    - **Validates: Requirements 4.4**

- [ ] 4. 實作 Telegram Bot Handler
  - [ ] 4.1 實作影片下載函式
    - 實作 `download_video(file: File, file_path: str) -> bool`
    - 下載影片到 /tmp 暫存目錄
    - _Requirements: 3.1, 3.3_
  - [ ] 4.2 實作主要 Handler 函式
    - 實作 `video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`
    - 整合下載、轉檔、回傳、清理流程
    - 使用 try-finally 確保暫存檔清理
    - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.2, 5.3_

- [ ] 5. 實作 Bot 主程式與啟動邏輯
  - [ ] 5.1 實作 main 函式與 Bot 初始化
    - 使用 `ApplicationBuilder` 建立 Bot
    - 從環境變數 `TELEGRAM_TOKEN` 讀取 Token
    - 註冊 `MessageHandler` (filters.VIDEO | filters.document.VIDEO)
    - 使用 `application.run_polling()` 啟動
    - _Requirements: 1.3, 7.1, 7.2, 7.3_

- [ ] 6. Checkpoint - 確保所有測試通過
  - Ensure all tests pass, ask the user if questions arise.
