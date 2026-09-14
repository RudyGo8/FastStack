<div align="center">
     <p align="center">
          <img src="./frontend/web/public/logo.png" width="150" height="150" alt="logo" />
     </p>
     <h1>FastStack</h1>
     <p>个人全栈脚手架：FastAPI + Vue3 + TypeScript + MySQL + Redis + Milvus</p>
     <p>基于开源项目 <a href="https://github.com/fastapiadmin/FastapiAdmin">FastapiAdmin</a> 精简而来，MIT 协议</p>
</div>

## 🚀 快速开始

```bash
# 方式一：一键启动（基础设施 + 后端 + 前端）
./run.sh

# 方式二：手动
docker compose up -d                                        # MySQL:3307 / Redis:6380 / Milvus:19531 / Attu:8082
cd backend && uv sync && uv run main.py run --env=dev      # 首次自动建表 + 初始化数据，端口 8001
cd ../frontend/web && pnpm install && pnpm run dev          # 端口 5173
```

默认账号：`super` / `admin` / `user`，密码均为 `123456`（部署后立即修改）。

开发配置（`backend/env/.env.dev`、`frontend/web/.env.development`）首次由 `run.sh` 自动生成：
数据库 `3307/123456`、Redis `6380` 无密码、`SECRET_KEY` 随机。

| 环境要求 | |
|---------|------|
| Python ≥ 3.12 + uv | Node.js ≥ 20 + pnpm |
| Docker（compose.yaml 起基础设施） | |

## 🧬 衍生新项目

```bash
./init-project.sh my-project   # 复制到 ../my-project：改容器名前缀/库名/标题，git init，随机 SECRET_KEY
```

## 📦 工程结构

```
FastStack/
├─ backend/              # FastAPI 后端（modules/system|generator|monitor|task|ai，Alembic，代码生成器）
├─ frontend/
│   ├── web/             # Vue3 Web 前端（Element Plus + TypeScript + Tailwind4）
│   └── app/             # UniApp 移动端（H5 + 小程序 + App）
├─ docker/               # 生产全栈部署（docker-compose.yaml + ../deploy.sh）
├─ compose.yaml          # 开发基础设施（MySQL/Redis/Milvus 全家桶，数据落 ./volumes/）
├─ run.sh                # 一键启动（开发）
└─ init-project.sh       # 脚手架衍生脚本
```

## 🐳 生产部署

```bash
cp docker/.env.example docker/.env    # 填写 MySQL/Redis 密码
./deploy.sh                           # 构建镜像并启动全栈（Nginx + SSL），详见 docker/README.md
```

## 📚 开发约定

写代码前先读 `SKILL.md`（工程地图、模块/页面结构、常用命令、验证方式）。新业务模块主路径：建表 → 代码生成器（菜单：系统工具）→ 生成前后端代码 → 微调。
