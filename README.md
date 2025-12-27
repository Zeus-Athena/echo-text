# EchoText

<div align="center">

**🎙️ Real-time Voice Transcription & AI Enhancement Platform**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com/u/ttjade)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[English](#english)** | **[中文](#中文)**

</div>

---

<a name="english"></a>
## 🌍 English

A full-featured web-based voice processing platform with real-time transcription, translation, text-to-speech, and AI-powered text enhancement.

### ✨ Features

- 🎤 **Real-time Transcription** - Live speech-to-text with multiple STT providers
- 🌐 **Translation** - Real-time voice translation and text translation
- 🤖 **AI Enhancement** - Summarization, polishing, and content optimization with LLM
- 📝 **Recording Management** - Save, organize, and search your recordings
- 🔊 **Text-to-Speech** - Convert text back to natural speech
- 📖 **Dictionary Lookup** - Integrated word definitions and translations
- 🔗 **Share Links** - Generate shareable links for recordings
- 📤 **Export** - Export transcripts in multiple formats

### 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI + Python 3.11+ + PostgreSQL |
| **Frontend** | Vite + React 18 + TypeScript + TailwindCSS |
| **Containerization** | Docker + Docker Compose |

### 📚 Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](docs/deployment.md) | Production deployment, security checklist, Nginx config |
| [API Examples](docs/api-examples.md) | API usage examples with curl and JavaScript |
| [Architecture](docs/architecture.md) | System design, data flow, tech stack decisions |

### 🚀 Quick Start

#### Docker Compose Deployment (Recommended)

**1. Clone the repository**
```bash
git clone https://github.com/Zeus-Athena/echo-text.git
cd echo-text
```

**2. Create data directory**
```bash
mkdir -p data/postgres data/uploads
```

**3. Start services**
```bash
docker-compose up -d
```

**4. Access the application**
- 🌐 **Web App**: http://localhost:8080
- 📚 **API Docs**: http://localhost:8080/api/docs

**5. Default Admin Account**
- Username: `admin`
- Password: Randomly generated on first startup, check the backend logs:
  ```bash
  docker-compose logs backend | grep -A 5 "Admin User Created"
  ```

> ⚠️ **Important**: Save this password or change it immediately after first login!

#### Manual Development Setup

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### 📁 Project Structure

```
echo_text/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core configuration
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utilities
│   ├── scripts/          # Database scripts
│   └── Dockerfile
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── hooks/        # Custom hooks
│   │   ├── stores/       # State management
│   │   └── api/          # API client
│   └── Dockerfile
├── docker-compose.yml    # Docker orchestration
└── README.md
```

### ⚙️ Configuration

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |

#### Docker Compose Customization

Edit `docker-compose.yml` to customize:
- Port mappings (default: 8080)
- Database credentials
- Volume mounts

### 🔧 Reverse Proxy (Nginx)

If running behind Nginx, add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

<a name="中文"></a>
## 🇨🇳 中文

基于 Web 的全功能语音处理平台，提供实时转录、翻译、语音合成和 AI 文本增强功能。

### ✨ 功能特性

- 🎤 **实时转录** - 支持多种 STT 服务商的实时语音转文字
- 🌐 **翻译功能** - 实时语音翻译和文本翻译
- 🤖 **AI 增强** - 使用大语言模型进行摘要、润色和内容优化
- 📝 **录音管理** - 保存、整理和搜索您的录音
- 🔊 **语音合成** - 将文本转换为自然语音
- 📖 **词典查询** - 集成单词定义和翻译
- 🔗 **分享链接** - 生成录音的分享链接
- 📤 **导出功能** - 支持多种格式导出转录文本

### 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI + Python 3.11+ + PostgreSQL |
| **前端** | Vite + React 18 + TypeScript + TailwindCSS |
| **容器化** | Docker + Docker Compose |

### 🚀 快速开始

#### Docker Compose 部署（推荐）

**1. 克隆仓库**
```bash
git clone https://github.com/Zeus-Athena/echo-text.git
cd echo-text
```

**2. 创建数据目录**
```bash
mkdir -p data/postgres data/uploads
```

**3. 启动服务**
```bash
docker-compose up -d
```

**4. 访问应用**
- 🌐 **Web 应用**: http://localhost:8080
- 📚 **API 文档**: http://localhost:8080/api/docs

**5. 默认管理员账号**
- 用户名：`admin`
- 密码：首次启动时随机生成，请查看后端日志获取：
  ```bash
  docker-compose logs backend | grep -A 5 "Admin User Created"
  ```

> ⚠️ **重要提示**：请保存此密码或在首次登录后立即修改！

#### 手动开发环境搭建

**后端**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件配置

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**
```bash
cd frontend
npm install
npm run dev
```

### 📁 项目结构

```
echo_text/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 核心配置
│   │   ├── models/       # 数据库模型
│   │   ├── schemas/      # Pydantic 模式
│   │   ├── services/     # 业务逻辑
│   │   └── utils/        # 工具函数
│   ├── scripts/          # 数据库脚本
│   └── Dockerfile
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # React 组件
│   │   ├── pages/        # 页面组件
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── stores/       # 状态管理
│   │   └── api/          # API 客户端
│   └── Dockerfile
├── docker-compose.yml    # Docker 编排
└── README.md
```

### ⚙️ 配置说明

#### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | 必填 |
| `SECRET_KEY` | JWT 密钥 | 必填 |
| `CORS_ORIGINS` | 允许的 CORS 来源 | `["*"]` |

#### Docker Compose 自定义配置

编辑 `docker-compose.yml` 可自定义：
- 端口映射（默认：8080）
- 数据库凭据
- 卷挂载路径

### 🔧 反向代理配置（Nginx）

如果在 Nginx 后运行，添加以下配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

<div align="center">

**Made with ❤️ by [Zeus-Athena](https://github.com/Zeus-Athena)**

</div>
