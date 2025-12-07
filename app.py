import os
import logging
import subprocess
import time
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 動態並發控制：透過環境變數調整同時處理數量
# MAX_CONCURRENT=1 → 完全排隊（適合 0.1 CPU / 512MB）
# MAX_CONCURRENT=2-3 → 輕度並發（適合 0.5 CPU / 1GB）
# MAX_CONCURRENT=5+ → 高並發（適合 1+ CPU / 2GB+）
MAX_CONCURRENT = int(os.environ.get('MAX_CONCURRENT', '1'))
processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
logger.info(f"🔧 並發控制：最多同時處理 {MAX_CONCURRENT} 個轉檔任務")

# 排隊追蹤器：記錄等待中的任務數量
class QueueTracker:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._waiting_count = 0  # 等待中的任務數
        self._processing_count = 0  # 處理中的任務數
    
    async def join_queue(self) -> int:
        """加入排隊，回傳前面等待的人數"""
        async with self._lock:
            position = self._waiting_count + self._processing_count
            self._waiting_count += 1
            return position
    
    async def start_processing(self):
        """從等待轉為處理中"""
        async with self._lock:
            self._waiting_count -= 1
            self._processing_count += 1
    
    async def finish_processing(self):
        """完成處理"""
        async with self._lock:
            self._processing_count -= 1
    
    async def get_queue_status(self) -> tuple[int, int]:
        """取得目前狀態 (等待中, 處理中)"""
        async with self._lock:
            return self._waiting_count, self._processing_count

queue_tracker = QueueTracker()

# --- 1. 極簡假網頁伺服器 (用來騙過 Render 的健康檢查) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    
    # 關閉 Log 避免洗版
    def log_message(self, format, *args):
        pass

def start_dummy_server():
    # Render 會自動給 PORT 環境變數，預設 10000
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"啟動假網頁伺服器監聽 Port: {port}")
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- 2. 工具函式區 (維持不變) ---
def generate_unique_filename(user_id: int, extension: str) -> str:
    timestamp = int(time.time() * 1000000)
    return f"user_{user_id}_{timestamp}.{extension}"

def cleanup_files(*file_paths: str) -> None:
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

def check_file_size(file_path: str, max_mb: int = 20) -> bool:
    if not os.path.exists(file_path):
        return False
    return (os.path.getsize(file_path) / (1024 * 1024)) <= max_mb

def get_video_duration(input_path: str) -> float:
    """使用 FFprobe 取得影片時長 (秒)"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"無法取得影片時長: {e}")
    return 0

def estimate_start_config(duration: float, file_size_mb: float) -> int:
    """
    根據影片時長和檔案大小，估算應該從哪個配置開始
    回傳 configs 陣列的起始索引
    """
    # 主要根據時長判斷，因為 GIF 大小與幀數（時長×FPS）高度相關
    # 檔案大小作為輔助參考
    complexity = duration * file_size_mb
    
    if duration > 90 or complexity > 1500:   # 超過 1.5 分鐘，或複雜度極高
        return 4                              # 直接從最低品質開始
    elif duration > 60 or complexity > 800:  # 超過 1 分鐘
        return 3
    elif duration > 30 or complexity > 300:  # 超過 30 秒
        return 2
    elif duration > 15 or complexity > 100:  # 超過 15 秒
        return 1
    else:                                    # 15 秒內短影片
        return 0                             # 從最高品質開始

def convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
    """
    使用 FFmpeg 調色盤優化 (palettegen + paletteuse) 產生高品質小檔案 GIF
    會根據影片時長智慧選擇起始配置，減少不必要的嘗試
    """
    # 嘗試不同的 FPS 和寬度組合 (從高品質到低品質)
    configs = [
        (15, 480),  # 高品質
        (12, 400),
        (10, 320),  # 中等
        (8, 280),
        (6, 240),   # 最小
    ]
    
    # 智慧選擇起始配置
    duration = get_video_duration(input_path)
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    start_idx = estimate_start_config(duration, file_size_mb)
    
    logger.info(f"影片分析: 時長={duration:.1f}秒, 大小={file_size_mb:.1f}MB, 從配置 {start_idx} 開始")
    
    palette_path = input_path.replace('.mp4', '_palette.png')
    
    for fps, width in configs[start_idx:]:
        logger.info(f"嘗試 FPS={fps}, 寬度={width}px 轉檔...")
        try:
            # 階段 1: 產生最佳調色盤
            filters = f"fps={fps},scale={width}:-1:flags=lanczos"
            palette_cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', f'{filters},palettegen=stats_mode=diff',
                '-y', palette_path
            ]
            result = subprocess.run(palette_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.warning(f"調色盤產生失敗: {result.stderr}")
                continue
            
            # 階段 2: 使用調色盤輸出 GIF (dither=bayer 可進一步壓縮)
            gif_cmd = [
                'ffmpeg', '-i', input_path, '-i', palette_path,
                '-lavfi', f'{filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5',
                '-y', output_path
            ]
            result = subprocess.run(gif_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.warning(f"GIF 輸出失敗: {result.stderr}")
                continue
            
            # 檢查檔案大小
            if check_file_size(output_path, max_size_mb):
                logger.info(f"轉檔成功！檔案大小: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
                return True
            else:
                size_mb = os.path.getsize(output_path) / (1024*1024)
                logger.info(f"檔案過大 ({size_mb:.2f} MB)，嘗試更低品質...")
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg 轉檔超時")
        except Exception as e:
            logger.error(f"FFmpeg 錯誤: {e}")
        finally:
            # 清理調色盤暫存檔
            if os.path.exists(palette_path):
                os.remove(palette_path)
    
    return False

async def download_video(file, file_path: str) -> bool:
    try:
        await file.download_to_drive(file_path)
        return True
    except Exception:
        return False

# --- 3. Bot 邏輯 ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /start 指令，回傳使用說明"""
    welcome_text = (
        "👋 嗨！我是影片轉 GIF 機器人\n\n"
        "📖 使用方式：\n"
        "直接傳送影片給我，我會自動轉換成 GIF 檔案回傳給你！\n\n"
        "⚠️ 注意事項：\n"
        "• 檔案大小限制 20MB（超過會提示如何處理）\n"
        "• 輸出 GIF 會自動優化品質與檔案大小\n\n"
        "🚀 現在就傳一個影片試試吧！"
    )
    await update.message.reply_text(welcome_text)

async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    input_path = None
    output_path = None
    user_id = update.effective_user.id
    
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("❌ 格式錯誤：請傳送影片檔案")
        return
    
    # 檢查檔案大小 (Telegram Bot API 限制 20MB 下載)
    file_size_mb = video.file_size / (1024 * 1024) if video.file_size else 0
    if file_size_mb > 20:
        await update.message.reply_text(
            f"❌ 檔案過大 ({file_size_mb:.1f} MB)\n\n"
            "Telegram Bot API 限制最大 20MB。\n"
            "💡 提示：傳送影片時可選擇較低畫質來縮小檔案。"
        )
        return
    
    # 取得影片檔名（用於訊息顯示）
    video_name = video.file_name or "未命名影片"
    
    # 加入排隊並取得前面等待人數
    position = await queue_tracker.join_queue()
    
    if position > 0:
        await update.message.reply_text(
            f"📹 收到影片！\n"
            f"📁 {video_name}\n\n"
            f"⏳ 目前排隊中，前面還有 {position} 個任務\n"
            f"請稍候，輪到您時會自動開始轉檔..."
        )
    else:
        await update.message.reply_text(f"📹 收到影片「{video_name}」！正在為您轉檔中...")
    
    # 排隊機制：超過並發限制時會在此等待
    async with processing_semaphore:
        await queue_tracker.start_processing()
        
        # 如果有排隊，通知使用者已開始處理
        if position > 0:
            await update.message.reply_text(f"🚀 輪到您了！正在轉檔「{video_name}」...")
        
        try:
            file = await video.get_file()
        except Exception as e:
            logger.error(f"取得檔案失敗: {e}")
            await update.message.reply_text("❌ 無法取得檔案，請稍後再試")
            await queue_tracker.finish_processing()
            return
            
        input_path = f"/tmp/{generate_unique_filename(user_id, 'mp4')}"
        output_path = f"/tmp/{generate_unique_filename(user_id, 'gif')}"
        
        try:
            if not await download_video(file, input_path):
                await update.message.reply_text("❌ 下載失敗，請稍後再試")
                return
            
            # 在執行緒池中執行阻塞的轉檔操作，避免卡住 event loop
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, convert_to_gif_with_retry, input_path, output_path
            )
            
            if not success:
                await update.message.reply_text(
                    "❌ 轉檔失敗\n\n"
                    "可能原因：影片太長導致 GIF 超過 20MB 限制。\n"
                    "💡 建議：使用較短的影片片段（約 15-30 秒內效果最佳）"
                )
                return

            # 上傳 GIF，大檔案需要更長 timeout，加入重試機制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(output_path, 'rb') as gif_file:
                        await update.message.reply_document(
                            document=gif_file, 
                            filename=f"video_{user_id}.gif",
                            disable_content_type_detection=True,
                            read_timeout=120, write_timeout=120, connect_timeout=60
                        )
                    logger.info(f"User {user_id} 轉檔成功")
                    break
                except Exception as upload_err:
                    if attempt < max_retries - 1:
                        logger.warning(f"上傳失敗 (嘗試 {attempt + 1}/{max_retries}): {upload_err}")
                        await asyncio.sleep(2)  # 等待 2 秒後重試
                    else:
                        raise upload_err

        except Exception as e:
            logger.exception("處理錯誤")
            await update.message.reply_text("❌ 發生未知錯誤，請稍後再試")
        finally:
            cleanup_files(input_path, output_path)
            await queue_tracker.finish_processing()

if __name__ == '__main__':
    # 讀取 Token
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        logger.critical("未設定 TELEGRAM_TOKEN")
        exit(1)

    # A. 啟動假網頁伺服器 (在背景執行，不卡住主程式)
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # B. 啟動 Bot (Polling)
    # concurrent_updates=True 允許同時處理多個訊息，不會互相阻塞
    application = Application.builder().token(token).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_to_gif_handler))
    
    logger.info("✅ Bot 已啟動 (Render Hybrid Mode)")
    application.run_polling()