---
description: 开发环境测试流程 (测试、检测、构建、启动)
---

# 开发环境测试流程

本流程适用于本地开发时的完整验证，包括运行测试、代码检测、构建 Docker 镜像并启动服务。

---

## 1. 后端测试与检测

// turbo
// turbo
```bash
cd backend && venv/bin/python -m pytest
```

// turbo
```bash
cd backend && venv/bin/python -m ruff check app --fix
```

// turbo
```bash
cd backend && venv/bin/python -m ruff format app
```

---

## 2. 前端测试与检测

// turbo
```bash
cd frontend && npm run test
```

// turbo
```bash
cd frontend && npm run lint
```

---

## 3. 构建 Docker 镜像

```bash
docker-compose -f docker-compose.develop.yml build
```

构建的镜像:
- `echo-text-backend:local` (后端)
- `echo-text-frontend:local` (前端)

---

## 4. 启动服务

```bash
docker-compose -f docker-compose.develop.yml up -d
```

启动后的服务:
| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 后端 (代码热更新) |
| frontend | 8080 | React 前端 |
| db | - | PostgreSQL 15 |
| redis | - | Redis 7 |
| arq-worker | - | 后台任务处理 |

---

## 5. 查看日志 (可选)

// turbo
```bash
docker-compose -f docker-compose.develop.yml logs -f backend
```

---

## 6. 停止服务 (可选)

```bash
docker-compose -f docker-compose.develop.yml down
```

---

## 快速命令汇总

```bash
# 一键测试 + 检测 (后端)
cd backend && venv/bin/python -m pytest && venv/bin/python -m ruff check app --fix && venv/bin/python -m ruff format app

# 一键测试 + 检测 (前端)
cd frontend && npm run test && npm run lint

# 构建并启动
docker-compose -f docker-compose.develop.yml build && docker-compose -f docker-compose.develop.yml up -d
```
