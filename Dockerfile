# 使用完整版 Python (避免缺件)
FROM python:3.10

# 安裝 FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 複製依賴
COPY requirements.txt .
# Render 不一定需要 packages.txt，但留著無妨，主要是 requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY app.py .

# 直接執行 Python
CMD ["python", "app.py"]