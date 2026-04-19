SHELL := /bin/bash

PY := backend/.venv/bin/python
CASE ?= case1

.PHONY: help dev seed seed-all cases reset smoke model-pull deps fixtures seed-hiring seed-hiring-all smoke-hiring hiring-fixtures

help:
	@echo "Helix / Recourse — make targets"
	@echo ""
	@echo "  make dev                 Start all four services (single window)"
	@echo "  make seed                Seed LenderCo with case1 (Priya Sharma)"
	@echo "  make seed CASE=case2     Seed a specific case (case1..case5)"
	@echo "  make seed-all            Seed every case under scripts/seed/loans/cases"
	@echo "  make cases               List available demo cases"
	@echo "  make fixtures            Regenerate every demo PDF from spec"
	@echo "  make reset               Wipe both DBs and uploads"
	@echo "  make smoke               Run end-to-end round-trip smoke test"
	@echo "  make model-pull          Pull glm-ocr:bf16 via Ollama (idempotent)"
	@echo "  make deps                Install frontend and backend dependencies"

dev:
	$(PY) scripts/dev.py

seed:
	$(PY) scripts/seed.py $(CASE)

seed-all:
	$(PY) scripts/seed.py --all

cases:
	@ls scripts/seed/loans/cases | grep -v '^_' | grep -v '\.py$$' | grep -v '__'
	@echo ""
	@echo "Each case directory contains:"
	@echo "  intake/         documents auto-uploaded at seed time"
	@echo "  evidence/       clean docs to upload during contest (Shield: accepted)"
	@echo "  adversarial/    designed to fail Shield checks (great for demos)"
	@echo "  case.json       applicant + features + catalogs"

fixtures:
	$(PY) -m scripts.seed.loans.cases.build_all

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

seed-hiring:
	$(PY) scripts/seed_hiring.py $(CASE)

seed-hiring-all:
	$(PY) scripts/seed_hiring.py --all

smoke-hiring:
	$(PY) scripts/smoke_hiring.py

hiring-fixtures:
	$(PY) -m scripts.seed.hiring.cases.build_all
