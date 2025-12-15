"""
台語即時語音辨識 WebSocket 伺服器 (GCP Cloud Run 版)
使用 Faster-Whisper small 模型 + CPU

部署：
1. gcloud run deploy whisper-asr --source . --region asia-east1 --allow-unauthenticated

本地測試：
python server.py
"""

import asyncio
import json
import numpy as np
import os
from typing import Optional
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ===== 配置 (CPU 優化版) =====
CONFIG = {
    "model_size": os.getenv("WHISPER_MODEL", "small"),      # small 適合 CPU
    "device": os.getenv("WHISPER_DEVICE", "cpu"),           # CPU 模式
    "compute_type": os.getenv("WHISPER_COMPUTE", "int8"),   # int8 量化加速
    "language": os.getenv("WHISPER_LANG", "nan"),           # nan=台語
    "sample_rate": 16000,
    "chunk_duration": 5,            # CPU 較慢，5秒處理一次
    "overlap_duration": 1,
}

# ===== Whisper 模型 =====
print(f"🔄 載入 Whisper 模型: {CONFIG['model_size']} ({CONFIG['device']})...")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel(
        CONFIG["model_size"],
        device=CONFIG["device"],
        compute_type=CONFIG["compute_type"]
    )
    print(f"✅ 模型載入完成")
except Exception as e:
    print(f"❌ 模型載入失敗: {e}")
    model = None

# ===== FastAPI App =====
app = FastAPI(title="台語即時 ASR (GCP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 音頻緩衝處理器 =====
class AudioProcessor:
    def __init__(self, sample_rate=16000, chunk_sec=5, overlap_sec=1):
        self.sample_rate = sample_rate
        self.chunk_samples = chunk_sec * sample_rate
        self.overlap_samples = overlap_sec * sample_rate
        self.buffer = deque(maxlen=sample_rate * 30)
        
    def add_audio(self, audio_data: bytes) -> Optional[np.ndarray]:
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        self.buffer.extend(audio_array)
        
        if len(self.buffer) >= self.chunk_samples:
            chunk = np.array(list(self.buffer)[:self.chunk_samples])
            for _ in range(self.chunk_samples - self.overlap_samples):
                if self.buffer:
                    self.buffer.popleft()
            return chunk
        return None
    
    def clear(self):
        self.buffer.clear()

# ===== WebSocket 連線管理 =====
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.processors: dict[str, AudioProcessor] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.processors[client_id] = AudioProcessor(
            sample_rate=CONFIG["sample_rate"],
            chunk_sec=CONFIG["chunk_duration"],
            overlap_sec=CONFIG["overlap_duration"]
        )
        print(f"🔗 客戶端連接: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.processors:
            del self.processors[client_id]
        print(f"🔌 客戶端斷開: {client_id}")
    
    async def send_text(self, client_id: str, message: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

# ===== Whisper 辨識函數 =====
def transcribe_audio(audio: np.ndarray, language: str = "nan") -> dict:
    if model is None:
        return {"error": "模型未載入"}
    
    try:
        segments, info = model.transcribe(
            audio,
            language=language,
            beam_size=3,              # 減少 beam size 加速
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            )
        )
        
        text = ""
        for segment in segments:
            text += segment.text
        
        return {
            "text": text.strip(),
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2)
        }
    except Exception as e:
        return {"error": str(e)}

# ===== API Routes =====
@app.get("/")
async def root():
    return FileResponse("client.html")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "config": CONFIG
    }

@app.get("/config")
async def get_config():
    return CONFIG

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    await manager.send_text(client_id, json.dumps({
        "type": "connected",
        "message": "連接成功",
        "config": CONFIG
    }))
    
    try:
        while True:
            data = await websocket.receive()
            
            if "bytes" in data:
                audio_bytes = data["bytes"]
                processor = manager.processors.get(client_id)
                
                if processor:
                    chunk = processor.add_audio(audio_bytes)
                    
                    if chunk is not None:
                        await manager.send_text(client_id, json.dumps({
                            "type": "processing",
                            "message": "辨識中..."
                        }))
                        
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            transcribe_audio,
                            chunk,
                            CONFIG["language"]
                        )
                        
                        await manager.send_text(client_id, json.dumps({
                            "type": "transcript",
                            **result
                        }))
            
            elif "text" in data:
                message = json.loads(data["text"])
                
                if message.get("type") == "config":
                    new_lang = message.get("language")
                    if new_lang:
                        CONFIG["language"] = new_lang
                        await manager.send_text(client_id, json.dumps({
                            "type": "config_updated",
                            "language": new_lang
                        }))
                
                elif message.get("type") == "clear":
                    processor = manager.processors.get(client_id)
                    if processor:
                        processor.clear()
                    await manager.send_text(client_id, json.dumps({
                        "type": "cleared"
                    }))
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"❌ WebSocket 錯誤: {e}")
        manager.disconnect(client_id)

# ===== 主程式 =====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3597))
    
    print("\n" + "="*50)
    print("🎤 台語即時語音辨識伺服器 (CPU 版)")
    print("="*50)
    print(f"📌 模型: {CONFIG['model_size']}")
    print(f"📌 語言: {CONFIG['language']}")
    print(f"📌 裝置: {CONFIG['device']} ({CONFIG['compute_type']})")
    print(f"📌 處理間隔: 每 {CONFIG['chunk_duration']} 秒")
    print(f"📌 Port: {port}")
    print("="*50)
    print(f"🌐 開啟瀏覽器訪問: http://localhost:{port}")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
