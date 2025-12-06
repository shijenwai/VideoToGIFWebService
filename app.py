import os
import logging
import time
import subprocess
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 全域 Application 實例
ptb_application: Application = None


def generate_unique_filename(user_id: int, extension: str) -> str:
    """生成唯一檔名以避免多使用者同時使用時的檔案衝突"""
    timestamp = int(time.time() * 1000000)
    return f"user_{user_id}_{timestamp}.{extension}"


def cleanup_files(*file_paths: str) -> None:
    """清理暫存檔案"""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已刪除暫存檔: {file_path}")
            except Exception as e:
                logger.error(f"刪除檔案失敗 {file_path}: {e}")


def check_file_size(file_path: str, max_mb: int = 20) -> bool:
    """檢查檔案大小是否超過限制"""
    if not os.path.exists(file_path):
        return False
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    logger.info(f"檔案大小: {file_size_mb:.2f} MB")
    return file_size_mb <= max_mb


def convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
    """使用漸進式 FPS 策略將影片轉換為 GIF"""
    fps_options = [20, 15, 10]
    
    for fps in fps_options:
        logger.info(f"嘗試使用 {fps} FPS 轉檔...")
        cmd = ['ffmpeg', '-i', input_path, '-vf', f'fps={fps}', '-y', output_path]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"FFmpeg 轉檔失敗 (FPS={fps}): {result.stderr}")
                continue
            
            if check_file_size(output_path, max_size_mb):
                logger.info(f"轉檔成功！使用 {fps} FPS")
                return True
            else:
                logger.warning(f"GIF 檔案超過 {max_size_mb}MB，嘗試降低 FPS...")
                if os.path.exists(output_path):
                    os.remove(output_path)
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg 轉檔超時 (FPS={fps})")
        except Exception as e:
            logger.error(f"FFmpeg 執行錯誤 (FPS={fps}): {e}")
    
    logger.error("所有 FPS 選項都無法產生符合大小限制的 GIF")
    return False


async def download_video(file, file_path: str) -> bool:
    """下載 Telegram 影片到指定路徑"""
    try:
        await file.download_to_drive(file_path)
        logger.info(f"影片下載成功: {file_path}")
        return True
    except Exception as e:
        logger.error(f"影片下載失敗: {e}")
        return False


async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理使用者傳送的影片訊息，將影片轉換為 GIF 並回傳"""
    input_path = None
    output_path = None
    
    try:
        user_id = update.effective_user.id
        await update.message.reply_text("📹 收到影片！正在處理中，請稍候...")
        
        if update.message.video:
            video_file = await update.message.video.get_file()
        elif update.message.document:
            video_file = await update.message.document.get_file()
        else:
            await update.message.reply_text("❌ 無法識別的影片格式")
            return
        
        input_filename = generate_unique_filename(user_id, "mp4")
        output_filename = generate_unique_filename(user_id, "gif")
        input_path = f"/tmp/{input_filename}"
        output_path = f"/tmp/{output_filename}"
        
        if not await download_video(video_file, input_path):
            await update.message.reply_text("❌ 影片下載失敗，請重試")
            return
        
        await update.message.reply_text("🔄 正在轉換為 GIF...")
        if not convert_to_gif_with_retry(input_path, output_path):
            await update.message.reply_text("❌ 轉檔失敗，請確認影片格式或嘗試較短的影片")
            return
        
        if not check_file_size(output_path, 20):
            await update.message.reply_text("❌ GIF 檔案超過 20MB 限制，請嘗試較短的影片")
            return
        
        await update.message.reply_text("✅ 轉換完成！正在傳送...")
        with open(output_path, 'rb') as gif_file:
            await update.message.reply_document(document=gif_file, filename=f"video_{user_id}.gif")
        
        logger.info(f"成功為使用者 {user_id} 完成影片轉 GIF")
    except Exception as e:
        logger.exception("處理影片時發生未知錯誤")
        await update.message.reply_text("❌ 發生未知錯誤，請稍後重試")
    finally:
        cleanup_files(input_path, output_path)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命週期管理：啟動時初始化 Bot，關閉時清理"""
    global ptb_application
    
    token = os.environ.get('TELEGRAM_TOKEN')
    webhook_url = os.environ.get('WEBHOOK_URL')  # 例如: https://jw9494-video-to-gif-bot.hf.space/webhook
    
    if not token:
        logger.error("未設定 TELEGRAM_TOKEN 環境變數")
        yield
        return
    
    # 建立 Application
    ptb_application = Application.builder().token(token).build()
    
    # 註冊 Handler
    video_handler = MessageHandler(
        filters.VIDEO | filters.Document.VIDEO,
        video_to_gif_handler
    )
    ptb_application.add_handler(video_handler)
    
    # 初始化並設定 Webhook
    await ptb_application.initialize()
    await ptb_application.start()
    
    if webhook_url:
        await ptb_application.bot.set_webhook(url=f"{webhook_url}/webhook")
        logger.info(f"Webhook 已設定: {webhook_url}/webhook")
    else:
        logger.warning("未設定 WEBHOOK_URL，請手動設定 Webhook")
    
    logger.info("Bot 啟動完成 (Webhook 模式)")
    
    yield
    
    # 關閉時清理
    await ptb_application.stop()
    await ptb_application.shutdown()
    logger.info("Bot 已關閉")


# 建立 FastAPI 應用
app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """健康檢查端點"""
    return {"status": "running", "message": "Video to GIF Bot is running"}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """處理 Telegram Webhook 請求"""
    global ptb_application
    
    if ptb_application is None:
        return Response(status_code=503, content="Bot not initialized")
    
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_application.bot)
        await ptb_application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.exception(f"Webhook 處理錯誤: {e}")
        return Response(status_code=500)
