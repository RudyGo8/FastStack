# FastStack 更新记录

本文件记录 FastStack 自身的发布与重要更新记录；逐次代码改动通过 Git 提交追溯。

## 未发布

### 新增

- 建立项目的架构地图、开发规范与执行约束（`CLAUDE.md` 与 `AGENTS.md` 保持完全同步）。
- 完善工作台首页基础能力：引入真实业务数据概览（`WelcomeBanner`、`DataStatistics`）、近 7 天登录统计（操作系统/浏览器/地区分布及趋势）、操作统计分析（操作类型、模块分布及趋势）。
- 后端新增 `module_monitor:dashboard` 统计接口路由与服务层，支持超级管理员与普通用户数据权限隔离，并实现权限实时从数据库加载刷新。
- 前端中英文国际化语言包补齐首页工作台对应词条（`zh.json` 与 `en.json`）。
- 全套 AI 管理模块升级增强：
  - 采用现代多会话交互式智能问答面板（`SopChatPanel`），支持流式回复、快捷问题提示、Markdown 渲染及动态会话管理。
  - 新增会话记录管理页面（`module_ai/memory`），支持会话搜索、详情抽屉查看与会话删除。
  - 新增知识库管理（`module_ai/knowledge`）、模型配置（`module_ai/model`）和 Prompt 配置（`module_ai/prompt`）页面。
  - 后端提供统一 SSE 流式聊天端点 `/api/v1/ai/chat/stream`，并在 `backend/sql/sys_menu.json` 中配置完整的 AI 管理子菜单与权限。
