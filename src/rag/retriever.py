"""
Módulo de recuperação de informações do sistema RAG.
Gerencia buscas semânticas e interação com LLM.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
import os
from langchain_community.vectorstores import FAISS

# Tentar importar a versão nova, senão usa a antiga
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Gerencia recuperação de documentos e geração de respostas."""
    
    def __init__(
        self,
        index_path: str = "data/faiss_index",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_provider: str = "mock",  # "ollama", "openai", "mock"
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3.1",
        openai_api_key: Optional[str] = None,
        top_k: int = 3
    ):
        """
        Inicializa o retriever.
        
        Args:
            index_path: Caminho do índice FAISS
            embedding_model: Modelo de embeddings
            llm_provider: Provedor LLM ("ollama", "openai", "mock")
            ollama_url: URL do servidor Ollama
            model_name: Nome do modelo LLM
            openai_api_key: Chave API OpenAI (se usar)
            top_k: Número de documentos a recuperar
        """
        self.index_path = Path(index_path)
        self.llm_provider = llm_provider
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.top_k = top_k
        
        logger.info(f"Inicializando retriever com provider: {llm_provider}")
        
        # Inicializar embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Carregar índice
        self.vectorstore = None
        self._load_index()
    
    def _load_index(self) -> None:
        """Carrega o índice FAISS."""
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Índice não encontrado em: {self.index_path}. "
                "Execute a ingestão primeiro: python -m src.rag.ingest docs/seu_documento.pdf"
            )
        
        self.vectorstore = FAISS.load_local(
            str(self.index_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        logger.info(f"Índice carregado de: {self.index_path}")
    
    def search(self, query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Busca documentos relevantes para a query.
        
        Args:
            query: Pergunta do usuário
            k: Número de documentos a retornar (padrão: self.top_k)
            
        Returns:
            Lista de documentos com scores e metadados
        """
        if k is None:
            k = self.top_k
        
        logger.info(f"Buscando documentos para: {query}")
        
        # Buscar documentos similares
        docs_and_scores = self.vectorstore.similarity_search_with_score(
            query, 
            k=k
        )
        
        # Formatar resultados
        results = []
        for doc, score in docs_and_scores:
            results.append({
                'content': doc.page_content,
                'page': doc.metadata.get('page', 'N/A'),
                'source': doc.metadata.get('source_file', 'Unknown'),
                'score': float(score)
            })
        
        logger.info(f"Encontrados {len(results)} documentos relevantes")
        
        return results
    
    def _build_prompt(self, question: str, contexts: List[Dict[str, Any]]) -> str:
        """
        Constrói o prompt para o LLM.
        
        Args:
            question: Pergunta do usuário
            contexts: Contextos recuperados
            
        Returns:
            Prompt formatado
        """
        context_text = "\n\n".join([
            f"[Página {ctx['page']}]\n{ctx['content']}"
            for ctx in contexts
        ])
        
        prompt = f"""Você é um assistente técnico especializado em documentação de produtos.
Sua tarefa é responder perguntas baseando-se EXCLUSIVAMENTE nas informações fornecidas abaixo.

INSTRUÇÕES IMPORTANTES:
1. Use APENAS as informações dos documentos fornecidos
2. Cite sempre a página de onde veio a informação (ex: "Conforme página 2...")
3. Se a informação não estiver nos documentos, responda: "Informação não encontrada na documentação fornecida"
4. Seja preciso e técnico
5. Não invente ou especule informações

DOCUMENTOS:
{context_text}

PERGUNTA: {question}

RESPOSTA (cite as páginas):"""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """Chama o Ollama para gerar resposta."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                    }
                },
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()['response']
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Não foi possível conectar ao Ollama em {self.ollama_url}")
            raise ConnectionError(
                f"Ollama não está rodando em {self.ollama_url}. "
                "Certifique-se de que o Ollama está instalado e rodando."
            )
        except Exception as e:
            logger.error(f"Erro ao chamar Ollama: {e}")
            raise
    
    def _call_openai(self, prompt: str) -> str:
        """Chama a API da OpenAI."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name or "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Você é um assistente técnico especializado."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                },
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            raise
    
    def _call_mock(self, prompt: str, contexts: List[Dict[str, Any]]) -> str:
        """Mock LLM para testes sem modelo real."""
        # Extrair informação relevante dos contextos
        info = []
        for ctx in contexts[:2]:  # Usar top 2 contextos
            snippet = ctx['content'][:300]
            info.append(f"Conforme documentação (Página {ctx['page']}): {snippet}...")
        
        response = "Baseado na documentação técnica disponível:\n\n"
        response += "\n\n".join(info)
        response += "\n\n[NOTA: Esta é uma resposta simulada usando modo MOCK. Para respostas completas geradas por IA, configure um LLM real (Ollama ou OpenAI).]"
        
        return response
    
    def _generate_answer(self, prompt: str, contexts: List[Dict[str, Any]]) -> str:
        """
        Gera resposta usando o provedor LLM configurado.
        
        Args:
            prompt: Prompt formatado
            contexts: Contextos para fallback mock
            
        Returns:
            Resposta gerada
        """
        logger.info(f"Gerando resposta com: {self.llm_provider}")
        
        if self.llm_provider == "ollama":
            return self._call_ollama(prompt)
        elif self.llm_provider == "openai":
            return self._call_openai(prompt)
        elif self.llm_provider == "mock":
            return self._call_mock(prompt, contexts)
        else:
            raise ValueError(f"Provedor LLM não suportado: {self.llm_provider}")
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        Responde uma pergunta usando RAG.
        
        Args:
            question: Pergunta do usuário
            
        Returns:
            Dict com resposta e fontes
        """
        # Buscar contextos relevantes
        contexts = self.search(question)
        
        if not contexts:
            return {
                'answer': 'Nenhum documento relevante encontrado na base de conhecimento.',
                'sources': [],
                'question': question
            }
        
        # Construir prompt
        prompt = self._build_prompt(question, contexts)
        
        # Gerar resposta
        try:
            answer = self._generate_answer(prompt, contexts)
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            # Fallback para mock em caso de erro
            logger.warning("Usando modo MOCK como fallback")
            answer = self._call_mock(prompt, contexts)
        
        # Formatar fontes
        sources = [
            {
                'page': ctx['page'],
                'snippet': ctx['content'][:200] + '...' if len(ctx['content']) > 200 else ctx['content'],
                'score': ctx['score']
            }
            for ctx in contexts
        ]
        
        return {
            'answer': answer.strip(),
            'sources': sources,
            'question': question
        }


def main():
    """Função principal para testar o retriever."""
    import sys
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determinar provider
    provider = os.getenv("LLM_PROVIDER", "mock")
    
    # Criar retriever
    try:
        retriever = DocumentRetriever(llm_provider=provider)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Verificar se há pergunta nos argumentos
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
    else:
        question = "Qual é a faixa de temperatura operacional do Alpha-X Pro?"
    
    print(f"\n❓ Pergunta: {question}")
    print(f"🤖 Provider: {provider}\n")
    
    # Fazer pergunta
    result = retriever.ask(question)
    
    print(f"✅ Resposta:\n{result['answer']}\n")
    print(f"📚 Fontes ({len(result['sources'])}):")
    for i, source in enumerate(result['sources'], 1):
        print(f"\n  {i}. Página {source['page']} (score: {source['score']:.3f})")
        print(f"     {source['snippet']}")


if __name__ == "__main__":
    main()