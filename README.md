<div align=”center”>
     <p align=”center”>
          <img src=”./frontend/web/public/logo.png” width=”150” height=”150” alt=”logo” />
     </p>
     <h1>SopFast</h1>
     <p>S&OP 智能分析平台：FastAPI + Vue3 + MySQL + Redis + Milvus</p>
     <p>基于 <a href=”https://github.com/fastapiadmin/FastapiAdmin”>FastapiAdmin</a> 脚手架，融合 SopAgent 业务能力</p>
</div>

## 快速开始

适用于 WSL / Linux 开发：前后端直接运行在本机，MySQL、Redis、Milvus 等基础设施运行在 Docker 中。

```bash
# 推荐：一键启动基础设施、后端和 Web 前端
./run.sh

# 也可以分别启动
docker compose up -d
cd backend && uv sync && uv run main.py run --env=dev
cd ../frontend/web && pnpm install && pnpm run dev
```

默认地址：

| 服务 | 地址 |
| --- | --- |
| Web 前端 | `http://127.0.0.1:5180` |
| 后端接口 | `http://127.0.0.1:8001` |
| Swagger | `http://127.0.0.1:8001/docs` |
| Attu (Milvus) | `http://127.0.0.1:8083` |

默认账号为 `super`、`admin`、`user`，密码均为 `123456`。部署后请立即修改。

首次执行 `./run.sh` 会生成开发配置：

- `backend/env/.env.dev`：MySQL `3309/123456`、Redis `6381`（无密码）、随机 `SECRET_KEY`
- `frontend/web/.env.development`：Web 前端联调配置

### SOP 模块

S&OP 业务功能位于 `backend/app/modules/sop/`，包含：

- **智能问答**：RAG 知识库 + Agent 流式对话（SSE）
- **数据中心**：数据源管理、Excel 导入、同步状态
- **知识库**：文档上传/管理、向量检索
- **指标分析**：SPU 维度查询与分析
- **会议报告**：快照生成、docx 导出
- **市场热点**：外部市场数据接入（待配置数据源）

通过 `.env` 中的 `SOP_ENABLE=false` 可关闭 SOP 后台任务（MCP 热插拔、夜间快照调度）。

#### 菜单与权限

S&OP 菜单在每次后端启动时**幂等对账**：由 `menu_sync.py` 声明 16 个节点（1 目录 + 7 页面 + 8 按钮），按 `route_name` / `permission` 稳定键查找并增量创建/更新，然后自动授权给所有现有角色。管理员无法通过角色权限设置页移除 S&OP 权限，新建角色也会自动继承。

#### 升级说明

从旧版本升级时**无需清空 Docker volumes**：启动后端即自动完成菜单对账和全角色授权。已有会话需重新登录以获取最新菜单。

### 开发数据目录

根目录的 `docker-compose.yaml` 负责开发基础设施，容器名以 `sop_` 前缀隔离，数据默认保存在：

```text
volumes/
├── mysql/
├── redis/
├── etcd/
├── minio/
└── milvus/
```

如需存到其他位置，在项目根目录创建 `.env`：

```env
DOCKER_VOLUME_DIRECTORY=/volumes
```

如果从旧版配置的 Docker 命名卷切换到 `volumes/`，旧数据不会自动迁移。

## 环境要求

- Python ≥ 3.12，推荐使用 `uv`
- Node.js ≥ 20、pnpm ≥ 9
- Docker 与 Docker Compose v2

## 工程结构

```text
SopFast/
├── backend/
│   ├── app/
│   │   ├── modules/
│   │   │   ├── sop/          # S&OP 业务模块（Agent/RAG/Tools/Tracing）
│   │   │   ├── system/       # 系统管理（用户/角色/菜单/字典等）
│   │   │   ├── ai/           # AI 对话模块
│   │   │   └── ...           # 监控/任务/代码生成等
│   │   └── core/             # 框架核心（数据库/缓存/权限/调度）
│   ├── env/                  # 环境变量配置
│   └── sql/                  # 菜单/权限种子数据
├── frontend/
│   └── web/                  # Vue3 管理后台
│       └── src/views/module_sop/  # SOP 7 个页面
├── docker/                   # 生产部署配置
│   └── docker-compose.yaml
├── volumes/                  # 本地开发数据（不提交 Git）
├── docker-compose.yaml       # 本地开发基础设施（sop_* 容器）
├── run.sh                    # 一键开发启动
└── deploy.sh                 # 生产部署
```

## 基础设施端口

开发环境使用独立端口，避免与其他项目冲突：

| 服务 | 端口 |
| --- | --- |
| MySQL | 3309 |
| Redis | 6381 |
| Milvus | 19532 |
| Attu | 8083 |

## 生产部署

```bash
cp docker/.env.example docker/.env
# 编辑 docker/.env，设置 MySQL、Redis 密码
# 按 docker/README.md 准备 SSL 证书
./deploy.sh
```

生产部署的完整说明见 [docker/README.md](docker/README.md)。

## 集成对账

SopAgent 原始业务能力在 SopFast 中的恢复状态见 [docs/sopagent-parity.md](docs/sopagent-parity.md)。
