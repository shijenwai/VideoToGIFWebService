FROM python:3.10-slim

# 安裝 FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY app.py .

# 暴露 Hugging Face Spaces 預設端口
EXPOSE 7860

# 使用 uvicorn 啟動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
