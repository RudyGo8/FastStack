# SopFast 整合方案：以 FastapiAdmin 脚手架为基座融合 SopAgent

## 已确认的决策

| 决策点 | 结论 |
|---|---|
| 前端 | 7 个页面全部用 Element-Plus 重写进 sopfast web，走完整 RBAC 菜单 |
| 基础设施 | 沿用 fva-* 容器名与端口（MySQL 3307 / Redis 6380 / Milvus 19531 / Attu 8082） |
| 业务库 | MySQL 只用一个 `sop_fast` 库：系统表（sys_*/task_* 等）与 SOP 业务表全部放这里 |
| DB 访问 | SopAgent 业务代码保留同步 SQLAlchemy（独立 engine 指向 sop_fast 库），不做异步化；脚手架异步引擎同样指向 sop_fast |

## 总体结构

```
SopFast/
├── backend/
│   ├── app/modules/sop/              # ★ 新增业务模块（收编 SopAgent）
│   │   ├── plugin.toml
│   │   ├── config.py                 # SOP_* 环境变量集中读取（替代原 core/config.py）
│   │   ├── database.py               # 同步 engine → mysql://...@localhost:3307/sop_fast（与脚手架异步引擎同库）
│   │   ├── models/                   # 业务表模型（12 张，丢弃 db_user）
│   │   ├── schemas/
│   │   ├── agent/ rag/ tools/ tracing/ services/ utils/   # 原样搬运 + import 改写
│   │   ├── domain/                   # 原 domains/sop/*（规则、同步、快照、导出）
│   │   ├── chat/controller.py        # 会话管理 + SSE 流式问答
│   │   ├── document/controller.py    # 文档上传/列表/删除
│   │   └── report/controller.py      # S&OP 数据查询/导入/快照/导出
│   └── env/.env.dev|.env.example     # 追加 SOP 配置段
├── frontend/web/
│   ├── src/api/module_sop/{chat,document,report}.ts
│   └── src/views/module_sop/{dashboard,data_center,knowledge,analysis,report,market,chat}/index.vue
├── docker/mysql/init/01-create-sop-fast.sql  # 容器首启自动建 sop_fast 库
└── volumes/                          # 空目录，首启初始化
```

**路由映射**（ROOT_PATH=/api/v1）：
- `/api/r1/sop/*` → `/api/v1/sop/*`
- `/api/r1/chat/*` → `/api/v1/sop/chat/*`
- `/api/r1/documents/*` → `/api/v1/sop/documents/*`
- 原 auth 路由、db_user 表删除 → 统一用脚手架 `/api/v1/system/auth/*`

---

## 阶段 1：后端收编（可独立验证）

### 1.1 依赖合并（backend/pyproject.toml）
追加：langchain、langchain-community、langchain-core、langchain-mcp-adapters、langchain-text-splitters、langgraph、mcp、mysql-mcp-server、pymilvus、docx2txt、pypdf、pymupdf、unstructured、rapidocr-onnxruntime、ragas、structlog。
丢弃：python-jose（auth 废弃）、uvicorn/python-dotenv/fastapi/sqlalchemy/redis（脚手架已有，版本满足）。
`uv sync` 验证可装（风险：unstructured+onnxruntime 体积 ~1GB，装不动则 OCR 功能降级延后）。

### 1.2 模块搬运与 import 改写（83 个 py 文件）
- `app/{agent,rag,tools,tracing,services,models,schemas,utils}` → `app/modules/sop/` 同名子包
- `app/domains/sop/*` → `app/modules/sop/domain/`
- `app/core/{config,database,cache}.py` → 适配为 `app/modules/sop/{config,database,cache}.py`
- **丢弃**：`core/security.py`、`api/routes/auth.py`、`models/db_user.py`
- 批量改 import：`from app.core.config|database|cache import` → `from app.modules.sop.…`；`from app.agent|rag|tools|models|schemas|services|domains…` → `from app.modules.sop.…`
- **防撞名校验**：收编完成后 grep 确认 sop 模块内无 `from app.core.`（脚手架 app.core 存在，静默错引会出 bug）
- 日志保留 structlog（`app/modules/sop/utils/log.py`），不强行切 loguru

### 1.3 配置合并
- `env/.env.example`、`env/.env.dev` 追加 SOP 段：模型（ARK_API_KEY/BASE_URL/MODEL/…）、RAG、Milvus(19531)、S&OP 源库、Redis(6380, db=2, 前缀 sop_agent)、业务 MySQL(3307/sop_fast)
- 敏感值（API Key）留空由使用者填

### 1.4 controller 层重写（5 组路由 → 3 个 controller，脚手架风格）
- `OperationLogRoute` + `Security(AuthPermission([...]))` + `SuccessResponse` 包装
- chat/stream 保留 `StreamingResponse` SSE；会话归属用 `AuthSchema.user.username`
- 文档目录：`backend/data/sop/documents`
- `app/api/v1/routers.py` DOMAIN_CONTROLLERS 增加 `"/sop": [ChatRouter, DocumentRouter, ReportRouter]`

### 1.5 lifespan 挂载（create_app，加 SOP_ENABLE 开关）
- `mcp_client_manager.initialize()` + `watch_config_loop(30)`
- `snapshot_scheduler_loop(23:00)`
- sop_fast 库启动时 create_all（checkfirst，仅业务表）

### 1.6 菜单与权限种子（sql/sys_menu.json）
新增「S&OP 分析」目录 + 7 个页面菜单（component_path=`module_sop/xxx/index`）+ 按钮权限：
`module_sop:report:query|import|sync|export`、`module_sop:document:upload|delete`、`module_sop:chat:stream` 等；admin 角色全量授权（新库首启自动种入）。

### 1.7 docker 建库
docker-compose 的 `MYSQL_DATABASE` 改为 `sop_fast`（新 volumes 首启直接建库）；脚手架 env 的 `DATABASE_NAME` 同步改为 `sop_fast`。若旧 fva-mysql 容器还在跑，手动执行 `CREATE DATABASE sop_fast` 后重启后端即可。

### 1.8 测试移植
SopAgent 业务测试（sop_rules / sop_ingestion / sop_snapshots / sop_service / warehouse_sync）移植到 `backend/tests/module_sop/`，改 import 跑通；routes 测试按新路径重写（可精简）。

---

## 阶段 2：前端 Element-Plus 重写（sopfast web）

### 2.1 API 层
`src/api/module_sop/{chat,document,report}.ts`，沿用现有 request 封装（自动带 token/刷新）。

### 2.2 页面（约 3700 行 Vue → TS + Element-Plus）
| 新页面 | 原页面（行数） | 要点 |
|---|---|---|
| module_sop/dashboard | DashboardPage (705) | el-card 指标卡 + echarts 趋势图 |
| module_sop/data_center | DataCenterPage (678) | el-tabs：数据源目录 / xlsx 导入(el-upload) / 同步状态 |
| module_sop/knowledge | KnowledgePage (574) | 文档上传/列表/删除 + 向量库状态 |
| module_sop/analysis | AnalysisPage (202) | SPU 查询 + 指标分析 |
| module_sop/report | ReportPage (1031) | 报告列表/详情/快照生成/docx 导出 |
| module_sop/market | MarketPage (45) | 市场热点展示 |
| module_sop/chat | ChatPage (444) | 会话列表 + SSE 流式对话 + markdown-it/highlight.js 渲染 |

- 复用脚手架已有依赖：echarts 6、markdown-it、highlight.js、dompurify、el-upload
- 移植 SopAgent 前端业务逻辑：services/*.js 的接口调用、chatStream.js 的 SSE 解析、reportMetrics/presentation.js 的指标计算

### 2.3 路由
sys_menu 种子已含 component_path，动态路由自动生效，无需改前端路由表。

---

## 阶段 3：联调验证

1. `docker compose up -d`（fva-*；新 volumes 首启初始化 sop_fast 单库，系统表 + 业务表都在其中）
2. `uv run main.py run --env=dev`；swagger 逐个验证 /api/v1/sop/* 接口
3. 前端 `pnpm dev`：admin 登录 → S&OP 菜单 7 页逐页走查
4. 冒烟链路：上传文档 → 知识库问答（SSE）→ SPU 列表 → 生成快照 → 导出报告
5. `uv run pytest` 全量（脚手架原有测试 + module_sop 移植测试）

---

## 风险与对策

| 风险 | 对策 |
|---|---|
| 依赖体积/安装失败（unstructured、onnxruntime） | 优先 uv sync 验证；失败则拆为 optional-dependencies，OCR 解析延后 |
| sop 模块静默错引脚手架 `app.core.*` | 收编后 grep 强校验 + 导入冒烟（`python -c "import app.modules.sop"`） |
| SSE 被中间件缓冲 | X-Accel-Buffering:no 已设；联调时若异常，chat 路由豁免操作日志/限流 |
| chat 会话归属从原 user 表迁移 | 会话表带 username 字段，沿用 username 关联，无需迁移数据（新库从零开始） |

## 实施顺序

阶段 1 → 后端接口自测（swagger）→ 阶段 2 逐页重写（chat、dashboard 先行）→ 阶段 3 联调。
