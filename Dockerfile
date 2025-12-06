# --- 關鍵修正：改用完整版 (移除 -slim) ---
# 完整版包含完整的 Debian 網路工具與 DNS 解析庫
FROM python:3.10

# 安裝 FFmpeg (Debian 基礎映像檔使用 apt-get)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY requirements.txt .
COPY packages.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY app.py .

# 暴露端口 (給 HF 健康檢查用)
EXPOSE 7860

# 啟動命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]