"""Script de teste para o sistema RAG."""
import requests
import json
import sys

API_URL = "http://localhost:8001"

def test_health():
    """Testa o health check."""
    print("🏥 Testando health check...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        # Verificar se obteve resposta
        if response.status_code == 200:
            try:
                data = response.json()
                print(json.dumps(data, indent=2))
                print()
                return data
            except json.JSONDecodeError:
                print(f"❌ Resposta não é JSON válido: {response.text}")
                return None
        else:
            print(f"❌ Status code {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à API!")
        print()
        print("A API está rodando?")
        print("Inicie com: python -m src.rag.api")
        print()
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Timeout ao conectar à API")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

def test_question(question: str):
    """Testa uma pergunta."""
    print(f"❓ Pergunta: {question}")
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={"question": question},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Resposta:")
            print(result['answer'])
            print()
            
            print(f"📚 Fontes ({len(result['sources'])}):")
            for i, source in enumerate(result['sources'], 1):
                print(f"  {i}. Página {source['page']} (score: {source['score']:.3f})")
                print(f"     {source['snippet'][:100]}...")
            print()
        else:
            print(f"❌ Erro {response.status_code}")
            try:
                error = response.json()
                print(f"   Detalhes: {error.get('detail', 'Sem detalhes')}")
            except:
                print(f"   Resposta: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Perdeu conexão com a API")
    except requests.exceptions.Timeout:
        print("❌ Timeout (a resposta demorou muito)")
    except Exception as e:
        print(f"❌ Erro ao fazer pergunta: {e}")

def test_search(query: str):
    """Testa a busca de documentos."""
    print(f"🔍 Buscando: {query}")
    print()
    
    try:
        response = requests.get(
            f"{API_URL}/search",
            params={"query": query, "k": 3},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"📄 Resultados ({len(result['results'])}):")
            for i, doc in enumerate(result['results'], 1):
                print(f"  {i}. Página {doc['page']} (score: {doc['score']:.3f})")
                print(f"     {doc['content'][:150]}...")
                print()
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"❌ Erro na busca: {e}")

if __name__ == "__main__":
    print("="*80)
    print("🧪 TESTE DO SISTEMA MINI-RAG")
    print("="*80)
    print()
    
    # Testar health
    health = test_health()
    
    if health is None:
        print("❌ Não foi possível verificar o status da API")
        sys.exit(1)
    
    if not health.get('index_loaded'):
        print("⚠️  Índice não carregado!")
        print()
        print("Execute primeiro:")
        print("   python -m src.rag.ingest docs/seu_documento.pdf")
        print()
        sys.exit(1)
    
    if not health.get('ollama_available'):
        print("⚠️  Ollama não está disponível")
        print("   O sistema usará modo MOCK (respostas simuladas)")
        print()
    
    print("-"*80)
    print()
    
    # Testar busca simples
    test_search("temperatura operacional")
    
    print("-"*80)
    print()
    
    # Testar perguntas
    questions = [
        "Qual é a faixa de temperatura operacional?",
        "Quais são as interfaces disponíveis?",
        "Como fazer update de firmware?",
    ]
    
    for q in questions:
        test_question(q)
        print("-"*80)
        print()
    
    print("✅ Testes concluídos!")