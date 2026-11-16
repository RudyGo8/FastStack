---
name: "faststack-dev"
description: "FastStack 操作手册：本地启动、数据库迁移、按范围测试、构建发布、常见排查。执行命令前先读本文件；架构边界与项目规则见 CLAUDE.md。"
---

# FastStack 操作手册

本文件只放**可重复执行的命令**。架构边界、模块规则、版本号约定见 [CLAUDE.md](CLAUDE.md)。

## 目录

- [1. 本地启动](#1-本地启动)
- [2. 数据库迁移](#2-数据库迁移)
- [3. 测试](#3-测试)
- [4. 构建与发布](#4-构建与发布)
- [5. 排查](#5-排查)

---

## 1. 本地启动

### 一键（推荐）

```bash
./run.sh          # docker 基础设施 + 后端热重载 + 前端 Vite
./stop.sh         # 停止前后端 + 基础设施（数据保留在 docker/volumes/dev/）
```

首次执行会自动生成三份本地配置，无需手工准备：

| 生成物 | 来源模板 | 说明 |
| --- | --- | --- |
| `.env` | `.env.example` | 基础设施数据目录 |
| `backend/env/.env.dev` | `backend/env/.env.example` | PostgreSQL 5434 / Redis 6380 / 随机 SECRET_KEY |
| `frontend/web/.env.development` | `.env.development.example` | 前端代理目标 |

### 分别启动

```bash
docker compose up -d                                    # PostgreSQL:5434 / Redis:6380（数据落 docker/volumes/dev/）
cd backend && uv sync --extra postgres && uv run main.py run --env=dev
cd frontend/web && pnpm install && pnpm run dev         # http://127.0.0.1:5180
```

`--extra postgres` 不能省。数据库驱动是可选 extra，裸 `uv sync` 装不出驱动，后端起不来。

### 首次启动做了什么

`app/scripts/initialize.py` 自动执行迁移并导入 `backend/sql/*.json` 种子数据（菜单/角色/用户/字典）。dev 环境检测到模型变更还会自动生成并应用迁移。

### 默认账号

`super` / `admin` / `user`，密码均为 `123456`。

---

## 2. 数据库迁移

```bash
cd backend
uv run main.py revision -m "说明"     # 按当前模型生成迁移文件
uv run main.py upgrade --env=dev      # 应用到 head
```

改了 `model.py` 就必须走这一步，否则启动后接口会因缺列报错。

切换数据库类型只改 `backend/env/.env.dev` 的 `DATABASE_TYPE`（`mysql` / `postgres` / `sqlite`），并按类型安装对应 extra：

```bash
uv sync --extra postgres   # MySQL 用 mysql；另有 sqlite / all-db
```

---

## 3. 测试

### 后端

```bash
cd backend
uv run pytest                                   # 全量
uv run pytest tests/test_main.py                # 单文件
uv run pytest tests/test_main.py::test_xxx -x   # 单用例，遇错即停
uv run pytest -k "migration"                     # 按名字匹配
```

`conftest.py` 会自建临时库并初始化数据，不需要预先起数据库容器。

### Web 前端

```bash
cd frontend/web
pnpm test                 # vitest run（单次）
pnpm test:watch           # 监听模式
pnpm test src/xxx.spec.ts # 单文件
pnpm ts:check             # vue-tsc 类型检查，改完 TS/Vue 必跑
pnpm lint                 # eslint + prettier + stylelint（全量，勿在提交钩子外手动跑）
```

### 移动端

```bash
cd frontend/app && pnpm dev:h5   # H5 调试；小程序用 pnpm dev:mp-weixin
```

---

## 4. 构建与发布

### Web 前端（三份产物都要同步）

```bash
cd frontend/web && pnpm build:prod
cd ../..
rsync -a --delete frontend/web/dist/ docker/nginx/web/dist/
rsync -a --delete frontend/web/dist/ backend/dist/
```

`--delete` 不能省：产物文件名带 content hash，不带会把旧 chunk 留在目录里。

| 产物 | 服务的入口 |
| --- | --- |
| `frontend/web/dist` | 构建输出目录 |
| `docker/nginx/web/dist` | docker 部署的 `/web` |
| `backend/dist` | 后端一体化托管（`path_conf.FRONTEND_DIST_DIR`） |

### 移动端

```bash
cd frontend/app && pnpm build:h5
rsync -a --delete frontend/app/dist/build/h5/ docker/nginx/app/dist/build/h5/
```

### 生产部署

```bash
cp docker/.env.example docker/.env     # 首次：填 PostgreSQL/Redis 密码
./deploy.sh
```

完整步骤（SSL 证书、域名、容器编排）见 [docker/README.md](docker/README.md)。

---

## 5. 排查

| 现象 | 检查 |
| --- | --- |
| 后端起不来，报缺驱动 | 是否漏了 `uv sync --extra postgres`（MySQL 用 `--extra mysql`） |
| `Address already in use` | `lsof -ti tcp:8001 \| xargs kill`（前端同理换 5180） |
| 接口报列不存在 / 字段缺失 | 改了 model 没跑 `uv run main.py upgrade --env=dev` |
| 新模块路由 404 | dev reload 只在文件变更时重载，动态路由发现只在启动时执行，**必须重启后端** |
| 新增页面菜单点不开 | 菜单管理里 `route_path` / `route_name` / `component_path` / `keep_alive` 没配 |
| 页面缓存失效、重复请求 | 组件 `defineOptions({ name })` 与菜单 `route_name` 不一致 |
| 线上行为和源码不一致 | 先核 dist 产物，再回源码查；源码改了没重建同步是常见原因 |
| 首次请求 500、启动不报错 | 看 `backend/logs/faststack.log`（loguru），静态托管路径问题只会在首个请求暴露 |

定位产物是否已更新：

```bash
grep -l "关键字符串" docker/nginx/web/dist/js/*.js
```
