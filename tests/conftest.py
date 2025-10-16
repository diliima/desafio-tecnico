"""
Configurações e fixtures compartilhadas para os testes.
"""
import pytest
import os
import pandas as pd
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Diretório com dados de teste."""
    path = Path(__file__).parent / "fixtures"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture(scope="session")
def sample_pdf(test_data_dir):
    """Caminho para PDF de exemplo."""
    return test_data_dir / "sample_manual.pdf"


@pytest.fixture
def valid_product_data():
    """Dados válidos de produtos para testes."""
    return pd.DataFrame([
        {
            'product_id': 1,
            'sku': 'SKU-001',
            'model': 'Model A',
            'category': 'Electronics',
            'weight_grams': 500.0,
            'dimensions_mm': '100x50x30',
            'vendor_code': 'V001',
            'launch_date': '2024-01-15',
            'msrp_usd': '99.99'
        },
        {
            'product_id': 2,
            'sku': 'SKU-002',
            'model': 'Model B',
            'category': 'Electronics',
            'weight_grams': 750.0,
            'dimensions_mm': '150x80x40',
            'vendor_code': 'V002',
            'launch_date': '2024-03-20',
            'msrp_usd': '149.50'
        }
    ])


@pytest.fixture
def invalid_launch_date_data():
    """Dados com launch_date inválida."""
    return pd.DataFrame([
        {
            'product_id': 999,
            'sku': 'SKU-999',
            'model': 'Model Invalid',
            'category': 'Electronics',
            'weight_grams': 500.0,
            'dimensions_mm': '100x50x30',
            'vendor_code': 'V001',
            'launch_date': '2024-13-45',  # Data inválida
            'msrp_usd': '99.99'
        }
    ])


@pytest.fixture
def invalid_dimensions_data():
    """Dados com dimensions_mm incompletas."""
    return pd.DataFrame([
        {
            'product_id': 998,
            'sku': 'SKU-998',
            'model': 'Model Incomplete',
            'category': 'Electronics',
            'weight_grams': 500.0,
            'dimensions_mm': '90x60x',  # Dimensão incompleta
            'vendor_code': 'V001',
            'launch_date': '2024-01-15',
            'msrp_usd': '99.99'
        }
    ])


@pytest.fixture
def duplicate_vendor_data():
    """Dados com vendor_code duplicado."""
    return pd.DataFrame([
        {
            'product_id': 10,
            'sku': 'SKU-010',
            'vendor_code': 'V001',
            'model': 'Product A',
            'category': 'Electronics',
            'launch_date': '2024-01-01',
            'msrp_usd': '50.00'
        },
        {
            'product_id': 11,
            'sku': 'SKU-011',
            'vendor_code': 'V001',  # Mesmo vendor_code
            'model': 'Product B',
            'category': 'Electronics',
            'launch_date': '2024-02-01',
            'msrp_usd': '75.00'
        }
    ])


@pytest.fixture
def inventory_with_invalid_fk():
    """Dados de inventário com foreign key inválida."""
    return pd.DataFrame([
        {
            'product_id': 9999,  # Produto inexistente
            'warehouse': 'WH01',
            'on_hand': 100,
            'min_stock': 10,
            'last_counted_at': '2024-01-15'
        }
    ])


@pytest.fixture
def valid_vendors_data():
    """Dados válidos de vendors."""
    return pd.DataFrame([
        {
            'vendor_code': 'V001',
            'name': 'Tech Vendor Inc',
            'country': 'USA',
            'support_email': 'support@techvendor.com'
        },
        {
            'vendor_code': 'V002',
            'name': 'Global Electronics',
            'country': 'China',
            'support_email': 'info@globalelec.com'
        }
    ])


@pytest.fixture
def api_base_url():
    """URL base da API para testes."""
    return os.getenv("API_URL", "http://localhost:8001")
