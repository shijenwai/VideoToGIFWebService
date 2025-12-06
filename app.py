import os
import logging
import subprocess
import time
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 工具函式區 (保持不變) ---
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
    # Render 免費版 CPU 也不強，維持 320p + lanczos 是好選擇
    fps_options = [15, 10] 
    
    for fps in fps_options:
        logger.info(f"嘗試使用 {fps} FPS 轉檔...")
        cmd = ['ffmpeg', '-i', input_path, '-vf', f'fps={fps},scale=320:-1:flags=lanczos', '-y', output_path]
        try:
            # Render 不會像 HF 那樣亂殺 Process，但設個 Timeout 是好習慣
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
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

# --- Bot 處理邏輯 ---
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
            await update.message.reply_text("❌ 轉檔失敗")
            return

        await update.message.reply_document(
            document=open(output_path, 'rb'), 
            filename=f"video_{user_id}.gif",
            read_timeout=60, 
            write_timeout=60, 
            connect_timeout=60
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
        logger.critical("未設定 TELEGRAM_TOKEN，程式終止")
        exit(1)

    # 建立與啟動 Bot (最簡潔的 Polling 寫法)
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_to_gif_handler))
    
    logger.info("✅ Bot 已啟動 (Render Polling Mode)")
    application.run_polling()