# SopFast

基于 FastapiAdmin 脚手架整合 SopAgent 的 S&OP 产销协同平台，采用模块化单体后端与独立 Web、移动端工程。

## 技术栈

| 层级 | 技术 | 声明版本或标签 | 来源 / 含义 |
| --- | --- | --- | --- |
| 后端 | Python | >=3.12 | 运行要求 |
| 后端 | FastAPI / Pydantic | 0.138.2 / >=2.12.5 | 依赖声明 |
| 后端 | SQLAlchemy / Alembic / Uvicorn | 2.0.51 / 1.18.4 / 0.49.0 | 依赖声明 |
| Web | Vue / TypeScript / Vite | ^3.5.34 / ^6.0.3 / ^7.1.5 | 依赖声明 |
| Web | Element Plus / Pinia / Vue Router | ~2.14.3 / ^3.0.4 / ^5.0.7 | 依赖声明 |
| Web | Tailwind CSS / Axios / ECharts | ^4.3.0 / ^1.16.1 / ^6.0.0 | 依赖声明 |
| 移动端 | uni-app | 3.0.0-4080520251106001 | 依赖声明 |
| 移动端 | Vue / TypeScript / Vite | ~3.4.38 / ~5.5.4 / ^5.2.8 | 依赖声明 |
| 移动端 | Wot UI / Pinia / Alova | ^2.2.0 / ^2.3.1 / ^3.5.1 | 依赖声明 |
| AI | Agno / LangChain / LangGraph / MCP | 2.5.8 / >=0.2.14 / >=0.2.31 / >=1.20.0 | 依赖声明 |
| AI | OpenAI SDK / PyMilvus | 2.46.0 / >=2.4.0 | 依赖声明 |
| 测试 | pytest / Ruff | 9.0.2 / 0.14.13 | 依赖声明 |
| Web 质量 | Vitest / vue-tsc / ESLint | ^4.1.7 / ^3.2.9 / ^10.3.0 | 依赖声明 |
| Web 质量 | Prettier / Stylelint | ^3.6.2 / ^17.0.0 | 依赖声明 |
| 运行工具 | Node.js | >=20.19.0 | Web 运行要求；移动端要求见其 package.json |
| 运行工具 | pnpm | Web 9.15.3 / 移动端 9.9.0 | packageManager 声明 |
| 运行工具 | uv / Docker Compose | uv 未固定 / Compose v2 | 工具要求 |
| 开发基础设施 | mysql | mysql:8.0 | Compose 镜像标签 |
| 开发基础设施 | redis | redis:7-alpine | Compose 镜像标签 |
| 开发基础设施 | milvus | milvusdb/milvus:v2.5.14 | Compose 镜像标签 |
| 开发基础设施 | etcd | quay.io/coreos/etcd:v3.5.18 | Compose 镜像标签 |
| 开发基础设施 | minio | minio/minio:RELEASE.2024-05-28T17-19-04Z | Compose 镜像标签 |
| 开发基础设施 | attu | zilliz/attu:v2.5.11 | Compose 镜像标签 |
| 生产代理 | nginx | nginx:1.25-alpine | Compose 镜像标签 |

以上记录仓库声明，保留原始 `^`、`~`、`>=` 等版本约束，不代表实际安装版本。依赖声明见 [backend/pyproject.toml](backend/pyproject.toml)、[Web package.json](frontend/web/package.json)、[移动端 package.json](frontend/app/package.json)；解析版本以对应 `uv.lock` / `pnpm-lock.yaml` 为准，运行环境以实际安装和镜像为准。公司数仓通过独立只读连接接入，数仓服务端版本尚未核实。

## 文档职责

| 文件 | 维护内容 |
| --- | --- |
| `README.md` | 项目总览、首次启动、目录与文档入口 |
| [prd.md](prd.md) | 当前业务目标、数据边界、待确认事项与验收标准 |
| [SKILL.md](SKILL.md) | 开发步骤、验证命令、迁移与发布操作 |
| `AGENTS.md` / `CLAUDE.md` | 架构边界与编码助手约束，两份完整副本同步更新 |
| [CHANGELOG.md](CHANGELOG.md) | SopFast 自身的未发布变化、正式版本及升级事项 |

新增或修改信息时更新对应文档；工程事实以当前代码和配置为准，业务目标以用户最新要求为准。

每次改动通过 Git 提交及 PR 描述追溯目的、范围和验证结果；发布相关变化汇总到 `CHANGELOG.md`。当前各工程声明版本分别为后端 3.2.0、Web 3.0.0、移动端 3.1.0，它们不等于 SopFast 整体发布版本。正式发布流程见 [开发指南](SKILL.md)。

## 快速开始

适用于 WSL / Linux：前后端运行在本机，基础设施运行在 Docker 中。

环境要求：Python >= 3.12、uv、Node.js >= 20.19、pnpm 9、Docker 与 Docker Compose v2。包管理器版本以各端 `package.json` 为准。

```bash
# 在仓库根目录执行
./run.sh
```

首次运行会从模板创建 `backend/env/.env.dev`（本地数据库与 Redis 配置、随机 SECRET_KEY）以及 `frontend/web/.env.development`。前端还需要通用 `frontend/web/.env`；该文件缺失时按 [开发指南](SKILL.md) 配置。

| 服务 | 默认开发地址或端口 |
| --- | --- |
| Web | `http://127.0.0.1:5180` |
| 后端 / Swagger | `http://127.0.0.1:8001` / `http://127.0.0.1:8001/docs` |
| MySQL / Redis | 3309 / 6381 |
| Milvus / Attu | 19532 / `http://127.0.0.1:8083` |

种子账号为 `super`、`admin`、`user`，初始密码为 `123456`；已有数据库的账号密码以实际设置为准。生产部署前修改默认密码。

## 工程与能力

| 位置 | 内容 |
| --- | --- |
| `backend/app/core/` | 统一认证、权限、数据库、缓存、调度等基础设施 |
| `backend/app/modules/` | 系统、监控、任务、AI、SOP 等业务模块 |
| `backend/app/modules/sop/` | 数据接入、业务报表、快照与 Word 导出、Agent、RAG、文档管理 |
| `frontend/web/src/views/module_sop/` | 工作台、预测校验、市场信息、会议报告及数据中心页面 |
| `frontend/web/src/views/module_ai/` | AI 页面，包含 SOP 聊天面板与知识库入口 |
| `frontend/app/` | 独立移动端工程 |
| `docs/business/` | 业务原始资料 |
| `docker-compose.yaml` | 开发基础设施，容器名使用 `sopfast_` 前缀 |
| `docker/`、`deploy.sh` | 生产部署配置与脚本 |

AI 预测当前等待其他部门接入；市场信息和扩展数据域是否可用取决于实际数据源。业务范围与未决口径见 [prd.md](prd.md)。

菜单由 `backend/app/modules/sop/menu_sync.py` 启动时幂等对账，按角色差异化授权。菜单变更后已有会话需重新登录。`SOP_ENABLE=false` 跳过 SOP 表初始化、MCP 初始化与监听、夜间快照任务，路由仍然注册。

## 数据与部署

开发基础设施默认持久化到 `volumes/` 下的 mysql、redis、etcd、minio、milvus 子目录。可在根目录 `.env` 中设置 `DOCKER_VOLUME_DIRECTORY` 修改位置；切换目录不会自动迁移旧数据。

生产操作见 [docker/README.md](docker/README.md)，发布步骤见 [SKILL.md](SKILL.md)。当前生产 Compose 主要编排后端、Nginx、MySQL 与 Redis；完整 SOP 还需核对业务数据库连接、Redis db2、Milvus、模型配置及业务文件持久化，不能把容器启动视为完整功能验收。

各工程细节：[后端](backend/README.md)、[Web](frontend/web/README.md)、[移动端](frontend/app/README.md)。各端说明如与代码不符，以实际脚本和配置为准。
