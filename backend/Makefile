# Makefile for Veracity Backend

.PHONY: help install test test-unit test-integration test-e2e test-cov lint format clean dev

help:
	@echo "Available commands:"
	@echo "  make install         - Install dependencies"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e       - Run end-to-end tests only"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make clean          - Clean cache and temp files"
	@echo "  make dev            - Start development server"

install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-e2e:
	pytest tests/e2e/ -v -m e2e

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

test-watch:
	pytest-watch tests/ -v

lint:
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/

format:
	black app/ tests/
	isort app/ tests/

type-check:
	mypy app/ --ignore-missing-imports

security-check:
	bandit -r app/
	safety check

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

migrate-rollback:
	alembic downgrade -1

db-reset:
	alembic downgrade base
	alembic upgrade head