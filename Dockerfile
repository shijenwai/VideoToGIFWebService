FROM python:3.10

# 安裝 FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Render 會自動偵測並注入 PORT 環境變數，這裡不用 EXPOSE 也可以，但寫了更清楚
EXPOSE 10000

CMD ["python", "app.py"]