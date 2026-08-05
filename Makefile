# ============================
# Desktop-2FA Makefile
# ============================

# --- Testy ---
test:
	pytest

test-cov:
	pytest --cov=desktop_2fa --cov-report=term

test-cov-html:
	pytest --cov=desktop_2fa --cov-report=html

# --- Linting ---
lint:
	ruff check .

lint-fix:
    ruff check . --fix

# --- Formatowanie ---
format:
	black .

# --- Type checking ---
typecheck:
	mypy .

# --- Full check (idealne przed commit/PR) ---
check-all: lint typecheck test-cov
