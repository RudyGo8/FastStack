# FastStack 部署说明

> **与仓库根文档的关系**：项目总览、快速开始、演示账号等请以 [根目录 README.md](../README.md) 为准；**本文档**侧重 Docker 部署的详细操作。

## 项目结构

```
docker/
├── backend/                # 后端服务配置
│   └── Dockerfile          # 后端 Dockerfile（依赖安装 + 代码复制，配合根 .dockerignore）
├── nginx/                  # Nginx 配置
│   ├── nginx.conf          # Nginx 配置文件
│   ├── ssl/                # SSL 证书目录（放置 server.key / server.pem，.gitignore 已排除）
│   ├── web/                # Web 前端静态文件（构建后手动同步 dist/）
│   └── app/ + docs/        # 移动端 H5 / 文档站点（按需启用）
├── compose.dev.yaml        # 开发环境基础设施（PostgreSQL/Redis，由根 run.sh 调用）
├── docker-compose.yaml     # 生产全栈编排（postgres / redis / backend / nginx）
├── volumes/                # 数据目录（.gitignore 已排除）
│   ├── dev/                # 开发数据：postgres/ redis/（以及按需的 mysql/ milvus/）
│   └── prod/               # 生产数据根目录（DATA_DIR）：postgres/ redis/ uploads/ logs/
├── .env                    # 生产环境变量（.gitignore 已排除）
├── .env.example            # 环境变量示例文件
└── README.md               # 本文档
```

> 数据默认落在 `docker/volumes/`。生产环境建议在 `docker/.env` 里把 `DATA_DIR` 改成仓库外的绝对路径（如 `/data/faststack/prod`），与发布文件彻底隔离。

## 部署准备

### 系统依赖

- Docker (>= 20.10)
- Docker Compose (v2，Docker 内置的 `docker compose` 命令)
- 如需构建前端：Node.js (>= 18) 和 npm / pnpm

### 环境配置

1. **配置环境变量**

   ```bash
   cp docker/.env.example docker/.env
   chmod 600 docker/.env  # 限制权限，防止其他用户读取密码
   ```

   主要配置项：

   | 变量 | 必填 | 默认值 | 说明 |
   |------|------|--------|------|
   | `DATA_DIR` | 否 | `./volumes/prod` | 生产数据根目录（数据库/Redis/上传/日志） |
   | `DATABASE_USER` | 是 | - | PostgreSQL 用户 |
   | `DATABASE_PASSWORD` | 是 | - | PostgreSQL 密码 |
   | `DATABASE_NAME` | 否 | `faststack` | 数据库名 |
   | `DATABASE_PORT` | 否 | `5432` | 数据库宿主机端口（仅绑定 127.0.0.1） |
   | `VECTOR_STORE_ENABLE` | 否 | `false` | 是否启用 pgvector 向量检索 |
   | `REDIS_PASSWORD` | 是 | - | Redis 密码 |
   | `BACKEND_PORT` | 否 | `8001` | 后端服务宿主机端口 |
   | `HTTP_PORT` | 否 | `80` | HTTP 宿主机端口 |
   | `HTTPS_PORT` | 否 | `443` | HTTPS 宿主机端口 |
   | `DEPLOY_ENV` | 否 | `prod` | 部署环境（dev/prod） |
   | `BACKEND_IMAGE_TAG` | 否 | `0.1.0` | 后端镜像标签 |

   > 仍使用 MySQL 的存量项目：`docker compose --profile legacy-mysql up -d`，并在 `backend/env/.env.prod` 里把 `DATABASE_TYPE` 设为 `mysql`。

2. **SSL 证书配置**（可选，但生产环境必须）

   ```bash
   # 自签名证书（测试用）：
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout docker/nginx/ssl/server.key \
     -out docker/nginx/ssl/server.pem \
     -subj "/CN=service.faststack.com"

   # 生产环境请使用正规 CA 签发的证书
   ```

## 部署方式

### 方式一：使用部署脚本（推荐）

在项目根目录执行：

```bash
./deploy.sh
```

脚本会自动执行：加载环境变量 → 检查依赖和目录 → 构建镜像 → 重建容器 → 验证服务 → 输出日志 → 清理构建缓存。代码需要提前上传或拉取到服务器，脚本本身不会更新代码。

**命令选项**

| 命令 | 说明 |
|------|------|
| `./deploy.sh` | 完整部署（检查、构建、启动和验证） |
| `./deploy.sh start` | 启动所有容器 |
| `./deploy.sh stop` | 停止所有容器 |
| `./deploy.sh restart` | 重启所有容器 |
| `./deploy.sh logs` | 查看所有容器日志 |
| `./deploy.sh verify` | 验证部署状态 |
| `./deploy.sh clean` | 清理旧镜像和构建缓存 |

### 方式二：手动操作

```bash
cd docker

# 启动所有服务
docker compose --env-file .env up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f [service_name]

# 停止服务
docker compose down

# 仅重建某个服务
docker compose up -d --no-deps --build [service_name]
```

## 访问信息

部署完成后，可以通过以下地址访问：

| 服务 | 地址 |
|------|------|
| Web 前端 | `https://your-domain/web` |
| API | `https://your-domain/api/v1/...` |
| 官网 | `https://your-domain/`（需要先放置 docs 构建产物） |
| 移动端 H5 | `https://your-domain/app`（需要先放置 app 构建产物） |
| 后台登录 | 默认账号 `super`、`admin`、`user`，密码均为 `123456` |

> `docker-compose.yaml` 已挂载 Web、App 和 Docs 静态目录，但部署脚本不负责构建前端；对应目录没有构建产物时页面不可用。

## 容器资源限制

| 服务 | CPU 限制 | 内存限制 | 内存预留 |
|------|----------|----------|----------|
| PostgreSQL | 无限制 | 1 GB | 256 MB |
| Redis | 无限制 | 512 MB | 128 MB |
| Backend | 1 核 | 1 GB | 256 MB |
| Nginx | 0.5 核 | 256 MB | 64 MB |

如需调整，修改 `docker-compose.yaml` 中对应服务的 `deploy.resources` 字段。

## 日志管理

```bash
# 查看所有容器日志
./deploy.sh logs

# 查看实时日志
cd docker
docker compose logs -f [服务名]

# 服务名：postgres, redis, backend, nginx
```

各容器的日志会被 Docker 自动轮转，限制为每个容器最多保留 3 个日志文件，每个最大 10MB。可在 `docker-compose.yaml` 中调整 `logging` 配置。

## 前端构建

部署脚本不会自动构建前端。发布 Web 前端前，在仓库根目录执行：

```bash
cd frontend/web
pnpm install
pnpm build:prod
mkdir -p ../../docker/nginx/web/dist
rsync -a --delete dist/ ../../docker/nginx/web/dist/
```

然后回到仓库根目录执行 `./deploy.sh`。

## 生产部署建议

1. **保留上传目录挂载**：`backend` 的 `static/upload` 用于持久化用户上传文件，不要随意移除
2. **使用正规 SSL 证书**：将 CA 签发的证书替换 `nginx/ssl/` 下的文件
3. **修改域名**：在 `nginx/nginx.conf` 中修改 `server_name`
4. **关闭调试**：确保 `.env` 中 `DEPLOY_ENV=prod`
5. **限制数据库端口**：数据库与 Redis 的 `ports` 默认只绑定 `127.0.0.1`，不要改成对公网开放

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 环境变量文件不存在 | 部署脚本会自动从 `.env.example` 创建，或手动 `cp docker/.env.example docker/.env` |
| 前端构建失败 | 建议在本地构建前端，将 `dist` 目录复制到 `docker/nginx/web/` 目录 |
| 容器启动失败 | `cd docker && docker compose logs [服务名]` 查看具体错误 |
| 数据库连接失败 | 确保 `.env` 中 `DATABASE_*` 正确，`postgres` 容器健康 |
| 端口冲突 | 修改 `.env` 中的端口配置，重新部署 |
| PostgreSQL 数据目录权限问题 | 数据目录属主必须是容器内 postgres 用户（UID 999），不要用宿主机用户改属主 |
| 后端健康检查失败 | 确保 postgres 和 redis 容器已就绪，查看后端日志：`docker compose logs backend` |

## 安全建议

1. **修改默认密码**：部署后请修改 `.env` 中的密码
2. **保护 `.env` 文件**：已加入 `.gitignore`，请勿手动提交
3. **使用正规 SSL 证书**：生产中不要使用自签名证书
4. **限制端口访问**：通过防火墙只开放 80/443 端口
5. **及时更新**：定期执行部署脚本获取最新版本

## 版本更新

先通过 Git、scp、FTP 或面板把新代码更新到服务器，再执行：

```bash
./deploy.sh    # 构建新镜像 → 重建容器 → 验证服务
```
