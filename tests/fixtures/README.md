# Test Fixtures

Este diretório contém arquivos de dados para testes.

## Arquivos

### products_valid.csv
Dados válidos de produtos para testes positivos.

### products_invalid.csv
Dados inválidos de produtos para testes de validação:
- product_id 999: Data inválida (2024-13-45)
- product_id 998: Dimensões incompletas (90x60x)
- product_id 997: Preço negativo
- product_id 996: Preço não-numérico
- product_id 995: SKU vazio

### vendors_valid.jsonl
Dados válidos de vendors em formato JSONL.

### sample_manual.pdf
PDF de exemplo para testes do sistema RAG.
*Nota: Copie um PDF técnico real aqui para testes completos.*

## Uso

Os arquivos são automaticamente carregados pelas fixtures do pytest definidas em `conftest.py`.

```python
def test_my_feature(valid_product_data):
    # valid_product_data é um DataFrame carregado de products_valid.csv
    assert len(valid_product_data) > 0
```
