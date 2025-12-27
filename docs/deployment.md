# 生产部署指南

本文档说明如何将 EchoText 安全地部署到生产环境。

## 🔐 安全配置检查清单

> [!CAUTION]
> 部署前必须完成以下所有安全配置项！

| 项目 | 状态 | 说明 |
|------|------|------|
| `SECRET_KEY` | ⬜ | 必须更换，使用 `openssl rand -hex 32` 生成 |
| 管理员密码 | ⬜ | 首次启动时随机生成，从日志中获取后建议立即修改 |
| `CORS_ORIGINS` | ⬜ | 设置为实际域名，禁止 `["*"]` |
| HTTPS | ⬜ | 必须启用 SSL/TLS 加密 |
| 数据库密码 | ⬜ | 更换默认的 `echotext_password` |

---

## 📦 环境变量配置

### 必需变量

```bash
# 生产环境标识
ENVIRONMENT=production
LOG_LEVEL=INFO

# 数据库连接（使用强密码）
DATABASE_URL=postgresql+asyncpg://echotext:YOUR_STRONG_PASSWORD@db:5432/echotext

# JWT 密钥（32+ 字节随机字符串）
SECRET_KEY=your-generated-secret-key-here

# CORS 配置（替换为实际域名）
CORS_ORIGINS=["https://your-domain.com"]

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### 生成安全密钥

```bash
# 生成 SECRET_KEY
openssl rand -hex 32

# 生成数据库密码
openssl rand -base64 24
```

---

## 🐳 Docker Compose 部署

### 1. 创建数据目录

```bash
mkdir -p data/postgres data/uploads
chmod 755 data/postgres data/uploads
```

### 2. 修改 docker-compose.yml

```yaml
services:
  db:
    environment:
      POSTGRES_PASSWORD: YOUR_STRONG_DB_PASSWORD  # 修改这里
  
  backend:
    environment:
      - DATABASE_URL=postgresql+asyncpg://echotext:YOUR_STRONG_DB_PASSWORD@db:5432/echotext
      - SECRET_KEY=your-generated-secret-key-here  # 修改这里
      - CORS_ORIGINS=["https://your-domain.com"]   # 修改这里
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 验证部署

```bash
# 检查健康状态
curl http://localhost:8080/health

# 期望响应：
# {"status":"healthy","version":"1.1.1","checks":{"postgresql":"ok","redis":"ok"}}
```

---

## 🔒 Nginx + HTTPS 配置

### 安装 Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d your-domain.com
```

### Nginx 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        
        # WebSocket 支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 超时（重要：实时转录需要长连接）
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 💾 数据持久化

### 数据目录说明

| 目录 | 用途 | 备份重要性 |
|------|------|------------|
| `data/postgres/` | PostgreSQL 数据 | 🔴 高 |
| `data/uploads/` | 用户上传的音频文件 | 🟡 中 |

### 定期备份

```bash
#!/bin/bash
# backup.sh - 数据库备份脚本

BACKUP_DIR=/path/to/backups
DATE=$(date +%Y%m%d_%H%M%S)

# 备份 PostgreSQL
docker exec echotext-db pg_dump -U echotext echotext > $BACKUP_DIR/db_$DATE.sql

# 压缩
gzip $BACKUP_DIR/db_$DATE.sql

# 保留最近 7 天
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

添加 cron 任务：

```bash
# 每天凌晨 2 点备份
0 2 * * * /path/to/backup.sh
```

---

## 📊 监控建议

### 健康检查

```bash
# 添加到监控系统（如 Uptime Kuma）
curl -f http://localhost:8080/health || exit 1
```

### 日志查看

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看 ARQ Worker 日志
docker-compose logs -f arq-worker
```

---

## ⬆️ 更新升级

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务（保留数据）
docker-compose up -d

# 检查状态
docker-compose ps
```

---

## 🆘 常见问题

### Q: 502 Bad Gateway

检查后端服务是否启动：

```bash
docker-compose logs backend
```

常见原因：
- 数据库连接失败
- SECRET_KEY 未配置

### Q: WebSocket 连接断开

检查 Nginx 超时配置，确保 `proxy_read_timeout` 足够长（推荐 3600s）。

### Q: 音频处理失败

检查 FFmpeg 是否可用：

```bash
docker exec echotext-backend ffmpeg -version
```
