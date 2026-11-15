$ErrorActionPreference = "Stop"

Write-Host "Starting ShopAgent v2 stack..."
docker compose -f docker-compose.dev.yml up -d --build

Write-Host "Applying database migrations..."
docker compose -f docker-compose.dev.yml exec -T app alembic upgrade head

Write-Host "Seeding deterministic demo data..."
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd seed-shop

Write-Host "Syncing after-sales policy knowledge base..."
docker compose -f docker-compose.dev.yml exec -T app shopagent_v2 cmd rag-ingest `
  /app/data/after_sales_policies `
  --collection after_sales_policies `
  --recursive

Write-Host ""
Write-Host "ShopAgent is ready: http://localhost:3000/shop"
Write-Host "API docs:         http://localhost:8000/docs"
Write-Host "Flower:           http://localhost:5555"
