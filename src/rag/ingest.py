"""
Módulo de ingestão de documentos para o sistema RAG.
Processa PDFs, faz chunking e cria índice FAISS.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Gerencia a ingestão e indexação de documentos técnicos."""
    
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 2400,
        chunk_overlap: int = 400,
        index_path: str = "data/faiss_index"
    ):
        """
        Inicializa o ingestor de documentos.
        
        Args:
            embedding_model: Nome do modelo de embeddings do HuggingFace
            chunk_size: Tamanho dos chunks em caracteres
            chunk_overlap: Overlap entre chunks
            index_path: Caminho para salvar o índice FAISS
        """
        self.embedding_model_name = embedding_model
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.vectorstore = None
        
    def load_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Carrega e processa um arquivo PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de documentos processados com metadados
        """
        logger.info(f"Carregando PDF: {pdf_path}")
        
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        logger.info(f"PDF carregado: {len(pages)} páginas")
        
        # Adicionar metadados extras
        for i, page in enumerate(pages):
            page.metadata['source_file'] = Path(pdf_path).name
            page.metadata['page'] = i + 1
            
        return pages
    
    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        """
        Divide documentos em chunks menores.
        
        Args:
            documents: Lista de documentos do LangChain
            
        Returns:
            Lista de chunks de documentos
        """
        logger.info(f"Dividindo {len(documents)} documentos em chunks...")
        
        chunks = self.text_splitter.split_documents(documents)
        
        logger.info(f"Criados {len(chunks)} chunks")
        
        return chunks
    
    def create_index(self, chunks: List[Any]) -> None:
        """
        Cria índice FAISS a partir dos chunks.
        
        Args:
            chunks: Lista de chunks de documentos
        """
        logger.info("Criando índice FAISS...")
        
        self.vectorstore = FAISS.from_documents(
            documents=chunks,
            embedding=self.embeddings
        )
        
        logger.info("Índice FAISS criado com sucesso")
    
    def save_index(self) -> None:
        """Salva o índice FAISS em disco."""
        if self.vectorstore is None:
            raise ValueError("Nenhum índice para salvar. Execute create_index primeiro.")
        
        save_path = str(self.index_path)
        self.vectorstore.save_local(save_path)
        logger.info(f"Índice salvo em: {save_path}")
    
    def load_index(self) -> None:
        """Carrega um índice FAISS existente do disco."""
        load_path = str(self.index_path)
        
        if not Path(load_path).exists():
            raise FileNotFoundError(f"Índice não encontrado em: {load_path}")
        
        self.vectorstore = FAISS.load_local(
            load_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        logger.info(f"Índice carregado de: {load_path}")
    
    def ingest_document(self, pdf_path: str, save: bool = True) -> None:
        """
        Pipeline completo de ingestão de documento.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            save: Se True, salva o índice após criação
        """
        # Carregar PDF
        documents = self.load_pdf(pdf_path)
        
        # Criar chunks
        chunks = self.chunk_documents(documents)
        
        # Criar índice
        self.create_index(chunks)
        
        # Salvar índice
        if save:
            self.save_index()
        
        logger.info("Ingestão concluída com sucesso")


def main():
    """Função principal para executar a ingestão."""
    import sys
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("Uso: python -m src.rag.ingest <caminho_para_pdf>")
        print("Exemplo: python -m src.rag.ingest docs/Alpha-X_Pro_Tecnico.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        logger.error(f"Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    # Criar ingestor e processar documento
    ingestor = DocumentIngestor()
    ingestor.ingest_document(pdf_path)
    
    print(f"\n✅ Documento indexado com sucesso!")
    print(f"📁 Índice salvo em: data/faiss_index")


if __name__ == "__main__":
    main()