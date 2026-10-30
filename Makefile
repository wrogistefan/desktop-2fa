# Use the project environment when available; override with make PYTHON=/path/python.
ifneq ($(wildcard .venv/Scripts/python.exe),)
PYTHON ?= .venv/Scripts/python.exe
else ifneq ($(wildcard .venv/bin/python),)
PYTHON ?= .venv/bin/python
else
PYTHON ?= python
endif

.PHONY: test test-cov test-cov-html lint lint-fix format format-check typecheck check-all

test:
	$(PYTHON) -m pytest -q

test-cov:
	$(PYTHON) -m pytest --cov=desktop_2fa --cov-report=term

test-cov-html:
	$(PYTHON) -m pytest --cov=desktop_2fa --cov-report=html

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check . --fix

format:
	$(PYTHON) -m black .

format-check:
	$(PYTHON) -m black --check .

typecheck:
	$(PYTHON) -m mypy src

check-all: lint format-check typecheck test
