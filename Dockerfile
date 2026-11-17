# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /workspace
COPY frontend/ ./frontend/
COPY src/ ./src/
RUN cd frontend \
    && npm install --no-audit --no-fund \
    && npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN groupadd --system --gid 10001 sita \
    && useradd --system --uid 10001 --gid sita --home-dir /nonexistent --shell /usr/sbin/nologin sita \
    && mkdir -p /data \
    && chown sita:sita /data

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir .

COPY sita.example.toml /app/sita.toml
COPY --from=frontend-build /workspace/src/tara_app/web/react-dist /tmp/react-dist
RUN python -c "import shutil; from pathlib import Path; import tara_app; shutil.copytree('/tmp/react-dist', Path(tara_app.__file__).parent / 'web' / 'react-dist', dirs_exist_ok=True); shutil.rmtree('/tmp/react-dist')"

ENV SITA_BIND_HOST=0.0.0.0 \
    SITA_ALLOWED_HOSTS=127.0.0.1:8765,localhost:8765 \
    TARA_MEMORY_DB=/data/memory.sqlite3 \
    TARA_CHAT_MEMORY_PATH=/data/chat-memory.json

USER 10001:10001
EXPOSE 8765
STOPSIGNAL SIGINT
CMD ["python", "-m", "tara_app", "--config", "/app/sita.toml", "--port", "8765"]
