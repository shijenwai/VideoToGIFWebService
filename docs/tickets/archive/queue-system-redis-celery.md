# T-20251207-001-分散式佇列系統升級

## Summary
實作基於 Redis + Celery 的分散式任務佇列，支援多台伺服器橫向擴展與高並發處理。

## Why
當流量成長到單機無法負荷（日活躍 > 100 人或單日請求 > 500 次）時，需要分散式架構來：
- 支援多 worker 橫向擴展
- 提供任務持久化與自動重試
- 實現可視化監控與管理

## Scope

### In Scope
- [ ] 安裝與配置 Redis 服務
- [ ] 建立 Celery 任務定義 (`tasks.py`)
- [ ] 修改 Bot 邏輯改為提交任務而非直接執行
- [ ] 部署至少 1 個 Celery worker
- [ ] 設定環境變數與連線配置
- [ ] 實作基本錯誤重試機制
- [ ] （選用）部署 Flower 監控介面

### Out of Scope
- 多地區部署與 CDN
- 進階監控告警系統
- 自動擴展 (Auto-scaling)

## Acceptance Criteria
- [ ] Bot 收到影片後能成功提交任務到 Redis 佇列
- [ ] Celery worker 能從佇列取得任務並執行轉檔
- [ ] 轉檔完成後能正確回傳 GIF 給使用者
- [ ] 任務失敗時能自動重試最多 3 次
- [ ] 支援至少 2 個 worker 同時處理任務
- [ ] 系統能承受 100+ 並發請求不崩潰

## Implementation Steps

### 1. 環境準備
```bash
pip install celery[redis] redis flower
```

### 2. 建立 tasks.py
```python
from celery import Celery
import os

app = Celery('video_tasks',
             broker=os.environ['CELERY_BROKER_URL'],
             backend=os.environ['CELERY_RESULT_BACKEND'])

@app.task(bind=True, max_retries=3)
def convert_video_task(self, input_path, output_path):
    try:
        return convert_to_gif_with_retry(input_path, output_path)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

### 3. 修改 app.py
- 移除 `run_in_executor` 邏輯
- 改為 `task = convert_video_task.delay(input_path, output_path)`
- 實作結果輪詢或 callback 機制

### 4. 部署 Worker
```bash
celery -A tasks worker --loglevel=info --concurrency=2
```

### 5. 環境變數設定
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 6. （選用）啟動監控
```bash
celery -A tasks flower --port=5555
```

## Test/Validation
- [ ] 單一使用者上傳影片能正常轉檔
- [ ] 10 個使用者同時上傳，全部成功處理
- [ ] 模擬 worker 崩潰，任務能自動重試
- [ ] 檢查 Redis 佇列狀態正常
- [ ] Flower 介面能顯示任務統計

## Story Points
8（需要 2 天以上）

## Status
- [ ] 待處理
- [ ] 進行中
- [ ] 待測試
- [ ] 待審核
- [ ] 已完成
- [x] 已封存（未來擴展選項）

## Notes

### 架構圖
```
User → Telegram Bot → Redis Queue → Celery Workers (多台) → FFmpeg
                                  ↓
                              Result Storage
```

### 成本考量
- Redis 服務：可用免費方案（Redis Labs 25MB 免費額度）
- 至少需要 2 台伺服器（Bot + Worker）
- 增加系統複雜度與維護成本

### 觸發條件
當以下任一條件成立時考慮實作：
- 日活躍使用者 > 100 人
- 單日轉檔請求 > 500 次
- 需要多地區部署
- 有預算支持付費服務

### 參考資源
- [Celery 官方文件](https://docs.celeryq.dev/)
- [Redis 免費方案](https://redis.io/docs/about/redis-cloud/)
- [Telegram Bot + Celery 範例](https://github.com/topics/telegram-bot-celery)

### 現況
目前使用 `asyncio.Semaphore` 的簡單排隊機制已足夠應付中小規模使用（< 50 人）。
此 ticket 作為未來擴展的技術儲備。
