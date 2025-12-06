---
title: Video To GIF Bot
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Video to GIF Telegram Bot

這是一個 Telegram Bot，可以將使用者傳送的影片轉換為 GIF 動圖。

## 功能特色

- 📹 支援多種影片格式
- 🎨 保持原始解析度
- ⚡ 漸進式 FPS 優化 (20→15→10 fps)
- 📦 自動控制檔案大小 (≤20MB)
- 🧹 自動清理暫存檔案

## 使用方式

1. 在 Telegram 搜尋你的 Bot
2. 傳送影片給 Bot
3. 等待轉換完成
4. 接收 GIF 檔案

## 環境變數設定

需要在 Hugging Face Space Settings → Repository secrets 設定：

- `TELEGRAM_TOKEN`: 你的 Telegram Bot Token

## 技術架構

- Python 3.10+
- python-telegram-bot v20+
- FFmpeg
