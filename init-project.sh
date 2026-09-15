#!/usr/bin/env bash
# SopFast 脚手架: 从当前仓库复制出一个新项目并完成改名初始化
# 用法: ./init-project.sh <新项目名>   (小写字母/数字/中划线, 如 my-crm)
# 产物: ../<新项目名>/ 已 git init(未提交); .env 等生成文件不带过去, 首次 ./run.sh 重建
set -euo pipefail

NAME="${1:?用法: ./init-project.sh <新项目名> (小写字母/数字/中划线)}"
[[ "$NAME" =~ ^[a-z][a-z0-9-]*$ ]] || { echo "错误: 项目名只能用小写字母/数字/中划线"; exit 1; }
DB_NAME="${NAME//-/_}"
SRC="$(pwd)"
DEST="$(cd .. && pwd)/$NAME"
[ "$SRC" != "$DEST" ] || { echo "错误: 请在 SopFast 仓库根目录执行"; exit 1; }
[ -e "$DEST" ] && { echo "错误: 已存在 $DEST"; exit 1; }
command -v rsync >/dev/null || { echo "错误: 缺少 rsync"; exit 1; }

echo "[1/4] 复制到 $DEST (排除 .git/依赖/生成文件/数据卷)..."
rsync -a \
    --exclude .git --exclude node_modules --exclude .venv --exclude __pycache__ \
    --exclude .pytest_cache --exclude .ruff_cache --exclude .mypy_cache --exclude dist \
    --exclude volumes --exclude 'backend/static/upload' \
    --exclude 'backend/env/.env.dev' --exclude 'backend/env/.env.prod' --exclude 'backend/env/.env.test' \
    --exclude 'frontend/web/.env' --exclude 'frontend/web/.env.development' --exclude 'frontend/web/.env.production' \
    --exclude 'docker/.env' --exclude 'docker/mysql/data' --exclude 'docker/redis/data' \
    "$SRC/" "$DEST/"

echo "[2/4] 替换标识: 容器名前缀 fva- -> $NAME-, 库名 -> $DB_NAME, 前端标题 -> $NAME ..."
sed -i "s/fva-/$NAME-/g" "$DEST/docker-compose.yaml"
sed -i "s/MYSQL_DATABASE=sopfast_mysql/MYSQL_DATABASE=$DB_NAME/" "$DEST/docker-compose.yaml"
sed -i "s/^DATABASE_NAME = .*/DATABASE_NAME = $DB_NAME/" "$DEST/backend/env/.env.example"
sed -i "s/^VITE_APP_TITLE = .*/VITE_APP_TITLE = $NAME/" \
    "$DEST/frontend/web/.env.development.example" "$DEST/frontend/web/.env.production.example"
sed -i "s/\"name\": \"sopfast\"/\"name\": \"$DB_NAME\"/" "$DEST/frontend/web/package.json"

echo "[3/4] git init..."
git -C "$DEST" init -b master -q

echo "[4/4] 完成。后续步骤:"
echo "  cd ../$NAME && ./run.sh   # 首次生成 .env.dev(含随机 SECRET_KEY, 对齐 compose 端口) 并启动"
echo "  手工项: 换 logo(frontend/web/public/logo.png)、改 README 标题和徽章"
echo "  与其他栈端口冲突时, 改 $NAME 目录下 docker-compose.yaml 的 ports"
