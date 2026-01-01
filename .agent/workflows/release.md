---
description: 标准发布流程 (Develop改版本 -> 合并Main -> 打标签 -> 推送)
---

# 标准发布流程 (Standard Release Workflow)

采用 **“Develop 驱动发布”** 模式：先在开发分支完成版本更新，最后合并到主分支发布。

## 1. 准备发布 (Prepare in Develop)
在 `develop` 分支上更新版本号：

- [ ] **切换分支**:
    ```bash
    git checkout develop
    git pull origin develop
    ```
- [ ] **更新版本号 files**:
    - `backend/pyproject.toml`
    - `backend/app/__version__.py`
    - `frontend/package.json`
    *(修改为目标版本 `TARGET_VERSION`)*
- [ ] **提交变更**:
    ```bash
    git add backend/pyproject.toml backend/app/__version__.py frontend/package.json
    git commit -m "chore: bump version to vTARGET_VERSION"
    ```

## 1.5 配置文件检查 (Configuration Verification)
确保生产环境所需的配置文件完整且正确：

- [ ] **检查后端配置**:
    - `backend/.env.example` 中所有必需字段都有对应的生产值
    - 确认 `backend/app/core/config.py` 中无硬编码的开发环境值
- [ ] **检查前端配置**:
    - `frontend/.env.example` 中 API 地址等配置正确
- [ ] **检查 Docker 配置**:
    - `docker-compose.yml` 或 `docker-compose.prod.yml` 环境变量完整
    - 镜像版本号是否需要更新
- [ ] **检查数据库迁移**:
    ```bash
    cd backend
    alembic history --verbose | head -20
    alembic heads
    ```
    确认是否有未应用的迁移或分叉的 migration heads

## 2. 代码验证 (Verification)
- [ ] **Backend 测试**:
    ```bash
    cd backend
    # 使用虚拟环境运行 (确保依赖环境正确)
    ./venv/bin/python -m ruff check .
    ./venv/bin/python -m ruff format --check .
    PYTHONPATH=. ./venv/bin/python -m pytest
    ```
- [ ] **Frontend Lint**:
    ```bash
    cd frontend
    npm run lint
    ```
- [ ] **修复问题 (If Failed)**:
    - 如果上述命令报错，**必须**先修复代码或测试。
    - 修复后再次运行测试，直到全部通过。

## 3. 合并与发布 (Merge & Release)
将准备好的 `develop` 合并到 `main`：

- [ ] **合并代码**:
    ```bash
    git checkout main
    git pull origin main
    git merge develop
    ```
- [ ] **打标签**:
    ```bash
    git tag -a vTARGET_VERSION -m "Release vTARGET_VERSION"
    ```

## 4. 推送 (Push)
同时推送两个分支和标签：

- [ ] **提交推送**:
    ```bash
    git push origin main
    git push origin vTARGET_VERSION
    git push origin develop
    ```
    *(推送 develop 是为了保存刚才的版本号更新 commit)*

## 5. 结束 (Completion)
- [ ] 通知用户发布已完成。
