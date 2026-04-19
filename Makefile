SHELL := /bin/bash

PY := backend/.venv/bin/python

.PHONY: help dev seed reset smoke model-pull deps

help:
	@echo "Helix / Recourse — make targets"
	@echo ""
	@echo "  make dev         Start all four services (single window)"
	@echo "  make seed        Seed LenderCo with the demo Priya Sharma case"
	@echo "  make reset       Wipe both DBs and uploads; re-run make seed after"
	@echo "  make smoke       Run end-to-end round-trip smoke test"
	@echo "  make model-pull  Pull glm-ocr:bf16 via Ollama (idempotent)"
	@echo "  make deps        Install frontend and backend dependencies"

dev:
	$(PY) scripts/dev.py

seed:
	$(PY) scripts/seed.py

reset:
	rm -f backend/recourse.db backend/recourse.db-wal backend/recourse.db-shm
	rm -f customer_portal/backend/lender.db customer_portal/backend/lender.db-wal customer_portal/backend/lender.db-shm
	rm -rf backend/uploads customer_portal/backend/uploads
	@echo "databases + uploads wiped."

smoke:
	$(PY) scripts/smoke.py

model-pull:
	ollama pull glm-ocr:bf16

deps:
	cd frontend && npm install
	cd customer_portal/frontend && npm install
	@echo "frontend deps installed."
	@echo "backend deps: run 'uv pip install --python backend/.venv/bin/python -r backend/requirements.txt'"
