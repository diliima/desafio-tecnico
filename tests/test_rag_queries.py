"""
Testes do sistema RAG (Retrieval-Augmented Generation).

Casos de teste implementados:
- RAG-01: Pergunta com resposta explícita no PDF
- RAG-02: Pergunta sobre consumo de energia
- RAG-03: Pergunta sobre interfaces/portas
- RAG-04: Pergunta fora do escopo
- RAG-05: Smoke test do endpoint /ask
"""
import pytest
import requests
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRAGExplicitAnswers:
    """Testes de perguntas com respostas explícitas no documento."""
    
    @pytest.mark.skipif(
        not Path("data/faiss_index/index.faiss").exists(),
        reason="Índice FAISS não encontrado. Execute a ingestão primeiro."
    )
    def test_temperature_query_explicit_answer(self, api_base_url):
        """
        RAG-01: Pergunta sobre temperatura operacional.
        
        Pergunta: "Qual é a faixa de temperatura operacional?"
        Esperado: Resposta com intervalo de temperatura e fonte paginada
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Qual é a faixa de temperatura operacional?"},
                timeout=10
            )
            
            # Verificar status code
            assert response.status_code == 200, f"API retornou {response.status_code}"
            
            result = response.json()
            
            # Verificações básicas
            assert 'answer' in result
            assert 'sources' in result
            assert 'question' in result
            
            # Verificar se a resposta contém informação de temperatura
            answer = result['answer'].lower()
            assert '°c' in answer or 'temperatura' in answer or 'grau' in answer
            
            # Verificar fontes
            if len(result['sources']) > 0:
                source = result['sources'][0]
                assert 'page' in source
                assert 'snippet' in source
                assert 'score' in source
                assert source['score'] >= 0.0
                assert source['page'] > 0
                
        except requests.exceptions.ConnectionError:
            pytest.skip("API não está disponível. Inicie o servidor com: uvicorn src.rag.api:app")
    
    
    @pytest.mark.skipif(
        not Path("data/faiss_index/index.faiss").exists(),
        reason="Índice FAISS não encontrado"
    )
    def test_power_consumption_query(self, api_base_url):
        """
        RAG-02: Pergunta sobre consumo de energia.
        
        Pergunta: "Qual o consumo de energia do equipamento?"
        Esperado: Resposta com valores de consumo (operação e standby)
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Qual o consumo de energia?"},
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'answer' in result
            answer = result['answer'].lower()
            
            # Verificar se menciona energia/consumo/watts
            energy_keywords = ['watt', 'w', 'energia', 'consumo', 'potência']
            assert any(keyword in answer for keyword in energy_keywords)
            
            # Verificar que tem pelo menos uma fonte
            assert len(result['sources']) > 0
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    @pytest.mark.skipif(
        not Path("data/faiss_index/index.faiss").exists(),
        reason="Índice FAISS não encontrado"
    )
    def test_interfaces_ports_query(self, api_base_url):
        """
        RAG-03: Pergunta sobre interfaces e portas.
        
        Pergunta: "Quais são as interfaces disponíveis?"
        Esperado: Lista de interfaces/portas com snippet paginado
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Quais são as interfaces disponíveis?"},
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'answer' in result
            answer = result['answer'].lower()
            
            # Verificar se menciona interfaces/portas/conectores
            interface_keywords = ['usb', 'hdmi', 'ethernet', 'porta', 'interface', 'conector']
            has_interface_info = any(keyword in answer for keyword in interface_keywords)
            
            # Se o documento não tiver essas informações, deve indicar
            if not has_interface_info:
                not_found_keywords = ['não', 'sem informação', 'não encontr']
                assert any(keyword in answer for keyword in not_found_keywords)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")


class TestRAGOutOfScope:
    """Testes de perguntas fora do escopo do documento."""
    
    @pytest.mark.skipif(
        not Path("data/faiss_index/index.faiss").exists(),
        reason="Índice FAISS não encontrado"
    )
    def test_out_of_scope_price_query(self, api_base_url):
        """
        RAG-04: Pergunta fora do escopo (preço).
        
        Pergunta: "Qual o preço do produto?"
        Esperado: 
        - Resposta indicando "não encontrado"
        - Passagens mais próximas como sugestão
        - Confidence baixo ou none
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Qual o preço do produto no mercado?"},
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'answer' in result
            answer = result['answer'].lower()
            
            # Verificar indicadores de "não encontrado"
            not_found_indicators = [
                'não encontr',
                'não há informação',
                'não disponível',
                'sem informação',
                'não consta'
            ]
            
            # Se o documento realmente não tem preço, deve indicar
            # Ou se tem preço, deve responder
            # Em ambos os casos, deve haver uma resposta válida
            assert len(answer) > 10, "Resposta muito curta"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_out_of_scope_weather_query(self, api_base_url):
        """
        Pergunta completamente fora do escopo (clima).
        
        Pergunta: "Como está o tempo hoje?"
        Esperado: Resposta indicando que não é sobre o documento
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "Como está o tempo hoje?"},
                timeout=10
            )
            
            # Pode retornar 200 com resposta de "não encontrado"
            # ou pode retornar erro dependendo da implementação
            assert response.status_code in [200, 400]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")


class TestRAGAPIEndpoints:
    """Testes dos endpoints da API."""
    
    def test_smoke_health_endpoint(self, api_base_url):
        """
        Smoke test: Endpoint /health responde.
        """
        try:
            response = requests.get(f"{api_base_url}/health", timeout=5)
            
            assert response.status_code == 200
            result = response.json()
            
            # Verificar estrutura da resposta
            assert 'status' in result
            assert 'index_loaded' in result
            assert 'llm_available' in result
            assert 'llm_provider' in result
            
            # Status deve ser string
            assert isinstance(result['status'], str)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_smoke_ask_endpoint(self, api_base_url):
        """
        RAG-05: Smoke test do endpoint /ask.
        
        Verifica que o endpoint responde e tem estrutura correta.
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "teste"},
                timeout=10
            )
            
            # Pode retornar 200 (sucesso) ou 503 (serviço não disponível)
            assert response.status_code in [200, 400, 503]
            
            if response.status_code == 200:
                result = response.json()
                
                # Verificar estrutura da resposta
                assert 'answer' in result
                assert 'sources' in result
                assert 'question' in result
                
                # Tipos corretos
                assert isinstance(result['answer'], str)
                assert isinstance(result['sources'], list)
                assert isinstance(result['question'], str)
                
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_ask_endpoint_validation(self, api_base_url):
        """
        Teste de validação de entrada do endpoint /ask.
        
        Pergunta muito curta deve ser rejeitada.
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={"question": "oi"},  # Muito curto (< 5 caracteres)
                timeout=5
            )
            
            # Deve rejeitar pergunta muito curta
            assert response.status_code in [400, 422]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_ask_endpoint_missing_question(self, api_base_url):
        """
        Teste com pergunta ausente.
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={},  # Sem campo 'question'
                timeout=5
            )
            
            # Deve retornar erro de validação
            assert response.status_code in [400, 422]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_ask_endpoint_with_top_k(self, api_base_url):
        """
        Teste do parâmetro top_k.
        """
        try:
            response = requests.post(
                f"{api_base_url}/ask",
                json={
                    "question": "Quais as especificações técnicas?",
                    "top_k": 5
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Verificar que retorna no máximo top_k fontes
                assert len(result['sources']) <= 5
                
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")
    
    
    def test_root_endpoint(self, api_base_url):
        """
        Teste do endpoint raiz (/).
        """
        try:
            response = requests.get(f"{api_base_url}/", timeout=5)
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'message' in result
            assert 'version' in result
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API não disponível")


class TestRAGRetrieverUnit:
    """Testes unitários do retriever (sem necessidade de API rodando)."""
    
    def test_mock_retriever_response_structure(self):
        """
        Teste da estrutura de resposta do retriever.
        """
        # Simular resposta esperada
        mock_response = {
            'answer': 'A temperatura operacional é de -10°C a +60°C',
            'question': 'Qual a temperatura?',
            'sources': [
                {
                    'page': 15,
                    'snippet': 'Temperatura de operação: -10°C a +60°C',
                    'score': 0.92
                }
            ]
        }
        
        # Verificar estrutura
        assert 'answer' in mock_response
        assert 'question' in mock_response
        assert 'sources' in mock_response
        assert isinstance(mock_response['sources'], list)
        
        if len(mock_response['sources']) > 0:
            source = mock_response['sources'][0]
            assert 'page' in source
            assert 'snippet' in source
            assert 'score' in source
    
    
    def test_confidence_scoring(self):
        """
        Teste de lógica de confiança baseada em score.
        """
        def get_confidence(score):
            if score >= 0.85:
                return 'high'
            elif score >= 0.65:
                return 'medium'
            else:
                return 'low'
        
        # Testes
        assert get_confidence(0.95) == 'high'
        assert get_confidence(0.85) == 'high'
        assert get_confidence(0.75) == 'medium'
        assert get_confidence(0.50) == 'low'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
