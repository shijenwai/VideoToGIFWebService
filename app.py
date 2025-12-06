import os
import logging
import subprocess
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
    """
    使用 FFmpeg 調色盤優化 (palettegen + paletteuse) 產生高品質小檔案 GIF
    會依序嘗試不同 FPS 和解析度組合，直到檔案大小符合限制
    """
    # 嘗試不同的 FPS 和寬度組合 (從高品質到低品質)
    configs = [
        (15, 480),  # 高品質
        (12, 400),
        (10, 320),  # 中等
        (8, 280),
        (6, 240),   # 最小
    ]
    
    palette_path = input_path.replace('.mp4', '_palette.png')
    
    for fps, width in configs:
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
        "• 支援 MP4、MOV 等常見影片格式\n"
        "• 建議影片長度在 30 秒內\n"
        "• 輸出 GIF 會自動壓縮至 20MB 以下\n\n"
        "🚀 現在就傳一個影片試試吧！"
    )
    await update.message.reply_text(welcome_text)

async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    input_path = None
    output_path = None
    try:
        user_id = update.effective_user.id
        await update.message.reply_text("📹 收到影片！Render 機器人正在為您轉檔中...")
        
        video = update.message.video or update.message.document
        if not video:
            await update.message.reply_text("❌ 格式錯誤")
            return

        file = await video.get_file()
        input_path = f"/tmp/{generate_unique_filename(user_id, 'mp4')}"
        output_path = f"/tmp/{generate_unique_filename(user_id, 'gif')}"
        
        if not await download_video(file, input_path):
            await update.message.reply_text("❌ 下載失敗")
            return
            
        if not convert_to_gif_with_retry(input_path, output_path):
            await update.message.reply_text("❌ 轉檔失敗 (檔案過大或超時)")
            return

        await update.message.reply_document(
            document=open(output_path, 'rb'), 
            filename=f"video_{user_id}.gif",
            disable_content_type_detection=True,
            read_timeout=60, write_timeout=60, connect_timeout=60
        )
        logger.info(f"User {user_id} 轉檔成功")

    except Exception as e:
        logger.exception("處理錯誤")
        await update.message.reply_text("❌ 發生未知錯誤")
    finally:
        cleanup_files(input_path, output_path)

if __name__ == '__main__':
    # 讀取 Token
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        logger.critical("未設定 TELEGRAM_TOKEN")
        exit(1)

    # A. 啟動假網頁伺服器 (在背景執行，不卡住主程式)
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # B. 啟動 Bot (Polling)
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_to_gif_handler))
    
    logger.info("✅ Bot 已啟動 (Render Hybrid Mode)")
    application.run_polling()