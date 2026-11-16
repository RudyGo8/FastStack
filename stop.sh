#!/usr/bin/env bash
# FastStack 一键停止本地开发环境：前端(5180) + 后端(8001) + docker 基础设施
# 生产环境请到 docker/ 目录用 docker compose down
cd "$(dirname "$0")" || exit 1

echo "[1/2] 停止前端(5180)与后端(8001)..."
stopped=0
for port in 8001 5180; do
    pids=$(lsof -ti tcp:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null && echo "  已停止端口 $port 上的进程"
        stopped=1
    fi
done
[ "$stopped" -eq 0 ] && echo "  没有在运行的前后端进程"

echo "[2/2] 停止 docker 基础设施..."
docker compose -p faststack-dev --project-directory docker -f docker/compose.dev.yaml stop

echo ""
echo "已停止。数据保留在 docker/volumes/dev/"
echo "彻底清除: docker compose -p faststack-dev --project-directory docker -f docker/compose.dev.yaml down -v && rm -rf docker/volumes/dev"
