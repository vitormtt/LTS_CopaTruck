.PHONY: venv install run test clean help

PYTHON ?= python3
VENV ?= .venv

ifeq ($(OS),Windows_NT)
    BIN := $(VENV)/Scripts
    PY := python
else
    BIN := $(VENV)/bin
    PY := $(PYTHON)
endif

help:
	@echo "LTS Perez — Comandos disponiveis:"
	@echo "  make venv     - Cria o ambiente virtual (.venv)"
	@echo "  make install  - Instala dependencias do requirements.txt"
	@echo "  make run      - Executa o simulador Streamlit (app.py)"
	@echo "  make test     - Roda a suite de testes automatizados"
	@echo "  make clean    - Remove ambiente virtual e caches Python"

venv:
	$(PY) -m venv $(VENV)
	@echo "Ambiente virtual criado em $(VENV)."

install: venv
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	@echo "Dependencias instaladas com sucesso."

run:
	$(BIN)/streamlit run app.py

test:
	$(BIN)/pytest

clean:
	rm -rf $(VENV)
	rm -rf build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Limpeza concluida."
