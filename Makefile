.PHONY: help install lint test test-unit test-integration test-prop up down demo clean

PYTHON ?= py -3.13

help:
	@echo "InvenIQ Orchestration Commands:"
	@echo "  make install        Install backend and pipeline dependencies"
	@echo "  make lint           Run code formatting and lint checks"
	@echo "  make test           Run all unit, integration, and property tests"
	@echo "  make test-unit      Run unit test suite"
	@echo "  make test-prop      Run property-based optimizer tests"
	@echo "  make generate-data  Run deterministic synthetic data generator"
	@echo "  make ingest         Run validation and ingest into Parquet Lakehouse"
	@echo "  make web-install    Install frontend dependencies (npm install in web/)"
	@echo "  make web-build      Build Next.js production bundle"
	@echo "  make web-dev        Start Next.js local development server (port 3000)"
	@echo "  make demo           Full demo seed: generate, validate, ingest, and sample run"
	@echo "  make up             Start local docker stack (Postgres, Redis, MinIO, API, Worker)"
	@echo "  make down           Stop local docker stack"
	@echo "  make clean          Clean cached and intermediate files"

install:
	$(PYTHON) -m pip install -e .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .

test:
	$(PYTHON) -m pytest tests/

test-unit:
	$(PYTHON) -m pytest tests/unit/

test-integration:
	$(PYTHON) -m pytest tests/integration/

test-prop:
	$(PYTHON) -m pytest tests/property/

generate-data:
	$(PYTHON) -m inveniq_pipelines.synthetic.generator

ingest:
	$(PYTHON) -m inveniq_pipelines.ingestion.loader

demo: generate-data ingest
	@echo "Demo data generated and ingested into Parquet Lakehouse successfully!"

web-install:
	cd web && npm install

web-build:
	cd web && npm run build

web-dev:
	cd web && npm run dev

up:
	docker compose up -d

down:
	docker compose down

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
