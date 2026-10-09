# One container serving the API (/api) and the built website (/). Used on Railway.
FROM node:22-alpine AS site
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STORAGE_DIR=/data STATIC_DIR=/app/site
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY api api
COPY agents agents
COPY policies policies
COPY retrieval retrieval
COPY evidence evidence
COPY evaluation evaluation
COPY --from=site /app/dist /app/site
RUN mkdir -p /data
EXPOSE 8000
# HOST=:: on Railway (IPv6 + IPv4 private networking); 0.0.0.0 elsewhere.
CMD uvicorn api.server:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}
