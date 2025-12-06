import os
import logging
import asyncio
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 工具函式區 (保持不變) ---
import time
def generate_unique_filename(user_id: int, extension: str) -> str:
    timestamp = int(time.time() * 1000000)
    return f"user_{user_id}_{timestamp}.{extension}"

def cleanup_files(*file_paths: str) -> None:
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已刪除暫存檔: {file_path}")
            except Exception as e:
                logger.error(f"刪除檔案失敗 {file_path}: {e}")

def check_file_size(file_path: str, max_mb: int = 20) -> bool:
    if not os.path.exists(file_path):
        return False
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    return file_size_mb <= max_mb

def convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
    fps_options = [20, 15, 10]
    for fps in fps_options:
        logger.info(f"嘗試使用 {fps} FPS 轉檔...")
        # 注意: HF Free Tier CPU 較弱，增加 timeout 到 600秒
        cmd = ['ffmpeg', '-i', input_path, '-vf', f'fps={fps},scale=320:-1:flags=lanczos', '-y', output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                logger.error(f"FFmpeg 轉檔失敗 (FPS={fps}): {result.stderr}")
                continue
            if check_file_size(output_path, max_size_mb):
                return True
            else:
                if os.path.exists(output_path): os.remove(output_path)
        except Exception as e:
            logger.error(f"FFmpeg 錯誤: {e}")
    return False

async def download_video(file, file_path: str) -> bool:
    try:
        await file.download_to_drive(file_path)
        return True
    except Exception as e:
        logger.error(f"下載失敗: {e}")
        return False

async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    input_path = None
    output_path = None
    try:
        user_id = update.effective_user.id
        await update.message.reply_text("📹 收到影片！轉檔中，HF 免費版運算較慢請稍候...")
        
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
            await update.message.reply_text("❌ 轉檔失敗 (可能檔案太大或超時)")
            return

        await update.message.reply_document(document=open(output_path, 'rb'), filename=f"video_{user_id}.gif")
        logger.info(f"User {user_id} 轉檔成功")

    except Exception as e:
        logger.exception("處理錯誤")
        await update.message.reply_text("❌ 發生未知錯誤")
    finally:
        cleanup_files(input_path, output_path)

# --- 核心修改：背景啟動器 ---
async def start_polling_bot():
    """在背景無限重試連線，直到成功"""
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        logger.error("❌ 未設定 TELEGRAM_TOKEN")
        return

    retry_count = 0
    while True:
        application = None # 初始化變數
        try:
            logger.info("⏳ Bot 正在背景嘗試連線 (Polling)...")
            
            # --- 關鍵修正：將 Application 建立移入迴圈內 ---
            # 每次重試都產生一個全新的實例，避免上次失敗的髒狀態殘留
            application = Application.builder().token(token).build()
            application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_to_gif_handler))
            
            await application.initialize()
            await application.start()
            # Drop pending updates 避免重啟時處理舊訊息
            await application.updater.start_polling(drop_pending_updates=True)
            
            logger.info("✅ Telegram Bot 連線成功！")
            
            # 保持運行
            while True:
                await asyncio.sleep(3600)
                
        except Exception as e:
            # 如果建立過 application，嘗試安全關閉它
            if application:
                try:
                    await application.shutdown()
                except:
                    pass
            
            retry_count += 1
            wait_time = min(retry_count * 5, 60)
            logger.warning(f"⚠️ 連線失敗 ({retry_count}): {e}。等待 {wait_time} 秒後重試...")
            await asyncio.sleep(wait_time)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 啟動背景任務 (不會卡住 FastAPI 啟動)
    asyncio.create_task(start_polling_bot())
    yield
    # 關閉邏輯 (HF 強制關閉時通常來不及執行，可忽略)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "alive", "mode": "polling"}