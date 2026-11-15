#!/usr/bin/env bash
set -euo pipefail

echo "Starting ShopAgent v2 stack..."
docker compose -f docker-compose.dev.yml up -d --build

echo "Applying database migrations..."
docker compose -f docker-compose.dev.yml exec -T app alembic upgrade head

echo "Seeding deterministic demo data..."
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd seed-shop

echo "Syncing after-sales policy knowledge base..."
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd rag-ingest \
  /app/data/after_sales_policies \
  --collection after_sales_policies \
  --recursive

echo
echo "ShopAgent is ready: http://localhost:3000/shop"
echo "API docs:         http://localhost:8000/docs"
echo "Flower:           http://localhost:5555"
