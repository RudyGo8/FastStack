# SopFast 项目约束

本文件用于指导编码助手在此仓库中开发、排查和验证。沟通、说明和提交描述默认使用中文。先理解相关实现，再修改；保持代码简洁，避免冗余代码和无关重构。

## 1. 项目定位与事实来源

SopFast 是基于 FastapiAdmin 脚手架整合 SopAgent 的 S&OP 产销协同平台，采用模块化单体后端与独立前端。系统管理、统一认证、菜单权限由脚手架提供，SOP 模块承担数据接入、业务分析、报告、Agent 与 RAG。

- 开发前阅读根目录 `SKILL.md` 及本次任务涉及的代码、测试和配置。
- `AGENTS.md` 与 `CLAUDE.md` 保留完整约束副本；修改任一文件时同步更新另一份，保持规则一致。
- 业务需求、数据边界与验收要求参考 `prd.md`；业务原始资料位于 `docs/business/`。
- 文档职责见 `README.md`：业务目标只在 `prd.md` 维护，命令与操作步骤只在 `SKILL.md` 维护，本文件维护执行约束。必要的边界提醒可保留，不复制整套需求或命令。
- 技术栈变化更新 `README.md`；发布相关变化更新根目录 `CHANGELOG.md` 的“未发布”，记录规则见 `SKILL.md`。每次改动通过 Git/PR 与交付说明追溯，不编造版本、提交或验证结果。
- 架构现状以代码和配置为准，业务目标以用户最新要求为准；发现冲突时说明，不能把规划当作已实现功能。
- 改动前执行 `git status --short`，保护已有未提交修改。禁止覆盖、回滚或清理与任务无关的内容。

## 2. 架构地图

| 位置                            | 职责                                                                |
| ------------------------------- | ------------------------------------------------------------------- |
| `backend/main.py`               | Typer CLI：启动服务、生成与应用迁移                                 |
| `backend/app/__init__.py`       | 应用工厂、生命周期、基础设施初始化与关闭                            |
| `backend/app/api/v1/routers.py` | 内置模块路由注册，`DOMAIN_CONTROLLERS` 为域路由清单                 |
| `backend/app/core/`             | 数据库、权限、安全、异常、调度、日志等公共基础设施                  |
| `backend/app/modules/system/`   | 用户、角色、菜单、认证、字典等系统功能                              |
| `backend/app/modules/ai/`       | 脚手架 AI 对话，与 SOP Agent 链路分别维护                           |
| `backend/app/modules/sop/`      | S&OP 业务边界                                                       |
| `frontend/web/`                 | Vue3 + TypeScript + Vite + Element Plus + Pinia + Tailwind 管理后台 |
| `frontend/app/`                 | 独立 uni-app 移动端，独立依赖和构建配置                             |
| 根目录 `docker-compose.yaml`    | 本地开发基础设施                                                    |
| `docker/`                       | 生产部署配置、Nginx 与镜像构建                                      |

SOP 内部职责：

- `data/`、`report/`、`chat/`、`document/`：HTTP 入口。
- `schemas/`：请求与响应契约；`models/`：持久化模型。
- `domain/`：报表口径、数据导入、数仓查询与同步、快照、导出、渠道归类和校验规则。
- `services/`：会话、文档加载、Embedding、Milvus 与父分块存储。
- `agent/`：Agent 构建、上下文和运行；`rag/`：检索与改写等管线。
- `tools/`：业务工具、RAG 工具、注册表与 MCP 网关；`tracing/`：调用追踪。
- `menu_sync.py`：SOP 菜单声明与幂等对账。

## 3. 后端边界

- 常规模块沿用 `controller/service/crud/model/schema` 分层；SOP 沿用现有 `domain/services/models/schemas` 结构。不要为统一形式重写已有模块。
- Controller 负责鉴权、参数、调用与响应；业务计算、同步、导出和 SQL 放到对应业务层。不要把领域逻辑堆进路由。
- 内置模块路由注册到 `app/api/v1/routers.py`，避免同时通过动态发现重复注册。`plugin.toml` 不能替代明确的路由注册。
- 复用 `AuthPermission`、`AuthSchema`、`OperationLogRoute` 与现有权限标识，SOP 权限形如 `module_sop:data:query`。禁止新增独立用户表、登录体系或绕过鉴权。
- 普通 JSON 接口沿用 `SuccessResponse`、`ResponseSchema[T]`；文件下载与流式接口沿用专用响应。错误遵循相邻代码的异常处理，不能捕获所有异常后返回伪成功。
- 系统数据库使用 `app/core/database.py` 的异步访问；SOP 使用 `modules/sop/database.py` 的同步 Session，两者生产配置指向同一应用库，但 ORM Base 与 Session 不同。不可交叉使用或擅自拆库。
- 同步数据库查询、文件解析和模型调用不能直接阻塞异步事件循环；使用同步路由或现有线程调度方式。Session 必须按请求/任务管理并关闭，事务失败要回滚。
- 配置分别沿用 `app/config/setting.py` 和 SOP 的 `config.py`，开发环境配置在 `backend/env/.env.dev`。禁止把连接信息、密钥或机器绝对路径写入代码。

## 4. 数据与业务口径

- 数仓连接边界是 `domain/source_database.py`，使用独立 `SOP_SOURCE_MYSQL_*` 配置与只读账号。禁止对公司数仓执行 DDL/DML，禁止使用应用库凭据替代数仓连接。
- 数仓 SQL、适配与同步在 `warehouse_queries.py`、`warehouse_sync.py` 等现有入口维护。查询参数必须绑定，动态表名/字段名必须使用可信白名单。
- 数据粒度、SPU 映射、去重键、区域和渠道归属必须有依据。字段或映射未确认时保留待接入/待适配状态，不得猜测映射、随意聚合或声称已接通。
- 保留事实数据的原始渠道，报表归类复用 `domain/channels.py`。明细渠道与全渠道汇总不能重复累计。
- 筛选、指标、预测范围、AI 预测接入阶段与验收标准遵循 `prd.md`。报表、会议报告和导出复用同一口径，禁止在各页面复制计算逻辑或用 LLM 编造业务数量。
- 仅展示真实业务数据。缺失、待接入、查询失败与真实零值必须区分；禁止通过演示数据、随机值或无依据的补零掩盖缺失。
- 导入和同步须维护现有审计、来源、质量问题与幂等机制；保留同步锁和并发保护，不能通过移除保护解决失败。
- 模型变更必须评估 Alembic 元数据和迁移，生成后检查脚本。当前 Alembic 目标是系统 `MappedBase.metadata`，不能假定 SOP 独立 Base 的模型会被自动迁移。现有 SOP 启动流程包含 `init_sop_tables()` 的 `create_all`，不能将其视为已有表结构升级方案，也不要新增隐式迁移路径。应用迁移前确认连接目标和影响。

## 5. Agent、RAG 与流式协议

- 复用 `agent/factory.py`、`agent/runner.py` 和工具注册/网关，不能绕过既有调用边界另建 Agent 体系。
- 检索、Embedding、Milvus、父分块与文档入库/删除要保持一致；改动模型维度或分块策略时必须评估存量数据兼容性。
- 会话读取、写入和删除必须保持用户隔离，不能只依赖客户端提供的 session_id。
- SOP 聊天使用 POST SSE；普通 AI 聊天另有 WebSocket 链路，不能互相替换。
- SOP 流式前端入口为 `src/api/module_ai/sop_chat.ts`，共享解析器为 `module_ai/sse.ts`。保留现有 `content`、`trace`、`rag_step`、`error`、`[DONE]` 协议及取消能力，协议调整需同步前后端。
- MCP 为可选能力；`SOP_ENABLE=false` 跳过 SOP 表初始化、MCP 初始化与监听、夜间快照任务，路由仍注册。关闭开关不保证路由可用，也不等于关闭整个模块。
- 日志和追踪不得输出密钥、Token、完整连接串或未经处理的敏感资料。

## 6. Web 前端约束

- SOP 数据与报告 API 位于 `src/api/module_sop/`，分析页面位于 `src/views/module_sop/`。
- SOP 聊天面板位于 `src/views/module_ai/chat/components/SopChatPanel.vue`，知识库位于 `src/views/module_ai/knowledge/`。不要按旧文档在 SOP 目录重复创建聊天/知识库页面。
- 普通请求统一使用 `@utils` 的 `request` 和 `ApiResponse<T>`；SSE 复用现有带鉴权的 fetch 封装。禁止硬编码后端地址或另建请求客户端。
- 页面私有组件放相邻 `components/`，共享报表组件和转换函数复用 `module_sop/shared/`；标准 CRUD 优先复用 `FaTable`、`FaDialog`、`useTable`、`useCrudForm` 等已有套件。
- 业务路由来自后端菜单。新增或调整 SOP 页面同步维护 `menu_sync.py` 中的稳定键、组件路径和权限，保留幂等对账与当前角色授权策略。
- `defineOptions({ name })` 与菜单 `route_name` 对齐，保护 KeepAlive、工作栏和登出缓存驱逐。目录路由不要新增壳组件，保持现有单层缓存与 include/exclude 管理方式，不新增 `:max` 改变缓存集合。
- 监听器、定时器、WebSocket、SSE 等资源要按页面激活/停用/卸载生命周期管理；连接守卫覆盖 CONNECTING 状态。切换筛选时取消旧请求或忽略过期响应，防止旧数据覆盖新条件。
- 前后端按钮权限标识一致；沿用现有 i18n 方式，新增公共词条维护中英文。
- Web 与移动端分别维护 API、组件和依赖。涉及跨端需求时评估两端，不能假定 Web 改动会自动同步到移动端。

## 7. 开发与验证

启动、依赖、测试、迁移与发布命令统一见 `SKILL.md`；版本要求和默认地址见 `README.md`，以实际配置为准。

- SOP Redis 默认使用 db2 与 `sop_agent` 键前缀，保留隔离策略，禁止全库清理缓存。
- 按改动范围运行已有后端/前端测试；TS/Vue 改动运行类型检查，发布相关改动运行构建。纯文档修改检查内容、路径和 diff，无需启动业务服务。
- 修复业务行为时添加能证明实际结果的必要回归测试，不能仅断言路由存在或依赖吞异常的辅助函数证明功能正常。
- 现有 `pnpm lint` 包含 `--fix`/`--write`，会修改文件；优先限定目标文件执行检查，避免产生全仓格式化改动。
- 前端 `dist` 是生成物，不直接编辑。部署任务按实际服务入口重建并同步产物；源码、构建通过与部署生效分别报告。
- `volumes/`、环境文件、业务上传、运行日志和本地数据不纳入提交。禁止为了启动或升级清空数据卷、删除业务数据、执行 `docker compose down -v`。
- 完成时说明改了什么、执行了哪些验证以及未验证部分。未执行的测试不得声称通过；不要未经用户要求提交、推送或部署。

## Code Quality Constraints

- 优先采用最简单、最直接的实现。
- 修改前必须搜索现有实现，优先复用已有代码。
- 相同或明显重复逻辑应合理封装，避免复制粘贴。
- 不得为了抽象而抽象，不得过度设计。
- 不创建无必要的 helper、utils、manager、service 等中间层。
- 删除无用代码、无用 import、临时调试代码和重复实现。
- 只修改当前需求涉及的代码，避免无关重构。

## Completion Constraint

代码写完不代表任务完成。

完成前必须：

1. 检查实现是否存在冗余或不必要复杂度。
2. 执行相关 lint / type check。
3. 执行与修改相关的测试。
4. 条件允许时执行实际运行验证。
5. 检查 git diff。
6. 验证失败必须修复后重新验证。

未经实际验证，不得宣称任务已完成。
