# 🧪 Guia Rápido de Testes

## Execução Rápida

### Windows PowerShell
```powershell
# Ativar ambiente virtual
.\env\Scripts\activate

# Executar todos os testes
pytest tests/ -v

# Executar testes específicos
.\run_tests.ps1 -Type etl      # Apenas ETL
.\run_tests.ps1 -Type rag      # Apenas RAG
.\run_tests.ps1 -Coverage      # Com cobertura
```

### Linux/Mac
```bash
# Ativar ambiente virtual
source env/bin/activate

# Executar todos os testes
pytest tests/ -v

# Executar testes específicos
python run_tests.py --etl      # Apenas ETL
python run_tests.py --rag      # Apenas RAG
python run_tests.py --coverage # Com cobertura
```

## Exemplos de Saída

### ✅ Testes Passando
```
tests\test_etl_validation.py::test_invalid_launch_date_quarantine PASSED [7%]
tests\test_etl_validation.py::test_incomplete_dimensions_rejected PASSED [15%]
...
========== 33 passed in 29.80s ==========
```

### ⏭️ Testes Pulados (API não rodando)
```
tests\test_rag_queries.py::test_temperature_query SKIPPED (API não disponível)
```

### ❌ Teste Falhando
```
tests\test_etl_validation.py::test_example FAILED
AssertionError: assert False
```

## Comandos Úteis

```bash
# Ver lista de testes sem executar
pytest --collect-only

# Executar último teste que falhou
pytest --lf

# Executar em paralelo (mais rápido)
pytest -n auto

# Modo verboso com detalhes
pytest -vv

# Parar no primeiro erro
pytest -x

# Executar teste específico
pytest tests/test_etl_validation.py::test_invalid_launch_date_quarantine

# Ver prints durante execução
pytest -s

# Gerar relatório HTML
pytest --html=report.html
```

## Troubleshooting

### Erro: "pytest: command not found"
```bash
pip install pytest pytest-cov pytest-xdist
```

### Erro: "API não disponível"
```bash
# Terminal 1: Iniciar API
uvicorn src.rag.api:app --reload --port 8001

# Terminal 2: Executar testes
pytest tests/test_rag_queries.py -v
```

### Erro: "Índice FAISS não encontrado"
```bash
python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf
```

### Erro: "ImportError: cannot import name..."
```bash
# Reinstalar dependências
pip install -r requirements.txt

# Verificar PYTHONPATH
echo $env:PYTHONPATH  # Windows
echo $PYTHONPATH      # Linux/Mac
```

## Ver Cobertura

```bash
# Gerar relatório de cobertura
pytest --cov=src --cov-report=html

# Abrir relatório no navegador
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## Marcadores (Markers)

```bash
# Apenas smoke tests
pytest -m smoke

# Apenas integração
pytest -m integration

# Apenas E2E
pytest -m e2e

# Excluir E2E
pytest -m "not e2e"

# Excluir lentos
pytest -m "not slow"
```

## Estrutura de Arquivos

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── pytest.ini               # Configuração pytest
├── test_etl_validation.py   # 13 testes ETL
├── test_rag_queries.py      # 13 testes RAG
├── test_integration.py      # 7 testes integração
├── fixtures/                # Dados de teste
│   ├── products_valid.csv
│   ├── products_invalid.csv
│   └── vendors_valid.jsonl
└── TEST_SUMMARY.md          # Resumo dos resultados
```

## Status Atual

✅ **33 testes implementados**
✅ **100% passando**
✅ **ETL, RAG e Integração cobertos**

---

Para mais detalhes, veja `tests/README.md` e `tests/TEST_SUMMARY.md`.
