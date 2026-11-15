# FastStack 项目规范

> 本文件只写本项目的架构边界与专属规则。通用代码质量、完成标准、文档约束见全局 `CLAUDE.md`。
> `AGENTS.md` 与本文件**逐字节一致**，任何改动必须同步两份。

## 分支

| 分支 | 职责 |
| --- | --- |
| `main` | 脚手架主线，日常改动全部落在这里（GitHub 默认分支） |
| `master` | 上游 FastapiAdmin 基线，只在追平上游时改动 |

追平上游：在 `master` 上合并上游改动并提交，然后 `git switch main && git merge master`。

## 顶层目录

| 目录 | 职责 |
| --- | --- |
| `backend/` | FastAPI 服务，入口 `main.py`，默认端口 8001 |
| `frontend/web/` | Vue3 管理后台，Vite 开发端口 5180 |
| `frontend/app/` | uni-app 移动端，有独立约定（见 `frontend/app/.agents/skills/`） |
| `docker/` | 生产部署（compose + nginx + Dockerfile） |
| `docs/` | 技术规范与计划；一次性报告归档到 `docs/history/` |

根目录 `docker-compose.yaml` 只起本地开发基础设施；`docker/docker-compose.yaml` 是全栈生产部署。

## 后端模块边界

- 业务模块固定放在 `app/modules/<模块>/<功能>/`，每个功能目录只放这五类文件：
  `controller.py`（路由）/ `service.py`（业务）/ `crud.py`（数据）/ `model.py`（ORM）/ `schema.py`（Pydantic）。
- `app/plugin/` 放可插拔模块，结构与 `modules/` 同构，顶级目录名以 `module_` 开头。
- 路由**只能**在 `app/api/v1/routers.py` 的 `DOMAIN_CONTROLLERS` 注册，不要在别处 `include_router`。
- 基础设施统一在 `app/core/`：`base_crud` / `base_model` / `base_schema` / `security` / `dependencies` / `exceptions` / `ap_scheduler` / `sse_manager` / `middlewares`。业务模块不得自建同类基类。
- 配置只在 `app/config/setting.py`（`Settings`）和 `path_conf.py`（路径常量）。新增配置项加在这两个文件，不要散落到模块内。

## 前端模块边界

- API 层 `src/api/module_<x>/` 与后端模块一一对应；页面在 `src/views/module_<x>/`。
- 列表/表单/弹窗一律复用 `hooks/core/` 套件（`useTable`、`useCrudForm`、`useCrudDialog`、`useTableColumns`、`useImportExport`）与公共组件 `FaXxx`，不手写 `ElTable`/`ElDialog`。
- 组件 `defineOptions({ name })` 必须与菜单 `route_name` 一致，否则 KeepAlive 缓存失效。
- 目录路由不挂组件（`component` 保持 `undefined`），KeepAlive 只在 `layouts/fa-page-content/index.vue` 存在一层。
- i18n 词条必须同时加到 `locales/langs/zh.json` 与 `en.json`。

## 数据库

- 默认数据库是 PostgreSQL 18（`DATABASE_TYPE=postgres`），MySQL 仅作兼容保留。
- 驱动是可选 extra：PostgreSQL 用 `uv sync --extra postgres`；MySQL 用 `mysql`，另有 `sqlite` / `all-db`。不带 `--extra` 启动会因为缺驱动失败。
- 连接串由 `app/config/db_url.py` 统一拼装，不要在各处手写 URI。
- 向量检索用 pgvector，由 `VECTOR_STORE_ENABLE` 控制：关闭时启动不建扩展、不建向量表，普通项目无需预装 pgvector。
- **改了 ORM 模型必须生成并执行 Alembic 迁移**：`uv run main.py revision -m "..."` + `uv run main.py upgrade --env=dev`。
- 种子数据在 `backend/sql/*.json`（菜单/角色/用户/字典/参数），由 `app/scripts/initialize.py` 在启动时导入。

## 鉴权

- 权限标识为三段式 `模块:资源:操作`（如 `module_ai:chat:query`），前后端必须完全一致。
- 后端每个接口都要挂 `Security(AuthPermission(["..."]))`；无权限要求的接口必须显式加入 `setting.py` 的 `WHITE_API_LIST_PATH`。
- 前端按钮级权限用 `v-hasPerm="'sys:user:add'"`，代码内判断用 `useAuth().hasAuth(...)`。
- 菜单与按钮权限写在 `backend/sql/sys_menu.json`，权限角色关联在 `sys_role_menus.json`。
- 新增页面后必须在「菜单管理」配置 `route_path` / `route_name` / `component_path` / `keep_alive`，否则动态路由不生效。

## 版本号

- 唯一来源是仓库根 `VERSION`。后端 `setting.py` 与前端 `vite.config.ts` 均读取该文件，禁止在 `.env` 或代码里再写死版本。
