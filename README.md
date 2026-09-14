<div align="center">
     <p align="center">
          <img src="./frontend/web/public/logo.png" width="150" height="150" alt="logo" />
     </p>
     <h1>FastStack</h1>
     <p>个人全栈脚手架：FastAPI + Vue3 + TypeScript + MySQL + Redis + Milvus</p>
     <p>基于开源项目 <a href="https://github.com/fastapiadmin/FastapiAdmin">FastapiAdmin</a> 精简而来，MIT 协议</p>
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
| Attu | `http://127.0.0.1:8082` |

默认账号为 `super`、`admin`、`user`，密码均为 `123456`。部署后请立即修改。

首次执行 `./run.sh` 会生成开发配置：

- `backend/env/.env.dev`：MySQL `3307/123456`、Redis `6380`（无密码）、随机 `SECRET_KEY`
- `frontend/web/.env.development`：Web 前端联调配置

### 开发数据目录

根目录的 `docker-compose.yaml` 负责开发基础设施，数据默认保存在：

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
FastStack/
├── backend/                  # FastAPI 后端
├── frontend/
│   ├── web/                 # Vue3 管理后台
│   └── app/                 # UniApp 移动端
├── docker/                  # 生产部署配置
│   └── docker-compose.yaml  # MySQL、Redis、Backend、Nginx
├── volumes/                 # 本地开发数据（不提交 Git）
├── docker-compose.yaml      # 本地开发基础设施
├── run.sh                   # WSL / Linux 一键开发
├── deploy.sh                # 生产部署
└── init-project.sh          # 从当前脚手架复制新项目
```

本地开发和生产部署使用不同的 Compose 文件：

- 根目录 `docker-compose.yaml`：本地开发，只启动基础设施。
- `docker/docker-compose.yaml`：生产部署，启动数据库、后端和 Nginx。

## 文档导航

- [后端开发](backend/README.md)
- [Web 前端开发](frontend/web/README.md)
- [移动端开发](frontend/app/README.md)
- [生产部署](docker/README.md)
- [工程开发约定](SKILL.md)

## 衍生新项目

```bash
./init-project.sh my-project
```

脚本会复制到 `../my-project`，修改容器名前缀、数据库名和前端标题，并初始化新的 Git 仓库；依赖、环境变量和 `volumes/` 数据不会被复制。

## 生产部署

```bash
cp docker/.env.example docker/.env
# 编辑 docker/.env，设置 MySQL、Redis 密码
# 按 docker/README.md 准备 SSL 证书
./deploy.sh
```

生产部署的完整说明见 [docker/README.md](docker/README.md)。

## 开发约定

写代码前先阅读 [SKILL.md](SKILL.md)。新业务模块的常用流程是：建表 → 使用后台“代码生成”功能生成前后端代码 → 按需求微调。
