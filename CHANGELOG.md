# FastStack 更新记录

后续新增记录单条控制在 1～2 句话内，只写用户/运维可见的变化，代码细节由 `git log` 追溯。

## 未发布

### 新增

- 工作台首页改为真实业务数据：概览卡片、近 7 天登录统计、操作统计，按超管与普通用户隔离数据权限。
- AI 管理模块重做：多会话流式问答面板、会话记录管理、知识库、模型与 Prompt 配置。
- 新增 `stop.sh`，一条命令停止前后端与基础设施；`run.sh` 首次运行自动生成全部本地配置。

### 新增（Agent Harness）

- 引入通用 LangGraph Agent Harness：身份、预算、工具网关、审批、持久任务与执行追踪，与任何业务模块解耦。
- 新增 `ai_agent_task` 任务队列表与 PostgreSQL 持久 Checkpoint（独立 schema `ai_agent_checkpoint`）。
- 业务工具通过注册接口接入，框架不内置业务工具；有副作用的工具必须声明幂等键与审批要求。

### 变更

- 数据库驱动改为按需安装（`uv sync --extra mysql`），不再默认全装。
- 版本号统一由根目录 `VERSION` 提供，不再在 `.env` 中重复定义。
- 移除仓库内的演示页与示例数据，首页只保留真实数据。
- 默认分支改为 `main`（脚手架主线），新增 `master` 承载上游 FastapiAdmin 基线。

### 升级注意

- 拉取后必须执行 `uv sync --extra mysql`，否则后端因缺数据库驱动无法启动。
- 需要执行数据库迁移：`uv run main.py upgrade --env=dev`。
