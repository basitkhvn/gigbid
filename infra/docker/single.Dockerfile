# Single-container deployment (free hosts): FastAPI serves the static UI; MCP servers run in-process; SQLite state on a volume.
FROM node:22-slim AS web
WORKDIR /web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
ENV STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app WEB_DIST=/app/web_out GIGBID_STATE_DIR=/state MODEL_PROFILE=open GIGSIM_INPROCESS=1
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir .
COPY . .
COPY --from=web /web/out /app/web_out
ENV FASTEMBED_CACHE_PATH=/app/.fastembed GIGBID_WARM=0
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5'); from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2')"
# bake the embedding cache + download models at BUILD time (build machine has the RAM; the 512 MB runtime instance then only reads the cache)
RUN python -c "from rag.corpus import get_corpus; [get_corpus(p).plain for p in ('ml','web','data')]"
EXPOSE 8000
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
