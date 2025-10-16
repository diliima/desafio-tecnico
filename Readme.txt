# 🚀 Desafio ETL e RAG - Pipeline de Dados e Recuperação Aumentada

Sistema completo de ETL (Extract, Transform, Load) e RAG (Retrieval-Augmented Generation) para processamento de documentos PDF e consultas inteligentes.

## 📋 Índice

- [Características](#-características)
- [Stack Tecnológica](#️-stack-tecnológica)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API Endpoints](#-api-endpoints)
- [Testes](#-testes)
- [Qualidade de Código](#-qualidade-de-código)
- [Troubleshooting](#-troubleshooting)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

## ✨ Características

- **Pipeline ETL**: Extração, transformação e carregamento de dados de PDFs
- **Armazenamento Otimizado**: Dados salvos em formato Parquet para alta performance
- **RAG System**: Sistema de recuperação aumentada com embeddings semânticos
- **API REST**: Interface FastAPI para consultas e operações
- **Validação de Dados**: Schema validation com Pydantic e Pandera
- **Observabilidade**: Logs estruturados e métricas de performance
- **Qualidade**: Code linting, formatting e type checking

## 🛠️ Stack Tecnológica

### Core
- **Python**: 3.11+
- **FastAPI**: Framework web moderno e performático
- **Uvicorn**: ASGI server de alta performance

### Processamento de Dados
- **Polars**: DataFrames de alta performance
- **Pandas**: Manipulação de dados tradicional
- **PyArrow**: Formato Parquet e interoperabilidade

### Validação
- **Pydantic**: Validação de dados e settings
- **Pandera**: Validação de DataFrames

### RAG & Embeddings
- **ChromaDB**: Vector database para embeddings
- **Sentence-Transformers**: Modelos de embeddings
- **FAISS**: Busca de similaridade vetorial

### Qualidade de Código
- **Ruff**: Linter extremamente rápido
- **Black**: Code formatter
- **MyPy**: Type checker
- **Pytest**: Framework de testes

## 📦 Pré-requisitos

- Python 3.11 ou superior
- pip (gerenciador de pacotes Python)
- PowerShell (Windows) ou Bash (Linux/Mac)
- Git

## 🔧 Instalação

### Windows (PowerShell)

```powershell
# 1. Clone o repositório
git clone https://github.com/seu-usuario/desafio-etl-rag.git
cd desafio-etl-rag

# 2. Execute o setup (cria venv e instala dependências)
.\scripts\setup.ps1

# 3. Ative o ambiente virtual
.\venv\Scripts\Activate.ps1

# 4. Configure as variáveis de ambiente
copy .env.example .env
# Edite o arquivo .env com suas configurações

Linux/Mac (Bash)

# 1. Clone o repositório
git clone https://github.com/seu-usuario/desafio-etl-rag.git
cd desafio-etl-rag

# 2. Execute o setup
make setup

# 3. Ative o ambiente virtual
source venv/bin/activate

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

🚀 Uso
Executar Pipeline ETL
O pipeline ETL processa documentos PDF e gera arquivos Parquet otimizados.

Windows:
.\scripts\run-etl.ps1

Linux/Mac:
make run-etl

Diretamente:
python src/etl/main.py

Executar API RAG
Inicia a API REST em http://localhost:8000

Windows:
.\scripts\run-rag.ps1

Linux/Mac:
make run-rag

Diretamente:
uvicorn src.rag.api:app --host 0.0.0.0 --port 8000 --reload

Acesse a documentação interativa em: http://localhost:8000/docs

desafio-etl-rag/
├── src/
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── main.py              # Pipeline ETL principal
│   │   ├── extractors.py        # Extração de dados
│   │   ├── transformers.py      # Transformações
│   │   └── loaders.py           # Carregamento de dados
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── api.py               # FastAPI endpoints
│   │   ├── embeddings.py        # Geração de embeddings
│   │   ├── retriever.py         # Sistema de recuperação
│   │   └── models.py            # Modelos Pydantic
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configurações gerais
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Sistema de logs
│       └── validators.py        # Validadores customizados
├── tests/
│   ├── test_etl.py
│   ├── test_rag.py
│   └── test_api.py
├── data/
│   ├── raw/                     # PDFs originais
│   ├── processed/               # Parquets processados
│   └── chroma_db/               # Vector database
├── scripts/
│   ├── setup.ps1
│   ├── run-etl.ps1
│   ├── run-rag.ps1
│   ├── test.ps1
│   └── lint.ps1
├── .env.example                 # Template de configuração
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml              # Configuração de ferramentas
├── Makefile                    # Comandos Linux/Mac
├── Dockerfile                  # Container Docker (opcional)
└── README.md
