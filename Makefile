.PHONY: dev down test migrate api-shell web-shell logs

dev:
	docker compose up -d postgres redis minio
	pnpm install
	pnpm -r --parallel dev

down:
	docker compose down

test:
	cd apps/api && pytest
	cd apps/web && pnpm test

migrate:
	cd apps/api && alembic upgrade head

api-shell:
	cd apps/api && python

web-shell:
	cd apps/web && pnpm exec tsc --noEmit

logs:
	docker compose logs -f
