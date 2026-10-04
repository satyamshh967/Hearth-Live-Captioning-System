.PHONY: dev test eval build run docker-build docker-up clean help

help:
	@echo "Hearth — Assistive Offline Captions"
	@echo "Commands:"
	@echo "  make dev          Start backend API and Vite web dev server"
	@echo "  make test         Run pytest unit and offline privacy tests"
	@echo "  make eval         Run ASR WER and intent evaluation harness"
	@echo "  make build        Build frontend PWA bundle"
	@echo "  make docker-build Build Docker container"
	@echo "  make docker-up    Run via docker-compose"
	@echo "  make clean        Remove cache and temporary files"

build:
	cd apps/web && npm run build

test:
	python -m pytest tests/ -v

eval:
	python eval/generate_evaluation_dataset.py
	python -u eval/run_eval.py

dev-backend:
	uvicorn services.core.api.main:app --reload --port 8000

dev-frontend:
	cd apps/web && npm run dev

dev:
	@echo "Starting Hearth dev servers..."
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals."

docker-build:
	docker build -t hearth:latest .

docker-up:
	docker-compose up -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf apps/web/dist
