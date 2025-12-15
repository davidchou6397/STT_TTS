# 台語即時語音辨識 - Railway / Render 部署

Port: 3597 | 模型: small | CPU + int8

---

## 方案 A：Railway 部署（推薦 ⭐）

### 步驟 1：註冊 Railway

1. 開啟 https://railway.app
2. 用 **GitHub 帳號**登入（最方便）
3. 免費額度：$5/月

### 步驟 2：上傳到 GitHub

先把這個資料夾推到你的 GitHub：

```bash
# 在 deploy-whisper 目錄
git init
git add .
git commit -m "whisper asr"
git branch -M main
git remote add origin https://github.com/你的帳號/whisper-asr.git
git push -u origin main
```

### 步驟 3：Railway 部署

**方法 A：網頁部署（最簡單）**

1. 登入 https://railway.app/dashboard
2. 點 **New Project** → **Deploy from GitHub repo**
3. 選擇你的 `whisper-asr` repo
4. Railway 會自動偵測 Dockerfile 並部署
5. 點 **Settings** → **Networking** → **Generate Domain**
6. 得到網址如：`whisper-asr-production.up.railway.app`

**方法 B：CLI 部署**

```bash
# 安裝 Railway CLI
npm install -g @railway/cli

# 登入
railway login

# 在 deploy-whisper 目錄
railway init
railway up

# 設定 Port（重要！）
railway variables set PORT=3597

# 產生網址
railway domain
```

### 步驟 4：更新前端 URL

部署成功後，修改 `client.html` 裡的 WebSocket URL：

```javascript
// 找到這行
value="ws://localhost:3597/ws/"

// 改成（Railway 給的網址）
value="wss://whisper-asr-production.up.railway.app/ws/"
```

然後重新 push 更新：
```bash
git add client.html
git commit -m "update websocket url"
git push
```

Railway 會自動重新部署。

---

## 方案 B：Render 部署

### 步驟 1：註冊 Render

1. 開啟 https://render.com
2. 用 **GitHub 帳號**登入
3. 免費方案有限制，建議用 **Starter ($7/月)**

### 步驟 2：上傳到 GitHub

（同 Railway 步驟 2）

### 步驟 3：Render 部署

1. 登入 https://dashboard.render.com
2. 點 **New** → **Web Service**
3. 連接你的 GitHub repo
4. 設定：
   - **Name**: whisper-asr
   - **Region**: Singapore（離台灣近）
   - **Branch**: main
   - **Runtime**: Docker
   - **Instance Type**: Standard ($25/月) 或 Starter ($7/月)
5. **Environment Variables** 加入：
   ```
   PORT=3597
   WHISPER_MODEL=small
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE=int8
   WHISPER_LANG=nan
   ```
6. 點 **Create Web Service**

### 步驟 4：取得網址

部署完成後得到：
```
https://whisper-asr.onrender.com
```

WebSocket URL 改為：
```
wss://whisper-asr.onrender.com/ws/
```

---

## 方案 C：Hugging Face Spaces（免費）

最簡單的免費方案，但效能有限。

### 步驟 1：創建 Space

1. 登入 https://huggingface.co
2. 點右上角 **New** → **Space**
3. 設定：
   - **Name**: taiwanese-asr
   - **SDK**: Docker
   - **Hardware**: CPU basic (免費)
4. 上傳所有檔案

### 步驟 2：得到網址

```
https://你的帳號-taiwanese-asr.hf.space
```

---

## 部署後測試

1. 開啟你的網址（如 `https://whisper-asr-production.up.railway.app`）
2. 點「連接伺服器」
3. 點麥克風開始錄音
4. 說台語，等待 5-8 秒會顯示辨識結果

---

## 費用比較

| 平台 | 免費額度 | 付費方案 | 建議 |
|------|----------|----------|------|
| **Railway** | $5/月 | $0.000463/秒 | ⭐ 推薦 |
| **Render** | 有限制 | $7-25/月 | 穩定 |
| **HF Spaces** | 免費 CPU | $0 | Demo 用 |
| **Fly.io** | 免費額度 | 用量計費 | 進階 |

---

## 常見問題

### Q: 部署很久？

首次部署需要：
1. 下載 Docker 映像
2. 安裝依賴
3. **下載 Whisper 模型（約 500MB）**

通常 5-10 分鐘完成。

### Q: WebSocket 連不上？

1. 確認用 `wss://` 不是 `ws://`
2. 確認網址結尾有 `/ws/`
3. 檢查瀏覽器 Console 錯誤訊息

### Q: 辨識結果是空的？

1. 確認麥克風權限已開啟
2. 說話聲音要夠大
3. CPU 模式需等待 5-8 秒

### Q: Railway 免費額度用完？

1. 綁定信用卡可獲得更多額度
2. 或暫停服務，下個月重置

---

## 本地測試

部署前先本地測試：

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動
python server.py

# 開啟瀏覽器
# http://localhost:3597
```

---

## 檔案清單

```
deploy-whisper/
├── server.py          # 後端伺服器
├── client.html        # 前端介面
├── Dockerfile         # Docker 配置
├── requirements.txt   # Python 依賴
├── railway.toml       # Railway 配置
├── render.yaml        # Render 配置
└── README.md          # 本說明檔
```
