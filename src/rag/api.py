"""
API FastAPI para o sistema RAG.
Expõe endpoints para perguntas e gerenciamento.
"""
import logging
import os
import uvicorn
from typing import Dict, Any, List, Optional
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .retriever import DocumentRetriever

# Imports locais
try:
    from src.rag.retriever import DocumentRetriever
    from src.rag.ingest import DocumentIngestor
except ImportError:
    from retriever import DocumentRetriever
    from ingest import DocumentIngestor

# Carregar variáveis de ambiente do .env
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

# Carregar .env no início
load_env()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar componentes globais
retriever: Optional[DocumentRetriever] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    # Startup
    global retriever
    
    # Usar OpenAI por padrão se a chave estiver configurada
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        llm_provider = "openai"
        logger.info("🤖 Chave OpenAI detectada, usando provider OpenAI")
    else:
        llm_provider = os.getenv("LLM_PROVIDER", "mock")
        logger.info(f"🤖 Usando provider: {llm_provider}")
    
    try:
        logger.info(f"Inicializando retriever com provider: {llm_provider}...")
        retriever = DocumentRetriever(
            llm_provider=llm_provider,
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        )
        logger.info("✅ Retriever inicializado com sucesso")
    except FileNotFoundError as e:
        logger.warning(f"⚠️  Índice não encontrado: {e}")
        logger.warning("Execute a ingestão antes de usar a API")
        logger.warning("Exemplo: python -m src.rag.ingest docs/seu_documento.pdf")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar retriever: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    # Shutdown
    logger.info("🛑 Encerrando aplicação...")


# Criar app FastAPI com lifespan
app = FastAPI(
    title="Mini-RAG API",
    description="API para sistema de Retrieval-Augmented Generation sobre documentação técnica",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos Pydantic
class QuestionRequest(BaseModel):
    """Modelo de requisição para perguntas."""
    question: str = Field(
        ..., 
        description="Pergunta sobre a documentação técnica",
        min_length=5,
        max_length=500
    )
    top_k: int = Field(
        3,
        description="Número de documentos a recuperar",
        ge=1,
        le=10
    )


class Source(BaseModel):
    """Modelo para fonte de informação."""
    page: int = Field(..., description="Número da página")
    snippet: str = Field(..., description="Trecho relevante do documento")
    score: float = Field(..., description="Score de relevância")


class QuestionResponse(BaseModel):
    """Modelo de resposta para perguntas."""
    answer: str = Field(..., description="Resposta gerada pelo sistema")
    sources: List[Source] = Field(..., description="Fontes utilizadas")
    question: str = Field(..., description="Pergunta original")


class HealthResponse(BaseModel):
    """Modelo de resposta para health check."""
    status: str
    index_loaded: bool
    llm_available: bool
    llm_provider: str


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "message": "Mini-RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "ask": "POST /ask - Fazer pergunta",
            "search": "GET /search - Buscar documentos",
            "ingest": "POST /ingest - Adicionar PDF"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica o status dos componentes."""
    index_loaded = retriever is not None and retriever.vectorstore is not None
    
    # Verificar LLM
    llm_available = False
    llm_provider = "none"
    
    if retriever:
        llm_provider = retriever.llm_provider
        
        if llm_provider == "openai":
            # Verificar se a chave está configurada
            llm_available = retriever.openai_api_key is not None
            if llm_available:
                try:
                    # Fazer teste rápido da API
                    from openai import OpenAI
                    client = OpenAI(api_key=retriever.openai_api_key)
                    # Teste com um prompt mínimo
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    llm_available = True
                except Exception as e:
                    logger.warning(f"OpenAI API não disponível: {e}")
                    llm_available = False
        elif llm_provider == "ollama":
            try:
                import requests
                response = requests.get(f"{retriever.ollama_url}/api/tags", timeout=5)
                llm_available = response.status_code == 200
            except:
                pass
        elif llm_provider == "mock":
            llm_available = True
    
    status = "healthy" if (index_loaded and llm_available) else "degraded"
    
    return {
        "status": status,
        "index_loaded": index_loaded,
        "llm_available": llm_available,
        "llm_provider": llm_provider,
        "model": retriever.model_name if retriever else "none"
    }


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Responde uma pergunta usando RAG."""
    if retriever is None:
        raise HTTPException(
            status_code=503,
            detail="Sistema não inicializado. Execute a ingestão de documentos primeiro."
        )
    
    if retriever.vectorstore is None:
        raise HTTPException(
            status_code=503,
            detail="Índice não carregado. Execute: python -m src.rag.ingest docs/seu_documento.pdf"
        )
    
    try:
        logger.info(f"Processando pergunta: {request.question}")
        
        original_top_k = retriever.top_k
        retriever.top_k = request.top_k
        
        result = retriever.ask(request.question)
        
        retriever.top_k = original_top_k
        
        response = QuestionResponse(
            answer=result['answer'],
            sources=[Source(**source) for source in result['sources']],
            question=result['question']
        )
        
        logger.info("✅ Pergunta processada com sucesso")
        return response
        
    except ConnectionError as e:
        logger.error(f"Erro de conexão: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"LLM não está disponível: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erro ao processar pergunta: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar pergunta: {str(e)}"
        )


@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingere um novo documento PDF."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos PDF são suportados"
        )
    
    try:
        temp_path = Path("data/temp") / file.filename
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Arquivo salvo: {temp_path}")
        
        ingestor = DocumentIngestor()
        ingestor.ingest_document(str(temp_path))
        
        global retriever
        llm_provider = os.getenv("LLM_PROVIDER", "mock")
        retriever = DocumentRetriever(llm_provider=llm_provider)
        
        temp_path.unlink()
        
        logger.info("✅ Documento ingerido com sucesso")
        
        return {
            "message": "Documento ingerido com sucesso",
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Erro ao ingerir documento: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao ingerir documento: {str(e)}"
        )


@app.get("/search")
async def search_documents(query: str, k: int = 3):
    """Busca documentos relevantes sem gerar resposta."""
    if retriever is None or retriever.vectorstore is None:
        raise HTTPException(
            status_code=503,
            detail="Sistema não inicializado ou índice não carregado"
        )
    
    try:
        results = retriever.search(query, k=k)
        return {
            "query": query,
            "results": results
        }
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro na busca: {str(e)}"
        )


def start_server(host: str = "0.0.0.0", port: int = 8001):
    """Inicia o servidor FastAPI."""
    logger.info("="*60)
    logger.info("🚀 Iniciando Mini-RAG API")
    logger.info(f"📍 URL: http://{host}:{port}")
    logger.info(f"📚 Documentação: http://{host}:{port}/docs")
    logger.info(f"🤖 LLM Provider: {os.getenv('LLM_PROVIDER', 'mock')}")
    logger.info("="*60)
    
    uvicorn.run(
        "src.rag.api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()