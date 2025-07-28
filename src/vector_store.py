"""Gerenciamento de vetores com Qdrant."""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

from src.config import get_config

config = get_config()


class EmbeddingManager:
    """Gerenciador de embeddings usando APIs externas."""
    
    def __init__(self, model_name: str = None):
        """Inicializa o gerenciador de embeddings."""
        self.model_name = model_name or config.DEFAULT_EMBEDDING_MODEL
        self.model_config = config.EMBEDDING_MODELS.get(self.model_name)
        
        if not self.model_config:
            raise ValueError(f"Modelo de embedding '{self.model_name}' não encontrado")
        
        self.provider = self.model_config["provider"]
        self.dimension = self.model_config["dimension"]
        self.model = self._initialize_model()
    
    def _initialize_model(self):
        """Inicializa o modelo de embedding baseado no provider."""
        if self.provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                api_key=config.OPENAI_API_KEY,
                model=self.model_config["model"]
            )
        elif self.provider == "gemini":
            # Implementação para Google Gemini
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                google_api_key=config.GEMINI_API_KEY,
                model=self.model_config["model"]
            )
        else:
            raise ValueError(f"Provider '{self.provider}' não suportado")
    
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto."""
        print(f"    🔍 Gerando embedding com modelo {self.model_name} ({self.provider})")
        try:
            embedding = self.model.embed_query(text)
            print(f"    ✅ Embedding gerado com sucesso: {len(embedding)} dimensões")
            return embedding
        except Exception as e:
            print(f"    ❌ Erro ao gerar embedding: {e}")
            raise e
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings para múltiplos textos."""
        return self.model.embed_documents(texts)


class QdrantVectorStore:
    """Interface para o banco de vetores Qdrant."""
    
    def __init__(self):
        """Inicializa a conexão com Qdrant."""
        self.host = config.QDRANT_HOST
        self.port = config.QDRANT_PORT
        self.api_key = config.QDRANT_API_KEY
        self.client = None
        self._connect()
    
    def _connect(self):
        """Conecta ao Qdrant."""
        try:
            # Usar URL explícita para garantir HTTP
            qdrant_url = f"http://{self.host}:{self.port}"
            
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=None,  # Não usar API key em desenvolvimento local
                timeout=60,
                prefer_grpc=False,  # Usar HTTP ao invés de gRPC
                check_compatibility=False  # Desabilitar check de versão
            )
            
            # Testar a conexão
            collections = self.client.get_collections()
            print(f"✅ Conectado ao Qdrant em {qdrant_url}")
            print(f"📊 Collections existentes: {len(collections.collections)}")
            
        except Exception as e:
            raise Exception(f"Erro ao conectar ao Qdrant: {str(e)}")
    
    def _ensure_connection(self):
        """Garante que a conexão está ativa."""
        if not self.client:
            self._connect()
        
        try:
            # Teste simples de conectividade
            self.client.get_collections()
        except Exception as e:
            print(f"⚠️ Reconectando ao Qdrant: {e}")
            self._connect()
    
    def create_collection(self, collection_name: str, embedding_model: str, 
                         description: str = "") -> str:
        """Cria uma nova collection no Qdrant."""
        self._ensure_connection()
        
        try:
            # Verificar se o modelo de embedding existe
            if embedding_model not in config.EMBEDDING_MODELS:
                raise ValueError(f"Modelo de embedding '{embedding_model}' não encontrado")
            
            model_config = config.EMBEDDING_MODELS[embedding_model]
            dimension = model_config["dimension"]
            
            # Criar a collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            
            # Criar ponto de metadata para a collection
            metadata_point = PointStruct(
                id=0,  # ID fixo para metadata
                vector=[0.0] * dimension,  # Vetor zero para metadata
                payload={
                    "name": collection_name,
                    "embedding_model": embedding_model,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "document_count": 0,
                    "model_config": model_config
                }
            )
            
            # Inserir metadata
            self.client.upsert(
                collection_name=collection_name,
                points=[metadata_point]
            )
            
            print(f"✅ Collection '{collection_name}' criada com modelo '{embedding_model}'")
            return collection_name
            
        except Exception as e:
            print(f"❌ Erro ao criar collection '{collection_name}': {e}")
            # Tentar deletar a collection se foi criada mas falhou no metadata
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            raise e
    
    def insert_documents(self, collection_name: str, documents: List[Document], 
                        embedding_model: str = None) -> bool:
        """Insere documentos em uma collection."""
        self._ensure_connection()
        
        try:
            # Buscar metadata da collection para obter o modelo de embedding
            if not embedding_model:
                metadata = self._get_collection_metadata(collection_name)
                if not metadata:
                    raise ValueError(f"Collection '{collection_name}' não encontrada ou sem metadata")
                embedding_model = metadata.get("embedding_model")
            
            # Inicializar o modelo de embedding
            embedding_manager = EmbeddingManager(embedding_model)
            
            # Preparar pontos para inserção
            points = []
            print(f"🔧 Iniciando inserção de {len(documents)} documentos na collection '{collection_name}'")
            print(f"📊 Modelo de embedding: {embedding_model}")
            
            for i, doc in enumerate(documents, start=1):  # Começar do 1 para não conflitar com metadata (ID 0)
                print(f"  Processando documento {i}/{len(documents)}: {len(doc.page_content)} chars")
                
                # Gerar embedding para o conteúdo
                try:
                    embedding = embedding_manager.get_embedding(doc.page_content)
                    print(f"    ✅ Embedding gerado: {len(embedding)} dimensões")
                except Exception as e:
                    print(f"    ❌ Erro ao gerar embedding: {e}")
                    raise e
                
                # Criar ponto
                point = PointStruct(
                    id=i,
                    vector=embedding,
                    payload={
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "file_name": doc.metadata.get("file_name", "Documento sem nome"),
                        "chunk_index": doc.metadata.get("chunk_index", 0),
                        "created_at": datetime.now().isoformat()
                    }
                )
                points.append(point)
                print(f"    📄 Ponto criado com ID {i}")
            
            # Inserir pontos
            if points:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                
                # Atualizar contador de documentos na metadata
                self._update_collection_document_count(collection_name, len(points))
                
                print(f"✅ {len(points)} documentos inseridos na collection '{collection_name}'")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Erro ao inserir documentos na collection '{collection_name}': {e}")
            raise e
    
    def search_similar(self, collection_name: str, query: str, top_k: int = 5, 
                      embedding_model: str = None) -> List[Dict[str, Any]]:
        """Busca documentos similares em uma collection."""
        self._ensure_connection()
        
        try:
            # Buscar metadata da collection para obter o modelo de embedding
            if not embedding_model:
                metadata = self._get_collection_metadata(collection_name)
                if not metadata:
                    raise ValueError(f"Collection '{collection_name}' não encontrada ou sem metadata")
                embedding_model = metadata.get("embedding_model")
            
            # Inicializar o modelo de embedding
            embedding_manager = EmbeddingManager(embedding_model)
            
            # Gerar embedding para a query
            query_embedding = embedding_manager.get_embedding(query)
            
            # Buscar documentos similares
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=Filter(
                    must_not=[
                        FieldCondition(
                            key="name",
                            match=MatchValue(value=collection_name)
                        )
                    ]
                )  # Excluir o ponto de metadata
            )
            
            # Formatar resultados
            results = []
            for point in search_result:
                results.append({
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "file_name": point.payload.get("file_name", "unknown"),
                    "score": point.score,
                    "id": point.id
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Erro ao buscar na collection '{collection_name}': {e}")
            raise e
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """Lista todas as collections disponíveis."""
        self._ensure_connection()
        
        try:
            collections_response = self.client.get_collections()
            collections = []
            
            for collection in collections_response.collections:
                collection_name = collection.name
                
                # Buscar metadata da collection
                metadata = self._get_collection_metadata(collection_name)
                
                if metadata:
                    collections.append({
                        "name": collection_name,
                        "embedding_model": metadata.get("embedding_model", "unknown"),
                        "description": metadata.get("description", ""),
                        "created_at": metadata.get("created_at", ""),
                        "document_count": metadata.get("document_count", 0),
                        "model_config": metadata.get("model_config", {})
                    })
                else:
                    # Collection sem metadata (legacy)
                    collections.append({
                        "name": collection_name,
                        "embedding_model": "unknown",
                        "description": "Collection sem configuração",
                        "created_at": "",
                        "document_count": 0,
                        "model_config": {}
                    })
            
            return collections
            
        except Exception as e:
            print(f"❌ Erro ao listar collections: {e}")
            raise e
    
    def list_collection_documents(self, collection_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Lista documentos de uma collection específica."""
        self._ensure_connection()
        
        try:
            # Buscar todos os pontos da collection (exceto metadata)
            scroll_result = self.client.scroll(
                collection_name=collection_name
            )
            
            documents = []
            for point in scroll_result[0]:  # scroll_result é uma tupla (points, next_page_offset)
                # Pular o ponto de metadata (ID 0)
                if point.id == 0:
                    continue
                    
                documents.append({
                    "id": point.id,
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "file_name": point.payload.get("file_name", "Documento sem nome"),
                    "chunk_index": point.payload.get("chunk_index", 0),
                    "created_at": point.payload.get("created_at", "")
                })
            
            return documents
            
        except Exception as e:
            print(f"❌ Erro ao listar documentos da collection '{collection_name}': {e}")
            raise e
    
    def delete_collection(self, collection_name: str) -> bool:
        """Deleta uma collection."""
        self._ensure_connection()
        
        try:
            self.client.delete_collection(collection_name)
            print(f"✅ Collection '{collection_name}' deletada")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao deletar collection '{collection_name}': {e}")
            raise e
    
    def _get_collection_metadata(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Busca metadata de uma collection."""
        try:
            # Buscar o ponto de metadata (ID 0)
            search_result = self.client.retrieve(
                collection_name=collection_name,
                ids=[0]
            )
            
            if search_result and len(search_result) > 0:
                point = search_result[0]
                return point.payload
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar metadata da collection '{collection_name}': {e}")
            return None
    
    def _update_collection_document_count(self, collection_name: str, increment: int = 0):
        """Atualiza o contador de documentos na metadata da collection."""
        try:
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                current_count = metadata.get("document_count", 0)
                new_count = current_count + increment
                
                # Obter dimensão correta do modelo
                model_config = metadata.get("model_config", {})
                dimension = model_config.get("dimension", 1536)
                
                # Atualizar o ponto de metadata
                updated_point = PointStruct(
                    id=0,
                    vector=[0.0] * dimension,  # Vetor zero com dimensão correta
                    payload={
                        **metadata,
                        "document_count": new_count
                    }
                )
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[updated_point]
                )
                
        except Exception as e:
            print(f"⚠️ Erro ao atualizar contador de documentos: {e}")
    
    def _recalculate_collection_document_count(self, collection_name: str):
        """Recalcula o contador de documentos baseado no número real de documentos."""
        try:
            # Contar documentos reais (excluindo metadata ID 0)
            scroll_result = self.client.scroll(
                collection_name=collection_name
            )
            
            real_count = 0
            for point in scroll_result[0]:
                if point.id != 0:  # Excluir ponto de metadata
                    real_count += 1
            
            # Atualizar metadata com contagem real
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                model_config = metadata.get("model_config", {})
                dimension = model_config.get("dimension", 1536)
                
                updated_point = PointStruct(
                    id=0,
                    vector=[0.0] * dimension,
                    payload={
                        **metadata,
                        "document_count": real_count
                    }
                )
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[updated_point]
                )
                
                print(f"✅ Contagem de documentos da collection '{collection_name}' atualizada para {real_count}")
                
        except Exception as e:
            print(f"❌ Erro ao recalcular contagem de documentos: {e}")
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Obtém informações detalhadas de uma collection."""
        try:
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                return {
                    "name": collection_name,
                    "embedding_model": metadata.get("embedding_model"),
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at", ""),
                    "document_count": metadata.get("document_count", 0),
                    "model_config": metadata.get("model_config", {})
                }
            return None
            
        except Exception as e:
            print(f"❌ Erro ao obter informações da collection '{collection_name}': {e}")
            return None 