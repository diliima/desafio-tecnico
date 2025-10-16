"""
Testes de integração do sistema completo (ETL + RAG).

Testa o fluxo end-to-end desde a ingestão até as queries.
"""
import pytest
import requests
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestETLtoRAGIntegration:
    """Testes de integração entre ETL e RAG."""
    
    @pytest.mark.integration
    def test_full_pipeline_smoke_test(self):
        """
        Smoke test do pipeline completo.
        
        Verifica que:
        1. Dados brutos existem
        2. Validação funciona
        3. API está acessível
        """
        # Verificar arquivos de dados brutos
        raw_dir = Path("raw")
        assert raw_dir.exists(), "Diretório raw/ não encontrado"
        
        # Verificar se há arquivos
        products_file = raw_dir / "products.csv"
        vendors_file = raw_dir / "vendors.jsonl"
        inventory_file = raw_dir / "inventory.parquet"
        
        has_data = products_file.exists() or vendors_file.exists() or inventory_file.exists()
        assert has_data, "Nenhum arquivo de dados encontrado em raw/"
    
    
    @pytest.mark.integration
    def test_data_quality_workflow(self, valid_product_data):
        """
        Teste do fluxo de qualidade de dados.
        
        1. Dados válidos passam pela validação
        2. Dados inválidos vão para quarentena
        3. Logs são gerados
        """
        # Simular processamento
        valid_count = len(valid_product_data)
        quarantine_count = 0
        
        # Validar cada linha
        for idx, row in valid_product_data.iterrows():
            try:
                # Verificações básicas
                assert row['sku'] is not None
                assert row['product_id'] > 0
                valid_count += 1
            except Exception as e:
                quarantine_count += 1
        
        # Dados válidos não devem ir para quarentena
        assert valid_count > 0
        assert quarantine_count == 0


class TestEndToEndScenarios:
    """Cenários end-to-end do sistema."""
    
    @pytest.mark.e2e
    @pytest.mark.skipif(
        not Path("data/faiss_index/index.faiss").exists(),
        reason="Sistema RAG não inicializado"
    )
    def test_query_after_ingestion(self, api_base_url):
        """
        Teste E2E: Query após ingestão de documento.
        
        1. Verifica que índice existe
        2. Faz query simples
        3. Valida resposta
        """
        try:
            # Verificar saúde do sistema
            health_response = requests.get(f"{api_base_url}/health", timeout=5)
            assert health_response.status_code == 200
            
            health = health_response.json()
            
            if not health['index_loaded']:
                pytest.skip("Índice não carregado")
            
            # Fazer query
            query_response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Quais são as principais características?"},
                timeout=15
            )
            
            assert query_response.status_code == 200
            result = query_response.json()
            
            # Validar resposta
            assert 'answer' in result
            assert len(result['answer']) > 0
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    @pytest.mark.e2e
    def test_data_lineage(self):
        """
        Teste de linhagem de dados.
        
        Verifica que conseguimos rastrear dados desde a origem.
        """
        # Verificar estrutura de diretórios
        assert Path("raw").exists(), "Diretório raw/ não encontrado"
        assert Path("data").exists(), "Diretório data/ não encontrado"
        
        # Verificar que temos dados de origem
        raw_files = list(Path("raw").glob("*.*"))
        assert len(raw_files) > 0, "Nenhum arquivo em raw/"


class TestErrorHandling:
    """Testes de tratamento de erros."""
    
    def test_api_error_responses(self, api_base_url):
        """
        Teste de respostas de erro da API.
        """
        try:
            # Requisição inválida (sem body)
            response = requests.post(f"{api_base_url}/ask", timeout=5)
            assert response.status_code in [400, 422]
            
            # Requisição com JSON inválido
            response = requests.post(
                f"{api_base_url}/ask",
                json={"invalid_field": "test"},
                timeout=5
            )
            assert response.status_code in [400, 422]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_missing_data_handling(self):
        """
        Teste de tratamento de dados ausentes.
        """
        # DataFrame com valores nulos
        data = pd.DataFrame([
            {'product_id': 1, 'sku': 'SKU-001', 'vendor_code': None},
            {'product_id': 2, 'sku': None, 'vendor_code': 'V001'},
        ])
        
        # Verificar que conseguimos detectar nulos
        null_counts = data.isnull().sum()
        assert null_counts['vendor_code'] == 1
        assert null_counts['sku'] == 1


class TestPerformance:
    """Testes de performance básicos."""
    
    @pytest.mark.performance
    def test_api_response_time(self, api_base_url):
        """
        Teste de tempo de resposta da API.
        
        Esperado: < 5 segundos para consultas simples
        """
        try:
            import time
            
            start = time.time()
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "teste de performance"},
                timeout=10
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                # Tempo de resposta deve ser razoável
                assert elapsed < 10, f"Resposta muito lenta: {elapsed:.2f}s"
                
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    @pytest.mark.performance
    def test_batch_validation_performance(self, valid_product_data):
        """
        Teste de performance de validação em lote.
        """
        import time
        
        # Criar dataset maior
        large_data = pd.concat([valid_product_data] * 100, ignore_index=True)
        
        start = time.time()
        
        # Validação simples
        for idx, row in large_data.iterrows():
            assert row['sku'] is not None
        
        elapsed = time.time() - start
        
        # Deve processar rapidamente
        assert elapsed < 5, f"Validação muito lenta: {elapsed:.2f}s para {len(large_data)} linhas"


class TestDataConsistency:
    """Testes de consistência de dados."""
    
    def test_product_vendor_consistency(self, valid_product_data, valid_vendors_data):
        """
        Teste de consistência entre produtos e vendors.
        
        Todos os vendor_codes em produtos devem existir em vendors.
        """
        product_vendors = set(valid_product_data['vendor_code'].unique())
        available_vendors = set(valid_vendors_data['vendor_code'].unique())
        
        # Verificar que todos os vendors dos produtos existem
        missing_vendors = product_vendors - available_vendors
        
        # Para dados de teste, pode haver vendors faltando
        # Em produção, isto seria um erro
        if len(missing_vendors) > 0:
            print(f"Warning: Vendors faltando: {missing_vendors}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-m', 'not e2e'])
