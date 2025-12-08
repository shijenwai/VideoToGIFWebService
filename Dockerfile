FROM python:3.10-slim

# Python 編譯優化：減少啟動時間與記憶體使用
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝 FFmpeg，並清理暫存以縮減映像檔體積
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Cloud Run 使用 PORT 環境變數，Render 預設 10000
EXPOSE 8080 10000

CMD ["python", "app.py"]