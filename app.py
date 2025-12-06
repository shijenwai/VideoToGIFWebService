import os
import logging
import time
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def generate_unique_filename(user_id: int, extension: str) -> str:
    """
    生成唯一檔名以避免多使用者同時使用時的檔案衝突
    
    Args:
        user_id: Telegram 使用者 ID
        extension: 檔案副檔名 (例如 'mp4', 'gif')
    
    Returns:
        唯一檔名字串
    """
    timestamp = int(time.time() * 1000000)  # 微秒級時間戳
    return f"user_{user_id}_{timestamp}.{extension}"


def cleanup_files(*file_paths: str) -> None:
    """
    清理暫存檔案，確保不因檔案不存在而拋錯
    
    Args:
        *file_paths: 要刪除的檔案路徑列表
    """
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已刪除暫存檔: {file_path}")
            except Exception as e:
                logger.error(f"刪除檔案失敗 {file_path}: {e}")


def check_file_size(file_path: str, max_mb: int = 20) -> bool:
    """
    檢查檔案大小是否超過限制
    
    Args:
        file_path: 檔案路徑
        max_mb: 最大檔案大小 (MB)
    
    Returns:
        True 表示檔案大小符合限制，False 表示超過限制
    """
    if not os.path.exists(file_path):
        return False
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    logger.info(f"檔案大小: {file_size_mb:.2f} MB")
    return file_size_mb <= max_mb


def convert_to_gif_with_retry(input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
    """
    使用漸進式 FPS 策略將影片轉換為 GIF
    優先使用高 FPS 保持畫質，若檔案過大則降低 FPS 重試
    
    Args:
        input_path: 輸入影片路徑
        output_path: 輸出 GIF 路徑
        max_size_mb: 最大檔案大小限制 (MB)
    
    Returns:
        True 表示轉檔成功，False 表示失敗
    """
    fps_options = [20, 15, 10]  # 漸進式 FPS 選項
    
    for fps in fps_options:
        logger.info(f"嘗試使用 {fps} FPS 轉檔...")
        
        # 建構 FFmpeg 命令
        # -i: 輸入檔案
        # -vf: 視訊濾鏡，fps 設定幀率
        # -y: 覆蓋輸出檔案
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f'fps={fps}',
            '-y',
            output_path
        ]
        
        try:
            # 執行 FFmpeg 轉檔
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 分鐘超時
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg 轉檔失敗 (FPS={fps}): {result.stderr}")
                continue
            
            # 檢查檔案大小
            if check_file_size(output_path, max_size_mb):
                logger.info(f"轉檔成功！使用 {fps} FPS")
                return True
            else:
                logger.warning(f"GIF 檔案超過 {max_size_mb}MB，嘗試降低 FPS...")
                # 刪除過大的檔案，準備重試
                if os.path.exists(output_path):
                    os.remove(output_path)
        
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg 轉檔超時 (FPS={fps})")
            continue
        except Exception as e:
            logger.error(f"FFmpeg 執行錯誤 (FPS={fps}): {e}")
            continue
    
    # 所有 FPS 選項都失敗
    logger.error("所有 FPS 選項都無法產生符合大小限制的 GIF")
    return False


async def download_video(file, file_path: str) -> bool:
    """
    下載 Telegram 影片到指定路徑
    
    Args:
        file: Telegram File 物件
        file_path: 目標檔案路徑
    
    Returns:
        True 表示下載成功，False 表示失敗
    """
    try:
        await file.download_to_drive(file_path)
        logger.info(f"影片下載成功: {file_path}")
        return True
    except Exception as e:
        logger.error(f"影片下載失敗: {e}")
        return False


async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    處理使用者傳送的影片訊息，將影片轉換為 GIF 並回傳
    """
    input_path = None
    output_path = None
    
    try:
        # 取得使用者資訊
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # 回覆確認訊息
        await update.message.reply_text("📹 收到影片！正在處理中，請稍候...")
        
        # 取得影片檔案
        if update.message.video:
            video_file = await update.message.video.get_file()
        elif update.message.document:
            video_file = await update.message.document.get_file()
        else:
            await update.message.reply_text("❌ 無法識別的影片格式")
            return
        
        # 生成唯一檔名
        input_filename = generate_unique_filename(user_id, "mp4")
        output_filename = generate_unique_filename(user_id, "gif")
        
        input_path = f"/tmp/{input_filename}"
        output_path = f"/tmp/{output_filename}"
        
        # 下載影片
        if not await download_video(video_file, input_path):
            await update.message.reply_text("❌ 影片下載失敗，請重試")
            return
        
        # 轉檔為 GIF
        await update.message.reply_text("🔄 正在轉換為 GIF...")
        if not convert_to_gif_with_retry(input_path, output_path):
            await update.message.reply_text("❌ 轉檔失敗，請確認影片格式或嘗試較短的影片")
            return
        
        # 檢查最終檔案大小
        if not check_file_size(output_path, 20):
            await update.message.reply_text("❌ GIF 檔案超過 20MB 限制，請嘗試較短的影片")
            return
        
        # 回傳 GIF
        await update.message.reply_text("✅ 轉換完成！正在傳送...")
        with open(output_path, 'rb') as gif_file:
            await update.message.reply_document(
                document=gif_file,
                filename=f"video_{user_id}.gif"
            )
        
        logger.info(f"成功為使用者 {user_id} 完成影片轉 GIF")
        
    except Exception as e:
        logger.exception("處理影片時發生未知錯誤")
        await update.message.reply_text("❌ 發生未知錯誤，請稍後重試")
    
    finally:
        # 確保清理暫存檔
        cleanup_files(input_path, output_path)


def main() -> None:
    """
    初始化並啟動 Telegram Bot
    使用同步方式啟動，避免 event loop 衝突
    """
    # 從環境變數讀取 Token
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        logger.error("未設定 TELEGRAM_TOKEN 環境變數")
        return
    
    # 建立 Application
    application = Application.builder().token(token).build()
    
    # 註冊 Handler：處理影片訊息和影片檔案
    video_handler = MessageHandler(
        filters.VIDEO | filters.Document.VIDEO,
        video_to_gif_handler
    )
    application.add_handler(video_handler)
    
    logger.info("Bot 啟動中...")
    
    # 使用同步方式啟動 Polling（內部會自己管理 event loop）
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
