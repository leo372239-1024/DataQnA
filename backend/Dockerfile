# DataQnA 后端镜像：Python 3.13 + uv，启动时自动 seed + uvicorn
FROM python:3.13-slim

# 安装 uv（经 PyPI，避免依赖 ghcr.io；版本与本地锁定一致，保证 lockfile 兼容）
RUN pip install --no-cache-dir "uv==0.11.19"

WORKDIR /app

# 先装依赖（利用 Docker 层缓存：仅 pyproject/uv.lock 变化时重建）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 拷贝源码
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

# 启动：建表 + 灌种子数据（幂等）→ 启动 API（依赖 postgres/redis 已由 compose healthcheck 保证就绪）
# 用 --no-sync 复用构建期 uv sync --no-dev 已装的 prod 环境，避免运行时重新下载 dev 依赖（mypy/ruff 等）
CMD ["sh", "-c", "uv run --no-sync python -m app.seed && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000"]
