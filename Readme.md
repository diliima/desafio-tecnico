# Sistema ETL + RAG - Alpha-X Pro

Sistema completo de ETL (Extract, Transform, Load) e RAG (Retrieval-Augmented Generation) para processamento de dados de produtos e consulta inteligente de documentação técnica.

## Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Testes](#testes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Troubleshooting](#troubleshooting)
- [Documentação Adicional](#documentação-adicional)

## Visão Geral

Este projeto implementa:

1. **Pipeline ETL**: Processa dados de produtos, vendors e inventário com validação e quarentena
2. **Sistema RAG**: API para consultas inteligentes sobre documentação técnica usando embeddings e LLM

## Características

### ETL
- Validação de dados com Pandera
- Normalização de datas inválidas
- Deduplicação de vendors
- Validação de foreign keys
- Sistema de quarentena para dados inválidos
- Exportação em Parquet particionado

### RAG
- Ingestão de PDFs técnicos
- Embeddings com Sentence Transformers
- Busca semântica com FAISS
- API REST com FastAPI
- Suporte a múltiplos LLM providers (Mock/Ollama)
- Sistema de confidence scoring

## Pré-requisitos

- **Python**: 3.11 ou superior
- **Sistema Operacional**: Windows, Linux ou macOS
- **Memória**: Mínimo 4GB RAM
- **Espaço em disco**: ~2GB para dependências e dados

## Instalação

### 1. Clone o Repositório

```bash
git clone <url-do-repositorio>
cd Desafio
```

### 2. Crie o Ambiente Virtual

**Windows (PowerShell)**:
```powershell
python -m venv env
.\env\Scripts\activate
```

**Linux/macOS**:
```bash
python3 -m venv env
source env/bin/activate
```

### 3. Instale as Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verifique a Instalação

```bash
python -c "import pandas, fastapi, sentence_transformers; print('Instalação OK')"
```

## Configuração

### 1. Arquivo `.env`

O projeto já inclui um arquivo `.env` com configurações padrão:

```env
# Database
DATABASE_URL=sqlite:///data/database.db

# ChromaDB
CHROMA_DB_PATH=data/chroma_db

# Embeddings Model
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2

# ETL Config
INPUT_PDF_PATH=data/raw/documents
OUTPUT_PARQUET_PATH=data/processed

# RAG Config
TOP_K_RESULTS=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### 2. Dados de Entrada

Certifique-se de que os seguintes arquivos existem no diretório `raw`:

- `products.csv` - Dados de produtos
- `vendors.jsonl` - Dados de fornecedores
- `inventory.parquet` - Dados de inventário

Para o sistema RAG, coloque documentos PDF em `docs`:
- `Alpha-X_Pro_Tecnico.pdf` (exemplo)

## Uso

### Pipeline ETL

#### Opção 1: Usando Python
```bash
python -m src.etl.run
```

#### Opção 2: Usando Makefile (se disponível)
```bash
make run-etl
```

**Saída esperada**:
- Dados limpos em `data/dim_product/`, `data/dim_vendor/`, `data/fact_inventory/`
- Dados em quarentena em `data/silver/_quarantine/`
- Relatório em `data/pipeline_report.json`

### Sistema RAG

#### 1. Ingestão de Documentos

```bash
python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf
```

**Saída esperada**:
```
Documento indexado com sucesso!
Índice salvo em: data/faiss_index
```

#### 2. Iniciar a API

```bash
# Com uvicorn diretamente
uvicorn src.rag.api:app --reload --port 8001

# Ou usando o módulo
python -m src.rag.api
```

**Saída esperada**:
```
Iniciando Mini-RAG API
URL: http://0.0.0.0:8001
Documentação: http://0.0.0.0:8001/docs
LLM Provider: mock
```

#### 3. Testar a API

**Via navegador**:
- Acesse: http://localhost:8001/docs (Swagger UI interativo)

**Via linha de comando**:
```bash
# Health check
curl http://localhost:8001/health

# Fazer pergunta
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual é a temperatura operacional?"}'
```

**Via script de teste**:
```bash
python test_rag.py
```

### Usando o Script de Verificação

Para diagnosticar problemas com a API:

```bash
python check_api.py
```

## Testes

### Executar Todos os Testes

**Windows PowerShell**:
```powershell
.\run_tests.ps1
```

**Linux/macOS**:
```bash
python run_tests.py
```

### Testes por Categoria

```bash
# Apenas ETL
pytest tests/test_etl_validation.py -v

# Apenas RAG
pytest tests/test_rag_queries.py -v

# Apenas Integração
pytest tests/test_integration.py -v

# Smoke tests
pytest tests/ -m smoke -v
```

### Com Cobertura de Código

```bash
pytest tests/ --cov=src --cov-report=html
```

Depois abra `htmlcov/index.html` no navegador.

### Testes Paralelos (mais rápido)

```bash
# Requer: pip install pytest-xdist
pytest tests/ -n auto -v
```

**Resultados esperados**:
- 33 testes passando
- Tempo de execução: ~29 segundos
- Cobertura: ETL + RAG + Integração

Veja mais detalhes em [`tests/README.md`](tests/README.md).

## Estrutura do Projeto

```
Desafio/
├── src/                        # Código fonte
│   ├── etl/                    # Pipeline ETL
│   │   ├── run.py              # Pipeline principal
│   │   └── utils.py            # Utilitários e validações
│   └── rag/                    # Sistema RAG
│       ├── ingest.py           # Ingestão de documentos
│       ├── retriever.py        # Recuperação e busca
│       └── api.py              # API FastAPI
├── tests/                      # Testes automatizados
│   ├── conftest.py             # Fixtures pytest
│   ├── test_etl_validation.py  # Testes ETL (13)
│   ├── test_rag_queries.py     # Testes RAG (13)
│   └── test_integration.py     # Testes integração (7)
├── raw/                        # Dados de entrada
│   ├── products.csv
│   ├── vendors.jsonl
│   └── inventory.parquet
├── docs/                       # Documentação técnica
│   └── Alpha-X_Pro_Tecnico.pdf
├── data/                       # Dados processados
│   ├── dim_product/            # Dimensão produtos
│   ├── dim_vendor/             # Dimensão vendors
│   ├── fact_inventory/         # Fato inventário
│   ├── faiss_index/            # Índice FAISS
│   └── silver/_quarantine/     # Dados em quarentena
├── requirements.txt            # Dependências Python
├── .env                        # Configurações
├── run_tests.py                # Script de testes
└── README.md                   # Este arquivo
```

## Troubleshooting

### Problema: "ModuleNotFoundError"

**Solução**:
```bash
# Reinstalar dependências
pip install -r requirements.txt

# Verificar se ambiente virtual está ativo
# Windows: .\env\Scripts\activate
# Linux/macOS: source env/bin/activate
```

### Problema: "API não disponível" nos testes

**Solução**:
```bash
# Terminal 1: Iniciar API
uvicorn src.rag.api:app --reload --port 8001

# Terminal 2: Executar testes
pytest tests/test_rag_queries.py -v
```

### Problema: "Índice FAISS não encontrado"

**Solução**:
```bash
# Executar ingestão primeiro
python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf
```

### Problema: Porta 8001 já em uso

**Solução**:
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8001 | xargs kill -9
```

### Problema: Erro ao carregar CSV

**Verificar**:
- Encoding do arquivo (UTF-8 esperado)
- Delimitador correto (vírgula)
- Aspas nos campos

**Solução**: O pipeline tem fallback para parsing manual em `src/etl/run.py`.

### Problema: Dependências conflitantes

**Solução**:
```bash
# Criar ambiente virtual limpo
rm -rf env  # ou rmdir /s env no Windows
python -m venv env
.\env\Scripts\activate  # ou source env/bin/activate
pip install -r requirements.txt
```

## Documentação Adicional

### Documentos do Projeto

- [`REPORT.md`](REPORT.md) - Relatório técnico completo
- [`tests/README.md`](tests/README.md) - Documentação de testes
- [`tests/TEST_SUMMARY.md`](tests/TEST_SUMMARY.md) - Resumo dos resultados
- [`tests/QUICK_START.md`](tests/QUICK_START.md) - Guia rápido de testes
- [`tests/SUCCESS_REPORT.md`](tests/SUCCESS_REPORT.md) - Relatório de sucesso

### APIs e Endpoints

**Documentação Interativa**: http://localhost:8001/docs

**Endpoints principais**:
- `GET /` - Informações da API
- `GET /health` - Health check
- `POST /ask` - Fazer pergunta
- `GET /search` - Buscar documentos
- `POST /ingest` - Adicionar PDF

### Configuração de IDE

**VS Code** (configuração em `.vscode/settings.json`):
- Python path configurado
- Linting com Ruff
- Formatação com Black

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Antes de submeter:

```bash
# Executar testes
pytest tests/ -v

# Verificar qualidade do código
ruff check src/ tests/
black --check src/ tests/

# Verificar tipos
mypy src/ --ignore-missing-imports
```


Para questões ou problemas:

1. Verifique a seção [Troubleshooting](#troubleshooting)
2. Consulte a [documentação de testes](tests/README.md)
3. Verifique logs em `data/pipeline_report.json`
4. Abra uma issue no repositório

---
