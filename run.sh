#!/usr/bin/env bash
# FastStack 一键启动（在 WSL / Linux 里执行）
#   ./run.sh        本地开发: docker 基础设施(MySQL/Redis) + 后端 + 前端
#   ./run.sh docker 完整 docker compose 全栈（后端镜像 + Nginx）
# Ctrl+C 一并停止前后端; 基础设施用下方提示的命令单独停
cd "$(dirname "$0")" || exit 1

# ── docker compose 全栈模式 ──
if [ "${1:-}" = "docker" ]; then
    cd docker || exit 1
    [ -f .env ] || { cp .env.example .env; echo "已生成 docker/.env，请填写密码后重新执行"; exit 1; }
    docker compose up -d --build
    exit
fi

echo "============================================"
echo "  FastStack 一键启动 (dev)"
echo "============================================"

# ── 0. 首次运行生成开发配置 ──
[ -f backend/env/.env.dev ] || {
    cp backend/env/.env.example backend/env/.env.dev
    sed -i "s|^DATABASE_PORT = .*|DATABASE_PORT = 3307|; s|^DATABASE_PASSWORD = .*|DATABASE_PASSWORD = 123456|; s|^REDIS_PORT = .*|REDIS_PORT = 6380|; s|^REDIS_PASSWORD = .*|REDIS_PASSWORD = ''|; s|^SECRET_KEY = .*|SECRET_KEY = $(openssl rand -hex 32)|" backend/env/.env.dev
    echo "已生成 backend/env/.env.dev（MySQL 3307/123456，Redis 6380 无密码，对齐 docker-compose.yaml）"
}
[ -f frontend/web/.env.development ] || cp frontend/web/.env.development.example frontend/web/.env.development

echo "[1/3] 启动基础设施 (MySQL:3307 / Redis:6380 / Milvus:19531)..."
docker compose up -d || exit 1

echo "等待 MySQL 就绪（首次初始化约 30s）..."
for _ in $(seq 1 60); do
    [ "$(docker compose ps mysql --format '{{.Health}}' 2>/dev/null)" = healthy ] && break
    sleep 1
done

echo "[2/3] 启动后端 (端口8001, dev 自动热重载)..."
(cd backend && uv sync --quiet) || exit 1
uv run --directory backend main.py run --env=dev &
BACK_PID=$!

echo "[3/3] 启动前端 (Vite)..."
[ -d frontend/web/node_modules ] || (cd frontend/web && pnpm install)
pnpm --dir frontend/web run dev &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null' EXIT
echo ""
echo "全部已启动: 后端 http://127.0.0.1:8001/docs | 前端 http://127.0.0.1:5180 (admin/123456) | Attu http://localhost:8082"
echo "停止基础设施: docker compose stop"
echo "Ctrl+C 停止前后端"
wait
