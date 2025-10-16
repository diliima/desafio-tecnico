.PHONY: setup run-etl run-rag test lint clean help venv

VENV = venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip

help:
    @echo "Comandos disponíveis:"
    @echo "  make setup     - Cria venv e instala dependências"
    @echo "  make run-etl   - Executa pipeline ETL e gera Parquets"
    @echo "  make run-rag   - Sobe API em localhost:8000"
    @echo "  make test      - Executa testes com pytest"
    @echo "  make lint      - Verifica código (ruff + black + mypy)"
    @echo "  make clean     - Remove arquivos temporários e venv"

venv:
    python -m venv $(VENV)

setup: venv
    $(PIP) install --upgrade pip
    $(PIP) install -r requirements.txt
    $(PIP) install -r requirements-dev.txt
    $(PYTHON) -m pre_commit install
    @echo "✅ Setup completo! Ative o venv com: $(VENV)\Scripts\activate"

run-etl:
    $(PYTHON) src/etl/main.py

run-rag:
    $(PYTHON) -m uvicorn src.rag.api:app --host 0.0.0.0 --port 8000 --reload

test:
    $(PYTHON) -m pytest -q tests/ --cov=src --cov-report=term-missing

lint:
    $(PYTHON) -m ruff check src/ tests/
    $(PYTHON) -m black --check src/ tests/
    $(PYTHON) -m mypy src/ --ignore-missing-imports

format:
    $(PYTHON) -m ruff check --fix src/ tests/
    $(PYTHON) -m black src/ tests/

clean:
    if exist $(VENV) rmdir /s /q $(VENV)
    if exist .pytest_cache rmdir /s /q .pytest_cache
    if exist .ruff_cache rmdir /s /q .ruff_cache
    if exist htmlcov rmdir /s /q htmlcov
    if exist .coverage del /q .coverage
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
    for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"