from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import time
import openai

from app.models.database import get_db
from app.models.vector_store import VectorStore
from app.models.document import AIModel, AIModelType

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# ========================================
# SCHEMAS
# ========================================

class SimilaritySearchRequest(BaseModel):
    """Schema para requisição de busca por similaridade."""
    vector_store_id: int = Field(..., description="ID do banco vetorial")
    query_text: str = Field(
        ..., 
        min_length=1, 
        max_length=5000, 
        description="Texto da consulta"
    )
    limit: int = Field(
        10, 
        ge=1, 
        le=100, 
        description="Número máximo de resultados"
    )
    similarity_threshold: float = Field(
        0.7, 
        ge=0.0, 
        le=1.0, 
        description="Limiar mínimo de similaridade"
    )
    group_by_document: bool = Field(
        False,
        description=(
            "Agrupar por documento (retorna apenas o chunk "
            "mais relevante de cada documento)"
        )
    )


class SimilarityResult(BaseModel):
    """Schema para resultado individual de busca."""
    id: str = Field(..., description="ID do vetor")
    score: float = Field(..., description="Score de similaridade")
    text: Optional[str] = Field(None, description="Texto do chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados")


class SimilaritySearchResponse(BaseModel):
    """Schema para resposta de busca por similaridade."""
    vector_store_id: int
    vector_store_name: str
    query_text: str
    results: List[SimilarityResult]
    total_results: int
    search_time_ms: int
    embedding_model_used: str
    grouped_by_document: bool
    searched_at: datetime


# ========================================
# FUNÇÕES PRINCIPAIS
# ========================================

async def get_vector_store(vector_store_id: int, db: Session) -> VectorStore:
    """Buscar banco vetorial ativo."""
    store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id,
        VectorStore.deleted_at.is_(None),
        VectorStore.is_active.is_(True)
    ).first()
    
    if not store:
        raise HTTPException(
            status_code=404,
            detail="Banco vetorial não encontrado ou inativo"
        )
    
    if not store.embedding_model_id:
        raise HTTPException(
            status_code=400,
            detail="Banco vetorial não tem modelo de embedding configurado"
        )
    
    return store


async def get_embedding_model(embedding_model_id: int, db: Session) -> AIModel:
    """Buscar modelo de embedding ativo."""
    model = db.query(AIModel).filter(
        AIModel.id == embedding_model_id,
        AIModel.model_type == AIModelType.EMBEDDING,
        AIModel.is_active.is_(True),
        AIModel.deleted_at.is_(None)
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail="Modelo de embedding não encontrado ou inativo"
        )
    
    if not model.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"API key não configurada para o modelo {model.name}"
        )
    
    return model


async def generate_embedding(text: str, model: AIModel) -> List[float]:
    """Gerar embedding usando OpenAI."""
    try:
        client = openai.OpenAI(api_key=model.api_key)
        
        response = client.embeddings.create(
            input=text,
            model=model.name
        )
        
        return response.data[0].embedding
        
    except Exception as e:
        logger.error(f"Erro ao gerar embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro na geração do embedding: {str(e)}"
        )


def group_results_by_document(
    results: List[SimilarityResult], 
    limit: int
) -> List[SimilarityResult]:
    """Agrupar resultados por documento, mantendo chunk mais relevante."""
    if not results:
        return results
    
    # Dicionário para armazenar o melhor resultado de cada documento
    best_by_document = {}
    
    for result in results:
        # Extrair document_id dos metadados
        if not result.metadata or 'document_id' not in result.metadata:
            continue
            
        document_id = result.metadata['document_id']
        
        # Se é o primeiro resultado deste documento ou tem score maior
        if (document_id not in best_by_document or 
                result.score > best_by_document[document_id].score):
            best_by_document[document_id] = result
    
    # Converter para lista e ordenar por score decrescente
    grouped_results = list(best_by_document.values())
    grouped_results.sort(key=lambda x: x.score, reverse=True)
    
    # Retornar apenas até o limite solicitado
    return grouped_results[:limit]


async def search_qdrant(
    vector_store: VectorStore,
    query_embedding: List[float],
    request: SimilaritySearchRequest
) -> List[SimilarityResult]:
    """Buscar no Qdrant."""
    try:
        from qdrant_client import QdrantClient
        
        # Extrair host e porta da URL
        url = vector_store.connection_url.replace(
            "http://", ""
        ).replace("https://", "").rstrip("/")
        
        if ":" in url:
            host, port_str = url.split(":", 1)
            port = int(port_str.split("/")[0])
        else:
            host = url
            port = 6333
        
        # Conectar e buscar
        if vector_store.api_key:
            client = QdrantClient(
                host=host, 
                port=port, 
                api_key=vector_store.api_key
            )
        else:
            client = QdrantClient(host=host, port=port)
        
        # Se agrupando por documento, buscar mais resultados para ter opções
        search_limit = (
            request.limit * 3 
            if request.group_by_document 
            else request.limit
        )
        
        search_results = client.search(
            collection_name=vector_store.index_name,
            query_vector=query_embedding,
            limit=search_limit,
            score_threshold=request.similarity_threshold,
            with_payload=True,
            with_vectors=False
        )
        
        # Converter resultados
        results = []
        for point in search_results:
            result = SimilarityResult(
                id=str(point.id),
                score=float(point.score),
                text=(
                    point.payload.get("text") 
                    if point.payload else None
                ),
                metadata=(
                    point.payload 
                    if point.payload else None
                )
            )
            results.append(result)
        
        # Agrupar por documento se solicitado
        if request.group_by_document:
            results = group_results_by_document(results, request.limit)
        
        return results
        
    except Exception as e:
        logger.error(f"Erro na busca Qdrant: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Erro na conexão com Qdrant: {str(e)}"
        )


# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@router.post("/similarity", response_model=SimilaritySearchResponse)
async def search_by_similarity(
    request: SimilaritySearchRequest,
    db: Session = Depends(get_db)
):
    """
    Busca por similaridade em banco vetorial.
    
    Fluxo:
    1. Busca configuração do banco vetorial
    2. Busca modelo de embedding configurado  
    3. Gera embedding da consulta
    4. Executa busca no banco vetorial
    5. Agrupa por documento se solicitado
    6. Retorna resultados
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"Iniciando busca: vector_store_id={request.vector_store_id}"
        )
        
        # 1. Buscar banco vetorial
        vector_store = await get_vector_store(
            request.vector_store_id, db
        )
        
        # 2. Buscar modelo de embedding
        embedding_model = await get_embedding_model(
            vector_store.embedding_model_id, db
        )
        
        logger.info(f"Usando modelo: {embedding_model.display_name}")
        
        # 3. Gerar embedding da consulta
        query_embedding = await generate_embedding(
            request.query_text, embedding_model
        )
        
        # 4. Buscar no banco vetorial (só Qdrant por enquanto)
        if vector_store.provider_type != "qdrant":
            raise HTTPException(
                status_code=400,
                detail="Apenas Qdrant é suportado nesta versão"
            )
        
        results = await search_qdrant(vector_store, query_embedding, request)
        
        # 5. Calcular tempo e montar resposta
        search_time_ms = int((time.time() - start_time) * 1000)
        
        response = SimilaritySearchResponse(
            vector_store_id=vector_store.id,
            vector_store_name=vector_store.name,
            query_text=request.query_text,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
            embedding_model_used=embedding_model.display_name,
            grouped_by_document=request.group_by_document,
            searched_at=datetime.utcnow()
        )
        
        logger.info(
            f"Busca concluída: {len(results)} resultados "
            f"em {search_time_ms}ms"
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        ) 