# API 使用示例

本文档提供 EchoText API 的常见使用场景和示例代码。

## 🔑 认证

所有 API 请求（除公开分享链接外）都需要 Bearer Token。

### 登录获取 Token

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=YOUR_PASSWORD_FROM_LOGS"
```

响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 使用 Token

```bash
# 设置环境变量方便后续使用
export TOKEN="your-access-token-here"

# 请求示例
curl http://localhost:8080/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎤 录音管理

### 上传录音

```bash
curl -X POST http://localhost:8080/api/v1/recordings \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@recording.webm" \
  -F "title=我的录音" \
  -F "source_language=zh"
```

响应：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "我的录音",
  "status": "uploaded",
  "duration": 120.5,
  "created_at": "2025-12-25T10:00:00Z"
}
```

### 处理录音（转录）

```bash
curl -X POST http://localhost:8080/api/v1/recordings/{recording_id}/process \
  -H "Authorization: Bearer $TOKEN"
```

### 获取录音列表

```bash
# 获取所有录音
curl http://localhost:8080/api/v1/recordings \
  -H "Authorization: Bearer $TOKEN"

# 获取特定文件夹的录音
curl "http://localhost:8080/api/v1/recordings?folder_id={folder_id}" \
  -H "Authorization: Bearer $TOKEN"

# 搜索录音
curl "http://localhost:8080/api/v1/recordings?search=会议" \
  -H "Authorization: Bearer $TOKEN"
```

### 获取转录结果

```bash
curl http://localhost:8080/api/v1/recordings/{recording_id}/transcript \
  -H "Authorization: Bearer $TOKEN"
```

响应：

```json
{
  "id": "...",
  "recording_id": "...",
  "content": "这是转录的文本内容...",
  "language": "zh",
  "stt_model": "whisper-large-v3-turbo"
}
```

---

## 🌐 实时转录 WebSocket

### 连接

```javascript
const ws = new WebSocket('wss://your-domain.com/api/v1/ws/transcribe');

ws.onopen = () => {
  // 发送配置
  ws.send(JSON.stringify({
    type: 'config',
    token: 'your-access-token',
    source_language: 'zh',
    target_language: 'en',  // 可选：翻译目标语言
    buffer_duration: 6      // 缓冲时长（秒）
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'transcription':
      console.log('转录:', data.text);
      break;
    case 'translation':
      console.log('翻译:', data.text);
      break;
    case 'error':
      console.error('错误:', data.message);
      break;
  }
};

// 发送音频数据（WebM/Opus 格式）
mediaRecorder.ondataavailable = (e) => {
  if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
    ws.send(e.data);
  }
};
```

### 心跳保活

```javascript
// 每 30 秒发送心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

---

## 🤖 AI 增强

### 文本翻译

```bash
curl -X POST http://localhost:8080/api/v1/translate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "source_language": "en",
    "target_language": "zh"
  }'
```

### AI 摘要

```bash
curl -X POST http://localhost:8080/api/v1/recordings/{recording_id}/summarize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_type": "summary"
  }'
```

### AI 润色

```bash
curl -X POST http://localhost:8080/api/v1/llm/polish \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这是需要润色的原文...",
    "style": "formal"
  }'
```

---

## 🔊 语音合成 (TTS)

```bash
curl -X POST http://localhost:8080/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，这是语音合成测试",
    "voice": "zh-CN-XiaoxiaoNeural"
  }' \
  --output speech.mp3
```

---

## 🔗 分享链接

### 创建分享链接

```bash
curl -X POST http://localhost:8080/api/v1/recordings/{recording_id}/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "expires_in_days": 7,
    "allow_download": true
  }'
```

响应：

```json
{
  "share_url": "https://your-domain.com/share/abc123",
  "expires_at": "2026-01-01T00:00:00Z"
}
```

### 访问分享内容（无需认证）

```bash
curl http://localhost:8080/api/v1/share/{share_code}
```

---

## 📤 导出

### 导出转录文本

```bash
# 导出为 TXT
curl http://localhost:8080/api/v1/recordings/{recording_id}/export?format=txt \
  -H "Authorization: Bearer $TOKEN" \
  --output transcript.txt

# 导出为 SRT 字幕
curl http://localhost:8080/api/v1/recordings/{recording_id}/export?format=srt \
  -H "Authorization: Bearer $TOKEN" \
  --output subtitles.srt

# 导出为 JSON
curl http://localhost:8080/api/v1/recordings/{recording_id}/export?format=json \
  -H "Authorization: Bearer $TOKEN" \
  --output transcript.json
```

---

## ⚙️ 用户 API 配置

### 设置 AI Provider API Key

```bash
curl -X PUT http://localhost:8080/api/v1/users/me/api-config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stt_provider": "Groq",
    "stt_api_key": "gsk_xxx",
    "llm_provider": "SiliconFlow",
    "llm_api_key": "sk-xxx"
  }'
```

---

## 📖 完整 API 文档

访问 Swagger UI 查看完整 API 文档：

- **开发环境**: http://localhost:8000/docs
- **生产环境**: https://your-domain.com/api/docs
