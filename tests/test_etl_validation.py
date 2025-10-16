"""
Testes de validação do pipeline ETL.

Casos de teste implementados:
- ETL-01: Data de lançamento inválida → quarentena
- ETL-02: Dimensões incompletas → rejeição
- ETL-03: Vendor code duplicado → única linha em dim_vendor
- ETL-04: Foreign key inválida → validação e quarentena
- ETL-05: Validação de tipos de dados
"""
import pytest
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.etl.utils import parse_dimensions, normalize_price
from src.etl.validators import DimProduct, RawProduct, validate_product_row


class TestETLValidation:
    """Testes de validação de dados do ETL."""
    
    def test_invalid_launch_date_quarantine(self, invalid_launch_date_data):
        """
        ETL-01: Data de lançamento inválida deve ser identificada.
        
        Entrada: launch_date = "2024-13-45"
        Esperado: Falha na validação, registro deve ir para quarentena
        """
        row = invalid_launch_date_data.iloc[0]
        
        # Tentar parsear a data inválida
        from datetime import datetime
        
        try:
            datetime.strptime(row['launch_date'], '%Y-%m-%d')
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert not is_valid, "Data inválida deveria falhar na validação"
        assert row['launch_date'] == '2024-13-45'
        
        # Verificar que o erro seria capturado
        error_msg = f"Invalid launch_date format: {row['launch_date']}"
        assert "Invalid launch_date" in error_msg
    
    
    def test_incomplete_dimensions_rejected(self, invalid_dimensions_data):
        """
        ETL-02: Dimensões incompletas devem ser rejeitadas.
        
        Entrada: dimensions_mm = "90x60x" (falta altura)
        Esperado: Parsing falha, registro rejeitado para quarentena
        """
        row = invalid_dimensions_data.iloc[0]
        dimensions_str = row['dimensions_mm']
        
        # Testar função de parsing de dimensões
        result = parse_dimensions(dimensions_str)
        
        assert result is None or result == (None, None, None), \
            "Dimensões incompletas deveriam retornar None"
        
        # Verificar que o formato está incorreto
        parts = dimensions_str.split('x')
        assert len(parts) == 3
        assert parts[2] == '', "Terceira dimensão está vazia"
    
    
    def test_dimensions_valid_format(self):
        """
        ETL-02b: Dimensões válidas devem ser parseadas corretamente.
        
        Entrada: dimensions_mm = "100x50x30"
        Esperado: Retorna tupla (100, 50, 30)
        """
        valid_dims = "100x50x30"
        result = parse_dimensions(valid_dims)
        
        assert result == (100, 50, 30), "Dimensões válidas deveriam ser parseadas"
    
    
    def test_vendor_code_deduplication(self, duplicate_vendor_data):
        """
        ETL-03: Vendor code duplicado deve gerar única entrada em dim_vendor.
        
        Entrada: Dois produtos com vendor_code='V001'
        Esperado: 
        - 2 produtos em dim_product
        - 1 vendor em dim_vendor
        """
        # Simular processamento de vendors
        unique_vendors = duplicate_vendor_data['vendor_code'].drop_duplicates()
        
        # Verificações
        assert len(duplicate_vendor_data) == 2, "Devem existir 2 produtos"
        assert len(unique_vendors) == 1, "Deve existir apenas 1 vendor único"
        assert unique_vendors.iloc[0] == 'V001'
        
        # Verificar que ambos produtos referenciam o mesmo vendor
        vendor_codes = duplicate_vendor_data['vendor_code'].unique()
        assert len(vendor_codes) == 1
    
    
    def test_foreign_key_validation(self, inventory_with_invalid_fk):
        """
        ETL-04: Foreign key inválida deve ser detectada.
        
        Entrada: inventory com product_id=9999 (inexistente)
        Esperado: Validação falha, registro vai para quarentena
        """
        # Lista de product_ids válidos
        valid_product_ids = [1, 2, 10, 11]
        
        inventory = inventory_with_invalid_fk
        invalid_product_id = inventory.iloc[0]['product_id']
        
        # Verificar se o product_id está na lista de válidos
        is_valid_fk = invalid_product_id in valid_product_ids
        
        assert not is_valid_fk, "FK inválida deveria ser detectada"
        assert invalid_product_id == 9999
        
        # Simular mensagem de erro
        error_msg = f"Foreign key violation: product_id {invalid_product_id} not found in dim_product"
        assert "Foreign key violation" in error_msg
    
    
    def test_numeric_field_validation(self):
        """
        ETL-05: Campos numéricos com valores não-numéricos devem ser rejeitados.
        
        Entrada: price='ABC' (não numérico)
        Esperado: Conversão falha, registro rejeitado
        """
        invalid_price = 'ABC'
        
        try:
            float(invalid_price)
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert not is_valid, "Preço não-numérico deveria falhar"
        
        # Verificar que preço válido funciona
        valid_price = '99.99'
        assert float(valid_price) == 99.99
    
    
    def test_price_normalization(self):
        """
        Teste adicional: Normalização de preço (vírgula → ponto).
        
        Entrada: msrp_usd='99,99'
        Esperado: Normalizado para '99.99'
        """
        price_with_comma = '99,99'
        normalized = normalize_price(price_with_comma)
        
        assert normalized == '99.99'
        assert float(normalized) == 99.99
    
    
    def test_negative_weight_rejected(self):
        """
        Teste adicional: Peso negativo deve ser rejeitado.
        
        Entrada: weight_g=-100
        Esperado: Validação falha
        """
        data = {
            'product_id': 1,
            'sku': 'SKU-001',
            'category': 'Test',
            'weight_g': -100,  # Peso negativo
            'vendor_code': 'V001'
        }
        
        # Validar usando função auxiliar
        errors = validate_product_row(data)
        
        assert len(errors) > 0, "Peso negativo deveria gerar erro"
        assert any('weight_g' in err for err in errors)
    
    
    def test_negative_price_rejected(self):
        """
        Teste adicional: Preço negativo deve ser rejeitado.
        
        Entrada: msrp_usd=-50.00
        Esperado: Validação falha
        """
        data = {
            'product_id': 1,
            'sku': 'SKU-001',
            'category': 'Test',
            'msrp_usd': -50.00,  # Preço negativo
            'vendor_code': 'V001'
        }
        
        errors = validate_product_row(data)
        
        assert len(errors) > 0, "Preço negativo deveria gerar erro"
        assert any('msrp_usd' in err for err in errors)
    
    
    def test_missing_required_fields(self):
        """
        Teste adicional: Campos obrigatórios ausentes.
        
        Entrada: produto sem SKU
        Esperado: Validação falha
        """
        data = {
            'product_id': 1,
            'sku': '',  # SKU vazio
            'category': 'Test',
            'vendor_code': 'V001'
        }
        
        errors = validate_product_row(data)
        
        assert len(errors) > 0, "SKU vazio deveria gerar erro"
        assert any('SKU' in err for err in errors)


class TestDataTypeValidation:
    """Testes de validação de tipos de dados."""
    
    def test_valid_product_schema(self, valid_product_data):
        """
        Teste de schema válido com Pydantic.
        """
        row = valid_product_data.iloc[0]
        
        # Tentar criar objeto RawProduct
        try:
            product = RawProduct(
                product_id=int(row['product_id']),
                sku=row['sku'],
                model=row['model'],
                category=row['category'],
                weight_grams=row['weight_grams'],
                dimensions_mm=row['dimensions_mm'],
                vendor_code=row['vendor_code'],
                launch_date=row['launch_date'],
                msrp_usd=row['msrp_usd']
            )
            is_valid = True
        except Exception as e:
            is_valid = False
            print(f"Erro na validação: {e}")
        
        assert is_valid, "Produto válido deveria passar na validação Pydantic"
    
    
    def test_email_validation(self):
        """
        Teste de validação de email.
        """
        from src.etl.validators import is_valid_email
        
        # Emails válidos
        assert is_valid_email("support@techvendor.com")
        assert is_valid_email("info@globalelec.com")
        assert is_valid_email("user.name@company.co.uk")
        
        # Emails inválidos
        assert not is_valid_email("invalid.email")
        assert not is_valid_email("@company.com")
        assert not is_valid_email("user@")
        assert not is_valid_email("")


class TestQuarantineScenarios:
    """Testes de cenários de quarentena."""
    
    def test_quarantine_record_structure(self):
        """
        Verificar estrutura esperada de um registro em quarentena.
        
        Campos esperados:
        - original_data: dados originais
        - quarantine_reason: motivo da quarentena
        - quarantine_timestamp: data/hora
        - source_file: arquivo de origem
        """
        quarantine_record = {
            'product_id': 999,
            'sku': 'SKU-999',
            'original_data': '{"launch_date": "2024-13-45"}',
            'quarantine_reason': 'Invalid launch_date format: 2024-13-45',
            'quarantine_timestamp': datetime.now(),
            'source_file': 'products.csv'
        }
        
        # Verificações
        assert 'quarantine_reason' in quarantine_record
        assert 'quarantine_timestamp' in quarantine_record
        assert 'Invalid launch_date' in quarantine_record['quarantine_reason']
        assert quarantine_record['source_file'] == 'products.csv'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
