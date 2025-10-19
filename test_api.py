"""Teste rápido da integração OpenAI."""
import os
from pathlib import Path
from src.rag.retriever import DocumentRetriever

# Carregar variáveis de ambiente do arquivo .env
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
        print("✅ Arquivo .env carregado")
    else:
        print("⚠️  Arquivo .env não encontrado")

def test_openai():
    """Testa a integração com OpenAI."""
    print("🧪 Testando integração OpenAI...")
    print("=" * 50)
    
    # Carregar .env primeiro
    load_env()
    
    # Verificar variáveis de ambiente
    api_key = os.getenv("OPENAI_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "mock")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    print(f"🔧 Provider configurado: {provider}")
    print(f"🤖 Modelo configurado: {model}")
    
    if not api_key or api_key == "sua_chave_openai_aqui":
        print("❌ OPENAI_API_KEY não configurada ou usando valor padrão")
        print("📝 Por favor, edite o arquivo .env e adicione sua chave da OpenAI")
        return
    
    print(f"✅ Chave configurada: {api_key[:8]}...")
    
    # Criar retriever com parâmetros explícitos
    try:
        retriever = DocumentRetriever(
            llm_provider="openai",
            openai_api_key=api_key,
            model_name=model
        )
        print("✅ Retriever criado com sucesso")
        print(f"🔧 Provider ativo: {retriever.llm_provider}")
    except FileNotFoundError as e:
        print(f"❌ Erro: Índice não encontrado")
        print("📋 Execute primeiro: python -m src.rag.ingest docs/seu_documento.pdf")
        return
    except Exception as e:
        print(f"❌ Erro ao criar retriever: {e}")
        return
    
    # Fazer pergunta de teste
    try:
        print("\n🤔 Fazendo pergunta de teste...")
        result = retriever.ask("Quais são as principais características técnicas?")
        print("✅ Pergunta processada com sucesso!")
        print(f"\n📝 Resposta:\n{result['answer']}")
        print(f"\n📚 Fontes utilizadas: {len(result['sources'])}")
        
        # Mostrar algumas fontes
        for i, source in enumerate(result['sources'][:2], 1):
            print(f"\n  📄 Fonte {i} (Página {source['page']}):")
            print(f"     {source['snippet'][:100]}...")
            
    except Exception as e:
        print(f"❌ Erro ao processar pergunta: {e}")
        import traceback
        traceback.print_exc()

def test_environment():
    """Testa se as variáveis de ambiente estão corretas."""
    print("\n🔍 Verificando configuração do ambiente...")
    print("=" * 50)
    
    load_env()
    
    vars_to_check = [
        "OPENAI_API_KEY",
        "LLM_PROVIDER", 
        "OPENAI_MODEL"
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            if var == "OPENAI_API_KEY":
                print(f"✅ {var}: {value[:8]}...")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: não configurada")

if __name__ == "__main__":
    test_environment()
    print("\n")
    test_openai()