---
name: sopfast-dev
description: "SopFast 仓库开发操作指南。适用于本项目的开发、调试、测试、数据库变更与发布操作。"
---

# SopFast 开发操作指南

本文件维护操作步骤和命令。项目入口见 [README.md](README.md)，业务验收见 [prd.md](prd.md)，架构和执行约束见 `AGENTS.md` / `CLAUDE.md`。

## 1. 开始任务

1. 执行 `git status --short`，确认已有修改及任务范围。
2. 阅读对应约束、需求、相邻代码和已有测试，明确验收条件与数据依赖。
3. 定位后端 Controller、领域服务、前端 API、页面、菜单与权限的对应关系；跨端任务同时评估 Web 和移动端。
4. 数据口径未确认时记录缺口，不自行推断映射；继续处理不依赖该口径的部分。

## 2. 开发环境

首次启动优先在根目录执行 `./run.sh`，详见 README。手动启动时：

```bash
# 根目录：配置文件缺失时从模板复制，已有文件不覆盖
cp -n backend/env/.env.example backend/env/.env.dev
cp -n frontend/web/.env.development.example frontend/web/.env.development
# 编辑 .env.dev，使系统连接与根目录 Compose 的 MySQL 3309、Redis 6381 一致
# 同时核对 SOP 的 MYSQL_*、SOP_REDIS_URL、MILVUS_* 与模型配置

docker compose up -d

# backend/ 内
uv sync
uv run main.py run --env=dev

# frontend/web/ 内，另开终端
pnpm install
pnpm dev
```

Web 通用 `.env` 缺失时需配置 `VITE_PORT=5180`、`VITE_APP_BASE_API=/api/v1`、`VITE_BASE_URL=/`；其他通用选项参考现有前端配置与工程说明。开发 mode 使用 `.env.development`，生产 mode 使用 `.env.production`。

系统连接由 `backend/app/config/setting.py` 管理；SOP 独立读取 `backend/app/modules/sop/config.py`。系统层支持多种数据库，不代表完整 SOP 可以只用 SQLite 启动。公司数仓只读连接使用 `SOP_SOURCE_MYSQL_*`，与可写应用库分开。

Vite 将 `/api/v1` 代理到 `VITE_API_BASE_URL`；普通 AI WebSocket 使用 `VITE_APP_WS_ENDPOINT`。后端测试通常请求 `/sop/...` 等实际路由，不将代理前缀直接套入测试。

停止本机前后端可使用 Ctrl+C；停止开发基础设施使用根目录 `docker compose stop`。

## 3. 实现功能

- 标准 CRUD 参考 `backend/app/modules/system/dict/`；SOP 按 `domain/`、`services/` 等现有职责扩展。
- 内置路由在 `backend/app/api/v1/routers.py` 注册；新增动态插件后重启服务并检查实际路由，避免与内置注册重复。
- SOP/AI 声明管理的菜单在 `backend/app/modules/sop/menu_sync.py` 修改；通用种子数据在 `backend/sql/`。不要只改数据库中的受管菜单。
- 前端普通接口在 `frontend/web/src/api/` 维护；SOP 聊天 API 位于 `module_ai/sop_chat.ts`，共享流解析器为 `module_ai/sse.ts`。
- 页面优先复用 `components/` 与 `hooks/core/`；报表转换复用 `views/module_sop/shared/`。权限字符串与后端、菜单保持一致。
- 修改移动端时阅读 `frontend/app/.agents/skills/` 对应说明，依赖和命令在该端独立执行。

## 4. 数据库变更

先检查模型所属 Base、目标数据库、现有迁移和数据影响。当前 Alembic 的 `target_metadata` 为系统 `MappedBase.metadata`；SOP 使用独立 Base，不能假定自动生成会包含 SOP 表变更。

```bash
# backend/ 内：仅在已确认迁移覆盖范围后执行
uv run main.py revision --env=dev -m "迁移说明"
# 检查生成脚本，确认没有意外删表、删列或数据丢失
uv run main.py upgrade --env=dev
```

系统初始化会自举空库、处理已有迁移和种子数据；dev 下还会尝试自动生成并应用模型差异。启动可能改变数据库或迁移文件，执行前确认目标连接。

SOP 启动建表使用 `init_sop_tables()` / `create_all(checkfirst=True)`，无法升级已有表结构。SOP 模型变更需明确迁移覆盖方案并验证，不能仅重启服务。

## 5. 验证与交付

| 改动 | 最小验证 |
| --- | --- |
| 后端业务 | 对应 pytest 用例；接口变更检查鉴权、参数和响应 |
| TS / Vue | 对应 Vitest 用例与类型检查 |
| 筛选、报表、导出 | 同条件结果一致性；必要时浏览器核验 |
| Agent / RAG / SSE | 工具和检索边界、用户隔离、流协议与取消 |
| 数据模型 | 迁移内容、覆盖范围与数据兼容性 |
| 发布 | 类型检查、测试、构建及实际服务入口 |
| 纯文档 | 路径、引用、约束同步与 `git diff --check` |

```bash
# backend/ 内，按范围选择
uv run pytest tests/module_sop
uv run pytest tests/module_system/test_auth_permissions.py
uv run ruff check app/modules/sop tests/module_sop

# frontend/web/ 内，按范围选择
pnpm test src/views/module_sop
pnpm test src/views/module_ai
pnpm ts:check
pnpm build
```

`pnpm lint` 含自动修复和格式化，先检查脚本并限定文件，避免全仓改写。修改行为时使用能验证实际结果的回归用例；“路由存在”或吞异常的测试不能证明功能正确。

交付说明包含改动范围、验证结果、未验证内容及数据依赖。提交经授权后遵循 commitlint / husky，使用 feat、fix、docs、refactor 等类型。

### 改动与版本记录

- 每个独立目的使用清晰的 Git 提交；有 PR 时说明问题、最终行为和验证结果。尚未提交的改动在交付说明中标明，不伪造提交或发布状态。
- 功能、修复、不兼容变更和重要工程变化，在根目录 `CHANGELOG.md` 的“未发布”中补充；同一任务后续修正合并为一条，不记录每次工具调用或重复格式化。
- 技术栈变化同步更新 README；需求变化更新 PRD；开发步骤变化更新 SKILL；约束变化同时更新 AGENTS 与 CLAUDE。
- 正式发布时确认 SopFast 整体版本，把对应“未发布”条目归入 `版本号 — YYYY-MM-DD`，补充迁移、配置及升级事项。版本采用 `主版本.次版本.修订号`：不兼容变化、兼容新增功能、兼容修复分别考虑对应递增。
- 发布经授权后创建对应 `vX.Y.Z` Git 标签并关联已验证的提交，保留“未发布”入口。各端包版本与整体发布版本分别管理，不直接把脚手架版本当作项目发布记录。

## 6. 常见排查入口

- 重复请求/连接：用 `rg` 定位回调来源，检查页面激活/停用清理、CONNECTING 守卫、单层 KeepAlive 和登出缓存驱逐。缓存相关代码位于 `frontend/web/src/layouts/fa-page-content/index.vue`、`frontend/web/src/store/modules/worktab.store.ts`。
- 筛选错数据：检查请求序号/取消、失败清空、API 参数、来源同步时间及原始事实，最后再判断业务口径。
- 前端托管失败：检查 `backend/app/config/path_conf.py` 的 `FRONTEND_DIST_DIR` 与应用挂载目录是否一致。
- 生成代码异常：检查 `backend/templates/`，注意 Jinja2 循环内赋值不会自动更新外层变量；用过滤器或 namespace 表达跨循环状态。

## 7. 发布产物

`dist` 为生成物。先配置 `frontend/web/.env.production`，执行类型检查和测试，再构建；当前 `build:prod` 只调用 Vite，不包含类型检查。

```bash
# frontend/web/ 内
pnpm ts:check
pnpm test
pnpm build:prod

# 根目录：按实际部署方式选择一条，不必同时同步两处
rsync -a --delete frontend/web/dist/ docker/nginx/web/dist/  # Docker /web
rsync -a --delete frontend/web/dist/ backend/dist/           # 后端静态托管
```

同步前确认目标目录；`--delete` 清理该产物目录的旧文件。部署步骤见 `docker/README.md`，`deploy.sh` 不负责构建前端。发布后检查实际访问页面、静态资源、接口和上传资料持久化，分别报告源码验证、构建与部署状态。
