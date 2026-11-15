<div align="center">
  <img src="./frontend/web/public/logo.png" width="120" alt="logo" />
  <h1>FastStack</h1>
  <p>个人全栈脚手架：FastAPI + Vue3 + MySQL + Redis + Milvus，前后端开箱即用。</p>
</div>

基于开源项目 [FastapiAdmin](https://github.com/fastapiadmin/FastapiAdmin) 精简而来，MIT 协议。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · Redis · uv |
| Web 前端 | Vue 3 · Vite · TypeScript · Element Plus · Tailwind 4 · Pinia |
| 移动端 | uni-app · Vue 3 · TypeScript |
| 基础设施 | MySQL 8 · Redis 7 · Milvus · MinIO · Docker Compose |

## 文档职责

| 文件 | 职责 |
| --- | --- |
| `README.md` | 项目门面：简介、技术栈、启动入口、端口与目录概览 |
| `SKILL.md` | 可执行命令：启动、迁移、测试、构建、排查 |
| `CLAUDE.md` / `AGENTS.md` | 架构边界与项目专属规则（两份逐字节一致） |
| `prd.md` | 业务目标与验收口径，仅人工维护 |
| `CHANGELOG.md` | 用户与运维可见的变更记录 |
| `backend/README.md` | 后端目录结构与环境变量 |
| `frontend/web/README.md` | Web 前端环境变量与开发约定 |
| `frontend/app/README.md` | 移动端开发说明 |
| `docker/README.md` | 生产部署完整步骤 |

## 运行

首次执行 `./run.sh` 会自动生成 `.env`、`backend/env/.env.dev`、`frontend/web/.env.development`，拉下代码直接跑即可。

```bash
./run.sh                    # 本地开发：docker 基础设施 + 后端热重载 + 前端 Vite
./stop.sh                   # 停止前后端与基础设施
./deploy.sh                 # 生产部署（详见 docker/README.md）

cd backend && uv run pytest          # 后端测试
cd frontend/web && pnpm test         # 前端测试
```

| 服务 | 地址 |
| --- | --- |
| Web 前端 | `http://127.0.0.1:5180` |
| 后端接口 | `http://127.0.0.1:8001` |
| Swagger | `http://127.0.0.1:8001/docs` |
| Attu（Milvus 控制台） | `http://127.0.0.1:8082` |
| MySQL / Redis | `127.0.0.1:3307` / `127.0.0.1:6380` |

默认账号 `super`、`admin`、`user`，密码均为 `123456`，部署后请立即修改。

## 目录

| 目录 | 职责 |
| --- | --- |
| `backend/` | FastAPI 服务，业务模块在 `app/modules/` |
| `frontend/web/` | Vue3 管理后台 |
| `frontend/app/` | uni-app 移动端 |
| `docker/` | 生产部署配置（compose + nginx + Dockerfile） |
| `docker-compose.yaml` | 本地开发基础设施 |
| `volumes/` | 本地数据目录（不提交 Git） |

## 版本

版本号唯一来源是根目录 [`VERSION`](VERSION)，后端与前端构建均读取该文件。
