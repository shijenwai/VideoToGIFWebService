# 並發控制配置指南

## 環境變數：MAX_CONCURRENT

控制 Bot 同時處理的轉檔任務數量。

## 推薦配置

| 伺服器規格 | MAX_CONCURRENT | 說明 |
|-----------|----------------|------|
| 0.1 CPU / 512MB | `1` | 完全排隊，避免資源耗盡（Render 免費方案） |
| 0.5 CPU / 1GB | `2` | 輕度並發 |
| 1 CPU / 2GB | `3-4` | 中度並發 |
| 2+ CPU / 4GB+ | `5-8` | 高並發 |

## 設定方式

### Render.com
1. 進入 Dashboard → Environment
2. 新增環境變數：
   ```
   Key: MAX_CONCURRENT
   Value: 1
   ```
3. 儲存後自動重啟

### Docker
```bash
docker run -e MAX_CONCURRENT=2 your-image
```

### 本地測試
```bash
export MAX_CONCURRENT=3  # Linux/Mac
set MAX_CONCURRENT=3     # Windows CMD
$env:MAX_CONCURRENT=3    # Windows PowerShell
```

## 行為說明

### MAX_CONCURRENT=1（預設）
- A 上傳影片 → 立即處理
- B 上傳影片 → **等待 A 完成**
- C 上傳影片 → **等待 B 完成**
- 優點：資源使用穩定，不會崩潰
- 缺點：高峰時段等待時間較長

### MAX_CONCURRENT=3
- A、B、C 上傳 → 同時處理
- D 上傳 → **等待前三者之一完成**
- 優點：提升吞吐量
- 缺點：需要足夠的 CPU/記憶體

## 監控與調整

### 觀察指標
1. **記憶體使用率**：超過 80% → 降低並發數
2. **CPU 使用率**：持續 100% → 降低並發數
3. **轉檔失敗率**：頻繁超時 → 降低並發數
4. **平均等待時間**：過長 → 提升並發數（若資源允許）

### 調整建議
- 從保守值（1）開始
- 逐步增加並觀察穩定性
- 找到「不崩潰的最大值」

## 日誌確認

Bot 啟動時會顯示：
```
🔧 並發控制：最多同時處理 1 個轉檔任務
```

確認此數字符合預期配置。

## 未來升級路徑

當流量成長到單機無法負荷時，參考：
- `docs/tickets/archive/queue-system-redis-celery.md`
- 實作分散式佇列系統
