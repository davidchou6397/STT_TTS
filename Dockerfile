FROM python:3.10-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 預先下載 tiny 模型（最小，約 75MB，省記憶體）
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

# 複製應用程式
COPY server.py .
COPY client.html .

# 設定環境變數
ENV PORT=3597
ENV WHISPER_MODEL=tiny
ENV WHISPER_DEVICE=cpu
ENV WHISPER_COMPUTE=int8
ENV WHISPER_LANG=nan

EXPOSE 3597

CMD ["python", "server.py"]
