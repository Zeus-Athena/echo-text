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

## 2. 代码验证 (Verification)
- [ ] **运行测试**:
    ```bash
    cd backend
    # 使用虚拟环境运行 (确保依赖环境正确)
    ./venv/bin/python -m ruff check .
    ./venv/bin/python -m ruff format --check .
    PYTHONPATH=. ./venv/bin/python -m pytest
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
