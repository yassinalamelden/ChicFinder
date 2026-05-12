.PHONY: dev-backend dev-frontend docker-build docker-up docker-down build-index lint

dev-backend:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd FrontEnd && npm run dev

docker-build:
	docker compose -f infrastructure/docker/docker-compose.yml build

docker-up:
	docker compose -f infrastructure/docker/docker-compose.yml up

docker-down:
	docker compose -f infrastructure/docker/docker-compose.yml down

build-index:
	python scripts/build_database.py

lint:
	ruff check api/ ai_engine/ chic_finder/ shared/ scripts/
