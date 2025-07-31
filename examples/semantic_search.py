from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import time
import openai

from app.models.database import get_db
from app.models.document import AIModel, AIModelType

# Importar funções reutilizáveis
from app.routers.search_dbv import (
    get_vector_store,
    get_embedding_model,
    generate_embedding,
    search_qdrant,
    group_results_by_document,
    SimilarityResult,
    SimilaritySearchResponse,
    SimilaritySearchRequest
)

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["semantic"])


# ========================================
# SCHEMAS
# ========================================

class SemanticAnswer(BaseModel):
    """Schema para resposta semântica de um modelo LLM."""
    model: str = Field(..., description="Nome do modelo LLM usado")
    answer: str = Field(..., description="Resposta gerada pelo modelo")
    context_used: List[str] = Field(
        ..., 
        description="Lista dos textos dos chunks usados como contexto"
    )


class SemanticSearchRequest(BaseModel):
    """Schema para requisição de busca semântica."""
    vector_store_ids: List[int] = Field(
        ..., 
        min_items=1,
        description="IDs dos bancos vetoriais para busca"
    )
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
    llm_model_ids: Optional[List[int]] = Field(
        None,
        description="IDs dos modelos LLM para geração de respostas semânticas"
    )


class SemanticSearchResponse(SimilaritySearchResponse):
    """Schema para resposta de busca semântica estendida."""
    semantic_answers: List[SemanticAnswer] = Field(
        default_factory=list,
        description="Respostas semânticas geradas pelos modelos LLM"
    )


# ========================================
# FUNÇÕES AUXILIARES
# ========================================

async def get_llm_model(llm_model_id: int, db: Session) -> AIModel:
    """Buscar modelo LLM ativo."""
    model = db.query(AIModel).filter(
        AIModel.id == llm_model_id,
        AIModel.model_type == AIModelType.LLM,
        AIModel.is_active.is_(True),
        AIModel.deleted_at.is_(None)
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Modelo LLM com ID {llm_model_id} não encontrado ou inativo"
            )
        )
    
    if not model.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"API key não configurada para o modelo {model.name}"
        )
    
    return model


async def generate_semantic_answer(
    query_text: str, 
    context_chunks: List[str], 
    model: AIModel
) -> str:
    """Gerar resposta semântica usando modelo LLM."""
    try:
        client = openai.OpenAI(api_key=model.api_key)
        
        # Montar contexto
        context = "\n\n".join([
            f"Trecho {i+1}: {chunk}" 
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Prompt estruturado
        prompt = f"""Baseado nos trechos de documentos fornecidos abaixo, \
responda à pergunta de forma clara e objetiva.

Pergunta: {query_text}

Contexto dos documentos:
{context}

Instruções:
- Responda com base apenas nas informações fornecidas no contexto
- Se a informação não estiver disponível no contexto, informe claramente
- Seja conciso mas completo na resposta
- Cite trechos relevantes quando apropriado

Resposta:"""

        # Limitar max_tokens para compatibilidade com diferentes modelos
        max_tokens = (
            min(model.max_context or 2000, 4000) 
            if model.max_context else 2000
        )
        
        response = client.chat.completions.create(
            model=model.name,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Você é um assistente especializado em análise de "
                        "documentos. Forneça respostas precisas baseadas "
                        "apenas no contexto fornecido."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta semântica: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Erro na geração de resposta com modelo "
                f"{model.name}: {str(e)}"
            )
        )


async def search_multiple_vector_stores(
    vector_store_ids: List[int],
    query_embedding: List[float], 
    request: SemanticSearchRequest,
    db: Session
) -> List[SimilarityResult]:
    """Buscar em múltiplos bancos vetoriais e unificar resultados."""
    all_results = []
    
    for store_id in vector_store_ids:
        try:
            # Buscar configuração do banco vetorial
            vector_store = await get_vector_store(store_id, db)
            
            # Realizar busca no banco vetorial
            if vector_store.provider_type != "qdrant":
                logger.warning(
                    f"Banco vetorial {store_id} usa provider "
                    f"{vector_store.provider_type}, apenas Qdrant é suportado"
                )
                continue
            
            # Buscar no Qdrant - criar SimilaritySearchRequest compatível
            similarity_request = SimilaritySearchRequest(
                vector_store_id=store_id,
                query_text=request.query_text,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold,
                group_by_document=request.group_by_document
            )
            
            results = await search_qdrant(
                vector_store, query_embedding, similarity_request
            )
            
            # Adicionar informação do banco vetorial aos metadados
            for result in results:
                if result.metadata:
                    result.metadata['vector_store_id'] = store_id
                    result.metadata['vector_store_name'] = vector_store.name
                else:
                    result.metadata = {
                        'vector_store_id': store_id,
                        'vector_store_name': vector_store.name
                    }
            
            all_results.extend(results)
            
        except HTTPException as e:
            logger.error(
                f"Erro ao buscar no banco vetorial {store_id}: {e.detail}"
            )
            # Continuar com outros bancos mesmo se um falhar
            continue
        except Exception as e:
            logger.error(
                f"Erro inesperado no banco vetorial {store_id}: {str(e)}"
            )
            continue
    
    # Ordenar todos os resultados por score decrescente
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    # Aplicar agrupamento por documento se solicitado
    if request.group_by_document:
        all_results = group_results_by_document(
            all_results, request.limit
        )
    else:
        # Limitar resultados finais
        all_results = all_results[:request.limit]
    
    return all_results


# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@router.post("/semantic", response_model=SemanticSearchResponse)
async def search_semantic(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Busca semântica em múltiplos bancos vetoriais com geração de respostas LLM.
    
    Fluxo:
    1. Valida bancos vetoriais e seus modelos de embedding
    2. Gera embedding da consulta uma única vez
    3. Busca em todos os bancos vetoriais especificados
    4. Unifica e ordena resultados por score
    5. Agrupa por documento se solicitado
    6. Gera respostas semânticas com modelos LLM especificados
    7. Retorna resultados consolidados
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"Iniciando busca semântica: "
            f"vector_stores={request.vector_store_ids}, "
            f"llm_models={request.llm_model_ids}"
        )
        
        # 1. Validar primeiro banco vetorial para obter modelo de embedding
        first_vector_store = await get_vector_store(
            request.vector_store_ids[0], db
        )
        embedding_model = await get_embedding_model(
            first_vector_store.embedding_model_id, db
        )
        
        logger.info(f"Usando modelo embedding: {embedding_model.display_name}")
        
        # 2. Gerar embedding da consulta (uma única vez)
        query_embedding = await generate_embedding(
            request.query_text, embedding_model
        )
        
        # 3. Buscar em todos os bancos vetoriais
        results = await search_multiple_vector_stores(
            request.vector_store_ids,
            query_embedding,
            request,
            db
        )
        
        # 4. Gerar respostas semânticas se modelos LLM foram especificados
        semantic_answers = []
        logger.info(
            f"🔍 LLM IDs: {request.llm_model_ids}, Results: {len(results)}"
        )
        if request.llm_model_ids and results:
            # Extrair textos dos top chunks para contexto
            context_chunks = []
            for result in results:
                # Buscar texto primeiro em result.text, 
                # depois em metadata.chunk_text
                text_content = (
                    result.text or 
                    (result.metadata.get("chunk_text") 
                     if result.metadata else None)
                )
                if text_content:
                    context_chunks.append(text_content)
            
            # Limitar contexto aos top 10 chunks
            context_chunks = context_chunks[:10]
            logger.info(f"🔍 Context chunks: {len(context_chunks)}")
            
            for llm_model_id in request.llm_model_ids:
                logger.info(f"🔍 Processing LLM ID: {llm_model_id}")
                try:
                    logger.info(f"🔍 Testando modelo LLM ID: {llm_model_id}")
                    llm_model = await get_llm_model(llm_model_id, db)
                    logger.info(
                        f"🔍 Modelo encontrado: {llm_model.display_name}"
                    )
                    logger.info(f"🔍 Tem API key: {bool(llm_model.api_key)}")
                    
                    if not context_chunks:
                        logger.warning("🔍 Sem chunks de contexto para LLM!")
                        continue
                        
                    logger.info(
                        f"🔍 Gerando resposta com {len(context_chunks)} chunks"
                    )
                    answer = await generate_semantic_answer(
                        request.query_text,
                        context_chunks,
                        llm_model
                    )
                    logger.info(f"🔍 Resposta gerada: {len(answer)} chars")
                    
                    semantic_answer = SemanticAnswer(
                        model=llm_model.display_name,
                        answer=answer,
                        context_used=context_chunks
                    )
                    
                    semantic_answers.append(semantic_answer)
                    logger.info(
                        f"🔍 Resposta adicionada! Total: {len(semantic_answers)}"
                    )
                    
                except HTTPException as e:
                    logger.error(
                        f"❌ ERRO HTTPException modelo LLM {llm_model_id}: {e.detail}"
                    )
                    # Continuar com outros modelos mesmo se um falhar
                    continue
                except Exception as e:
                    logger.error(
                        f"❌ ERRO inesperado modelo LLM "
                        f"{llm_model_id}: {str(e)}"
                    )
                    continue
        
        # 5. Calcular tempo e montar resposta
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # Determinar nome do vector store para resposta
        vector_store_name = first_vector_store.name
        if len(request.vector_store_ids) > 1:
            vector_store_name = (
                f"{vector_store_name} "
                f"(+{len(request.vector_store_ids)-1} outros)"
            )
        
        response = SemanticSearchResponse(
            vector_store_id=request.vector_store_ids[0],  # ID principal
            vector_store_name=vector_store_name,
            query_text=request.query_text,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
            embedding_model_used=embedding_model.display_name,
            grouped_by_document=request.group_by_document,
            searched_at=datetime.utcnow(),
            semantic_answers=semantic_answers
        )
        
        logger.info(
            f"Busca semântica concluída: {len(results)} resultados, "
            f"{len(semantic_answers)} respostas LLM em {search_time_ms}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erro inesperado na busca semântica: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        ) 