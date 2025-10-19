"""
Módulo de recuperação de informações do sistema RAG.
Gerencia buscas semânticas e interação com LLM.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
import re
import os
import numpy as np
from rank_bm25 import BM25Okapi
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
        llm_provider: str = "mock",
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3.1",
        openai_api_key: Optional[str] = None,
        top_k: int = 3,
        use_hybrid: bool = True  # ✅ NOVO: ativar busca híbrida
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
        self.use_hybrid = use_hybrid
        
        # ✅ NOVO: Configuração BM25
        self.bm25_weight = 0.3
        self.semantic_weight = 0.7
        self.bm25 = None
        self.documents_list = []  # Cache dos documentos para BM25
        
        logger.info(f"Inicializando retriever com provider: {llm_provider}")
        logger.info(f"Busca híbrida: {'Ativada' if use_hybrid else 'Desativada'}")
        
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
        
        # ✅ NOVO: Preparar BM25 se híbrido estiver ativo
        if self.use_hybrid:
            self._prepare_bm25()
    
    # ✅ NOVO MÉTODO
    def _prepare_bm25(self) -> None:
        """Prepara índice BM25 a partir dos documentos FAISS."""
        logger.info("Preparando índice BM25...")
        
        # Extrair todos os documentos do FAISS
        self.documents_list = []
        
        # Isso pode variar dependendo da versão do FAISS
        # Vamos buscar todos os documentos fazendo uma busca ampla
        try:
            # Buscar com uma query genérica para obter todos os docs
            all_docs = self.vectorstore.similarity_search("", k=1000)
            
            for doc in all_docs:
                self.documents_list.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            # Tokenizar corpus para BM25
            tokenized_corpus = [self._tokenize(doc['content']) for doc in self.documents_list]
            
            # Criar índice BM25
            self.bm25 = BM25Okapi(tokenized_corpus)
            
            logger.info(f"✓ Índice BM25 criado com {len(self.documents_list)} documentos")
            
        except Exception as e:
            logger.warning(f"Não foi possível criar índice BM25: {e}")
            logger.warning("Continuando apenas com busca semântica")
            self.use_hybrid = False
    
# ✅ NOVO MÉTODO
    def _tokenize(self, text: str) -> List[str]:
        """Tokenização simples para BM25."""
        return text.lower().split()
    
    # ✅ NOVO MÉTODO
    def _search_bm25(self, query: str, k: int = 10) -> List[tuple]:
        """
        Busca usando BM25.
        
        Returns:
            Lista de (índice, score)
        """
        if self.bm25 is None:
            return []
        
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Normalizar scores entre 0 e 1
        if scores.max() > 0:
            scores = scores / scores.max()
        
        # Retornar top-k índices e scores
        top_indices = np.argsort(scores)[-k:][::-1]
        return [(idx, float(scores[idx])) for idx in top_indices]
    
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
        
        # ✅ MODIFICADO: Usar busca híbrida se ativo
        if self.use_hybrid and self.bm25 is not None:
            return self._hybrid_search(query, k)
        else:
            return self._semantic_search(query, k)
    
    # ✅ NOVO MÉTODO
    def _semantic_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Busca apenas semântica (original)."""
        docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=k)
        
        results = []
        for doc, score in docs_and_scores:
            results.append({
                'content': doc.page_content,
                'page': doc.metadata.get('page', 'N/A'),
                'source': doc.metadata.get('source_file', 'Unknown'),
                'score': float(score)
            })
        
        logger.info(f"Encontrados {len(results)} documentos (semântica)")
        return results
    
    # ✅ NOVO MÉTODO
    def _hybrid_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Busca híbrida combinando BM25 e semântica.
        
        Args:
            query: Pergunta do usuário
            k: Número de documentos finais
            
        Returns:
            Lista de documentos ranqueados por score híbrido
        """
        # Buscar mais documentos inicialmente para rerank
        initial_k = min(k * 3, len(self.documents_list))
        
        # 1. Busca BM25
        bm25_results = self._search_bm25(query, k=initial_k)
        bm25_scores = {idx: score for idx, score in bm25_results}
        
        # 2. Busca Semântica
        semantic_results = self.vectorstore.similarity_search_with_score(query, k=initial_k)
        
        # Mapear documentos semânticos para índices
        semantic_scores = {}
        for doc, score in semantic_results:
            # Encontrar índice correspondente na lista de documentos
            for idx, cached_doc in enumerate(self.documents_list):
                if cached_doc['content'] == doc.page_content:
                    # Normalizar score (FAISS usa distância, menor = melhor)
                    # Converter para similaridade (maior = melhor)
                    semantic_scores[idx] = 1.0 / (1.0 + float(score))
                    break
        
        # 3. Combinar scores
        all_indices = set(bm25_scores.keys()) | set(semantic_scores.keys())
        hybrid_scores = []
        
        for idx in all_indices:
            bm25_score = bm25_scores.get(idx, 0.0)
            semantic_score = semantic_scores.get(idx, 0.0)
            
            # Score híbrido ponderado
            hybrid_score = (self.bm25_weight * bm25_score + 
                          self.semantic_weight * semantic_score)
            
            hybrid_scores.append((idx, hybrid_score))
        
        # 4. Ordenar por score híbrido
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 5. Formatar resultados
        results = []
        for idx, score in hybrid_scores[:k]:
            doc = self.documents_list[idx]
            results.append({
                'content': doc['content'],
                'page': doc['metadata'].get('page', 'N/A'),
                'source': doc['metadata'].get('source_file', 'Unknown'),
                'score': float(score)
            })
        
        logger.info(f"Encontrados {len(results)} documentos (híbrida: BM25={self.bm25_weight}, Semântica={self.semantic_weight})")
        return results

    def _validate_citations(self, answer: str, sources: List[Dict[str, Any]]) -> str:
        """
        Valida e garante que a resposta contenha citações de páginas.
        
        Args:
            answer: Resposta gerada pelo LLM
            sources: Fontes utilizadas
            
        Returns:
            Resposta com citações validadas
        """
        if not sources:
            return answer
        
        # Padrões para detectar citações de páginas
        citation_patterns = [
            r'página\s+\d+',
            r'pág\.\s*\d+',
            r'p\.\s*\d+',
            r'\[página\s+\d+\]',
            r'\(página\s+\d+\)',
        ]
        
        # Verificar se há citação de página na resposta
        has_citation = any(
            re.search(pattern, answer.lower()) 
            for pattern in citation_patterns
        )
        
        # Se não houver citação, adicionar uma
        if not has_citation:
            logger.warning("Resposta sem citação detectada, adicionando referência")
            
            # Pegar a primeira fonte mais relevante
            top_source = sources[0]
            page = top_source['page']
            
            # Adicionar citação no início da resposta
            answer = f"Conforme página {page}: {answer}"
        
        return answer
    
    def _call_mock(self, prompt: str, contexts: List[Dict[str, Any]]) -> str:
        """Mock LLM para testes sem modelo real - agora com citações adequadas."""
        if not contexts:
            return "Informação não encontrada na documentação fornecida."
        
        # Extrair informação relevante dos contextos
        info_parts = []
        for ctx in contexts[:2]:  # Usar top 2 contextos
            page = ctx['page']
            
            # Extrair primeira sentença mais relevante
            content = ctx['content'].strip()
            sentences = content.split('. ')
            
            # Pegar primeira sentença significativa (com mais de 20 caracteres)
            relevant_sentence = next(
                (s for s in sentences if len(s.strip()) > 20),
                content[:200]
            )
            
            # Formatar com citação
            info_parts.append(
                f"Conforme página {page}: {relevant_sentence.strip()}."
            )
        
        # Montar resposta
        response = "Baseado na documentação técnica:\n\n"
        response += "\n\n".join(info_parts)
        response += "\n\n[NOTA: Resposta em modo MOCK. Configure Ollama ou OpenAI para respostas completas geradas por IA.]"
        
        return response
    
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
        """Chama a API da OpenAI usando a biblioteca oficial."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        try:
            # Usar a biblioteca oficial da OpenAI
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model=self.model_name or "gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": """Você é um assistente técnico especializado em documentação de produtos.
                        
INSTRUÇÕES IMPORTANTES:
1. Use APENAS as informações dos documentos fornecidos
2. Cite sempre a página de onde veio a informação (ex: "Conforme página 2...")
3. Se a informação não estiver nos documentos, responda: "Informação não encontrada na documentação fornecida"
4. Seja preciso e técnico
5. Responda em português brasileiro
6. Mantenha um tom profissional e objetivo"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                top_p=0.9
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            # Fallback para requests se a biblioteca não estiver instalada
            logger.warning("Biblioteca openai não encontrada, usando requests")
            return self._call_openai_requests(prompt)
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            raise

    def _call_openai_requests(self, prompt: str) -> str:
        """Fallback usando requests diretamente."""
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
                        {
                            "role": "system", 
                            "content": "Você é um assistente técnico especializado. Use apenas as informações fornecidas e cite sempre as páginas."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "top_p": 0.9
                },
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI via requests: {e}")
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
        
        # ✅ VALIDAR CITAÇÕES AQUI
        answer = self._validate_citations(answer, contexts)
        
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