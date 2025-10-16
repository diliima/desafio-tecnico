# Testes do Sistema ETL + RAG

Este diretório contém todos os testes automatizados do sistema.

## Estrutura

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── pytest.ini               # Configuração do pytest
├── test_etl_validation.py   # Testes de validação ETL
├── test_rag_queries.py      # Testes do sistema RAG
├── test_integration.py      # Testes de integração
└── fixtures/                # Dados de teste
    ├── products_invalid.csv
    ├── products_valid.csv
    └── sample_manual.pdf
```

## Casos de Teste Implementados

### ETL (test_etl_validation.py)

- **ETL-01**: Data de lançamento inválida → quarentena
- **ETL-02**: Dimensões incompletas → rejeição
- **ETL-03**: Vendor code duplicado → única linha em dim_vendor
- **ETL-04**: Foreign key inválida → validação e quarentena
- **ETL-05**: Validação de tipos de dados

### RAG (test_rag_queries.py)

- **RAG-01**: Pergunta com resposta explícita (temperatura)
- **RAG-02**: Pergunta sobre consumo de energia
- **RAG-03**: Pergunta sobre interfaces/portas
- **RAG-04**: Pergunta fora do escopo
- **RAG-05**: Smoke test do endpoint /ask

### Integração (test_integration.py)

- Testes end-to-end do pipeline completo
- Testes de consistência de dados
- Testes de performance
- Testes de tratamento de erros

## Como Executar

### Todos os testes

```bash
pytest tests/ -v
```

### Testes específicos

```bash
# Apenas testes ETL
pytest tests/test_etl_validation.py -v

# Apenas testes RAG
pytest tests/test_rag_queries.py -v

# Apenas testes de integração
pytest tests/test_integration.py -v
```

### Por marcadores

```bash
# Apenas smoke tests (rápidos)
pytest tests/ -m smoke -v

# Apenas testes de integração
pytest tests/ -m integration -v

# Apenas testes e2e
pytest tests/ -m e2e -v

# Excluir testes lentos
pytest tests/ -m "not slow" -v
```

### Com cobertura de código

```bash
# Gerar relatório de cobertura
pytest tests/ --cov=src --cov-report=html

# Ver relatório
# Abrir: htmlcov/index.html
```

### Testes paralelos (mais rápido)

```bash
# Requer: pip install pytest-xdist
pytest tests/ -n auto -v
```

## Pré-requisitos

### Para testes ETL

- Nenhum pré-requisito especial
- Testes unitários que não dependem de serviços externos

### Para testes RAG

#### Opção 1: Com API rodando

```bash
# Terminal 1: Iniciar API
uvicorn src.rag.api:app --reload --port 8001

# Terminal 2: Executar testes
pytest tests/test_rag_queries.py -v
```

#### Opção 2: Sem API (testes unitários apenas)

```bash
# Pular testes que requerem API
pytest tests/test_rag_queries.py -v -k "not api_base_url"
```

### Para testes E2E

```bash
# 1. Executar ingestão de documentos
python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf

# 2. Iniciar API
uvicorn src.rag.api:app --reload --port 8001

# 3. Executar testes E2E
pytest tests/ -m e2e -v
```

## Fixtures Disponíveis

Veja `conftest.py` para lista completa. Principais:

- `valid_product_data`: Dados válidos de produtos
- `invalid_launch_date_data`: Dados com data inválida
- `invalid_dimensions_data`: Dados com dimensões incompletas
- `duplicate_vendor_data`: Dados com vendor duplicado
- `inventory_with_invalid_fk`: Inventário com FK inválida
- `api_base_url`: URL base da API

## Criando Novos Testes

### Template de teste unitário

```python
def test_my_validation():
    """Descrição do que está sendo testado."""
    # Arrange
    data = create_test_data()
    
    # Act
    result = validate_data(data)
    
    # Assert
    assert result is not None
    assert len(result['errors']) == 0
```

### Template de teste de API

```python
def test_my_endpoint(api_base_url):
    """Teste do endpoint X."""
    try:
        response = requests.post(
            f"{api_base_url}/endpoint",
            json={"param": "value"},
            timeout=10
        )
        
        assert response.status_code == 200
        result = response.json()
        assert 'expected_field' in result
        
    except requests.exceptions.ConnectionError:
        pytest.skip("API não disponível")
```

## Métricas de Qualidade

### Cobertura de Código

- **Meta**: > 80% para ETL, > 70% para RAG
- **Verificar**: `pytest --cov=src --cov-report=term`

### Tempo de Execução

- **Testes unitários**: < 2 segundos cada
- **Testes de integração**: < 10 segundos cada
- **Suite completa**: < 2 minutos

### Taxa de Sucesso

- **Desenvolvimento**: 100%
- **CI/CD**: > 95%

## Troubleshooting

### Erro: "API não disponível"

```bash
# Iniciar a API
uvicorn src.rag.api:app --reload --port 8001
```

### Erro: "Índice FAISS não encontrado"

```bash
# Executar ingestão
python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf
```

### Erro: "Módulo não encontrado"

```bash
# Instalar dependências
pip install -r requirements.txt

# Ou instalar pytest e plugins
pip install pytest pytest-cov pytest-xdist requests
```

### Erro: "Fixtures não encontradas"

```bash
# Criar diretório de fixtures
mkdir tests/fixtures

# Copiar arquivos de teste necessários
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Contato

Para questões sobre os testes, consulte a documentação principal ou abra uma issue.
