"""
Teste completo do sistema RAG.
"""
import requests
import json
import os
from pathlib import Path

# Carregar variáveis de ambiente
def load_env():
    """Carrega variáveis de ambiente do arquivo .env"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def test_health():
    """Testa o health check da API."""
    print("🏥 Testando health check...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        result = response.json()
        print(json.dumps(result, indent=2))
        
        # Verificar se está usando OpenAI
        if result.get("llm_provider") == "openai":
            print("✅ Sistema configurado para OpenAI")
        elif result.get("llm_provider") == "mock":
            print("⚠️  Sistema ainda em modo MOCK")
            print("   Verifique se as variáveis de ambiente estão corretas")
        
        return result.get("status") == "healthy"
    except requests.exceptions.ConnectionError:
        print("❌ API não está rodando em http://localhost:8001")
        print("   Execute: uvicorn src.rag.api:app --reload --port 8001")
        return False
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False

def test_question(question: str):
    """Testa uma pergunta específica."""
    print(f"\n❓ Pergunta: {question}")
    try:
        response = requests.post(
            "http://localhost:8001/ask",
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Resposta gerada com sucesso!")
            print(f"\n📝 Resposta:\n{result['answer']}")
            print(f"\n📚 Fontes ({len(result['sources'])}):")
            
            for i, source in enumerate(result['sources'], 1):
                print(f"\n  {i}. Página {source['page']} (score: {source.get('score', 'N/A'):.3f})")
                print(f"     {source['snippet'][:150]}...")
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
    
    except requests.exceptions.Timeout:
        print("⏱️  Timeout - a pergunta demorou muito para ser processada")
    except Exception as e:
        print(f"❌ Erro ao fazer pergunta: {e}")

def main():
    """Função principal do teste."""
    print("=" * 80)
    print("🧪 TESTE DO SISTEMA MINI-RAG")
    print("=" * 80)
    
    # Carregar variáveis de ambiente
    load_env()
    
    # Verificar configuração
    provider = os.getenv("LLM_PROVIDER", "mock")
    api_key = os.getenv("OPENAI_API_KEY")
    
    print(f"🔧 Provider configurado: {provider}")
    if provider == "openai":
        if api_key and api_key != "sua_chave_openai_aqui":
            print(f"🔑 OpenAI Key: {api_key[:8]}...")
        else:
            print("❌ Chave OpenAI não configurada corretamente!")
    
    print()
    
    # Testar health
    if not test_health():
        print("\n❌ Health check falhou. Verifique se a API está rodando.")
        return
    
    # Testar perguntas
    questions = [
        "Quais são as principais características técnicas do produto?",
        "Qual é a faixa de temperatura operacional?",
        "Como fazer a instalação básica?",
        "Quais são os requisitos do sistema?"
    ]
    
    for question in questions:
        test_question(question)
        print("\n" + "-" * 50)
    
    # Verificar se estava usando OpenAI
    if provider == "openai":
        print("\n🎉 Teste concluído com OpenAI!")
    else:
        print("\n⚠️  Teste concluído, mas ainda em modo MOCK")
        print("   Para usar OpenAI:")
        print("   1. Configure OPENAI_API_KEY no arquivo .env")
        print("   2. Configure LLM_PROVIDER=openai no arquivo .env")
        print("   3. Reinicie a API")

if __name__ == "__main__":
    main()