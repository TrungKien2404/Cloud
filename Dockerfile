FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend-react

COPY frontend-react/package*.json ./
RUN npm ci

COPY frontend-react/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./
COPY --from=frontend-build /app/frontend-react/dist ./frontend-react/dist

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV STATIC_DIR=/app/frontend-react/dist
ENV USERS_FILE=/tmp/stock_ai_users.json

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.api_service:app --host 0.0.0.0 --port ${PORT:-8000}"]
