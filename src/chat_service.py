"""Serviço de chat RAG com Qdrant."""

import os
import json
import requests
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict

from src.config import get_config
from src.vector_store import QdrantVectorStore

config = get_config()


@dataclass
class ChatMessage:
    """Representa uma mensagem de chat."""
    role: str  # 'user' ou 'assistant'
    content: str
    timestamp: datetime
    sources: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sources": self.sources or []
        }


@dataclass
class ChatSession:
    """Representa uma sessão de chat."""
    session_id: str
    messages: List[ChatMessage] = None
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        """Inicializa valores padrão."""
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def add_message(self, role: str, content: str, sources: List[Dict[str, Any]] = None):
        """Adiciona uma mensagem à sessão."""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            sources=sources
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class RAGChatService:
    """Serviço de chat RAG usando Qdrant."""
    
    def __init__(self):
        """Inicializa o serviço de chat."""
        self.vector_store = QdrantVectorStore()
        self.use_qdrant = True
        self.use_n8n = True  # Flag para habilitar/desabilitar N8N
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self) -> str:
        """Cria uma nova sessão de chat."""
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ChatSession(session_id)
        return session_id
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta uma sessão de chat."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões."""
        return [session.to_dict() for session in self.sessions.values()]
    
    def send_to_n8n(self, message: str, collections_info: List[Dict[str, Any]], 
                    session_id: str, chat_history: List[ChatMessage]) -> Dict[str, Any]:
        """Envia requisição para o webhook N8N do chat."""
        try:
            n8n_url = f"{config.N8N_WEBHOOK_URL}/rag-chat"
            
            # Preparar histórico de chat para envio
            history = []
            if chat_history:
                recent_messages = chat_history[-6:]  # Últimas 6 mensagens
                history = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in recent_messages
                ]
            
            # Preparar payload
            payload = {
                "message": message,
                "session_id": session_id,
                "collections": collections_info,
                "chat_history": history,
                "timestamp": datetime.now().isoformat(),
                "source": "rag-demo"
            }
            
            # Fazer request para N8N
            headers = {"Content-Type": "application/json"}
            
            # Adicionar autenticação básica se configurada
            auth = None
            if hasattr(config, 'N8N_USERNAME') and hasattr(config, 'N8N_PASSWORD'):
                auth = (config.N8N_USERNAME, config.N8N_PASSWORD)
            
            response = requests.post(
                n8n_url,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Processar resposta do N8N
            n8n_response = response.json()
            
            return {
                "success": True,
                "response": n8n_response.get("response", "Resposta processada pelo N8N"),
                "sources": n8n_response.get("sources", []),
                "n8n_data": n8n_response
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição para N8N: {e}")
            return {
                "success": False,
                "error": f"Erro de conexão com N8N: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Erro geral no N8N: {e}")
            return {
                "success": False,
                "error": f"Erro ao processar com N8N: {str(e)}"
            }
    
    def get_collections_info(self, collection_names: List[str] = None) -> List[Dict[str, Any]]:
        """Obtém informações detalhadas das collections selecionadas."""
        try:
            all_collections = self.vector_store.list_collections()
            
            if collection_names:
                # Filtrar apenas as collections selecionadas
                selected_collections = [
                    col for col in all_collections 
                    if col["name"] in collection_names and col.get("exists_in_qdrant", True)
                ]
            else:
                # Se não especificado, usar todas as collections existentes
                selected_collections = [
                    col for col in all_collections 
                    if col.get("exists_in_qdrant", True)
                ]
            
            # Enriquecer com informações adicionais
            collections_info = []
            for col in selected_collections:
                collection_info = {
                    "name": col["name"],
                    "embedding_model": col.get("embedding_model", "unknown"),
                    "model_config": col.get("model_config", {}),
                    "description": col.get("description", ""),
                    "document_count": col.get("document_count", 0),
                    "created_at": col.get("created_at", ""),
                    "vector_dimension": col.get("model_config", {}).get("dimension", 0),
                    "model_provider": col.get("model_config", {}).get("provider", "unknown")
                }
                collections_info.append(collection_info)
            
            return collections_info
            
        except Exception as e:
            print(f"❌ Erro ao obter informações das collections: {e}")
            return []
    
    def chat(self, session_id: str, message: str, 
             collection_names: Union[str, List[str]] = None, 
             similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """
        Processa uma mensagem de chat com suporte a múltiplas collections e threshold de similaridade.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do usuário
            collection_names: Nome(s) da(s) collection(s) - pode ser string, lista ou None para todas
            similarity_threshold: Threshold de similaridade (0.0 a 1.0, onde 0.0 = 0% e 1.0 = 100%)
        """
        try:
            # Verificar se a sessão existe
            if session_id not in self.sessions:
                session_id = self.create_session()
            
            session = self.sessions[session_id]
            
            # Adicionar mensagem do usuário
            session.add_message("user", message)
            
            # Normalizar collection_names para lista
            if isinstance(collection_names, str):
                collection_names = [collection_names]
            elif collection_names is None:
                collection_names = []
            
            # Obter informações das collections
            collections_info = self.get_collections_info(collection_names)
            
            if not collections_info:
                print("⚠️ Nenhuma collection válida encontrada")
            
            # Processar com N8N se habilitado
            if self.use_n8n:
                n8n_result = self.send_to_n8n(message, collections_info, session_id, session.messages)
                
                if n8n_result["success"]:
                    response = n8n_result["response"]
                    sources = n8n_result["sources"]
                    
                    # Adicionar resposta do assistente
                    session.add_message("assistant", response, sources)
                    
                    return {
                        "response": response,
                        "sources": sources,
                        "session_id": session_id,
                        "collections_used": collections_info,
                        "processed_by": "n8n"
                    }
                else:
                    # Fallback para processamento local se N8N falhar
                    print("⚠️ N8N falhou, usando processamento local como fallback")
            
            # Processamento local (fallback ou quando N8N está desabilitado)
            relevant_docs = self.search_relevant_documents_multiple(message, collection_names, similarity_threshold=similarity_threshold)
            response = self.generate_response(message, relevant_docs, session.messages)
            
            # Adicionar resposta do assistente
            session.add_message("assistant", response, relevant_docs)
            
            return {
                "response": response,
                "sources": relevant_docs,
                "session_id": session_id,
                "collections_used": collections_info,
                "processed_by": "local"
            }
            
        except Exception as e:
            error_msg = f"Erro ao processar mensagem: {str(e)}"
            return {
                "response": error_msg,
                "sources": [],
                "session_id": session_id,
                "collections_used": [],
                "processed_by": "error"
            }
    
    def search_relevant_documents_multiple(self, query: str, collection_names: List[str] = None, 
                                         top_k: int = 5, similarity_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca documentos relevantes em múltiplas collections com threshold de similaridade.
        
        Args:
            query: Query de busca
            collection_names: Lista de collections para buscar
            top_k: Número máximo de resultados por collection
            similarity_threshold: Threshold de similaridade (0.0 a 1.0, onde 0.0 = 0% e 1.0 = 100%)
        """
        try:
            if not self.use_qdrant:
                return []
            
            all_results = []
            
            if collection_names:
                # Buscar nas collections especificadas
                for collection_name in collection_names:
                    try:
                        results = self.vector_store.search_similar(
                            collection_name, 
                            query, 
                            top_k, 
                            similarity_threshold=similarity_threshold
                        )
                        # Adicionar informação da collection de origem
                        for result in results:
                            result["source_collection"] = collection_name
                        all_results.extend(results)
                    except Exception as e:
                        print(f"Erro ao buscar na collection {collection_name}: {e}")
                        continue
            else:
                # Buscar em todas as collections disponíveis
                collections = self.vector_store.list_collections()
                
                for collection_info in collections:
                    if collection_info.get("exists_in_qdrant"):
                        try:
                            results = self.vector_store.search_similar(
                                collection_info["name"], query, top_k
                            )
                            # Adicionar informação da collection de origem
                            for result in results:
                                result["source_collection"] = collection_info["name"]
                            all_results.extend(results)
                        except Exception as e:
                            print(f"Erro ao buscar na collection {collection_info['name']}: {e}")
                            continue
            
            # Ordenar por score e retornar os melhores
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            print(f"Erro na busca de documentos: {e}")
            return []

    # Manter método antigo para compatibilidade
    def search_relevant_documents(self, query: str, collection_name: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca documentos relevantes para a consulta. (Método de compatibilidade)"""
        if collection_name:
            return self.search_relevant_documents_multiple(query, [collection_name], top_k)
        else:
            return self.search_relevant_documents_multiple(query, None, top_k)
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]], 
                         chat_history: List[ChatMessage]) -> str:
        """Gera resposta baseada nos documentos relevantes."""
        try:
            # Construir contexto dos documentos
            context = ""
            if relevant_docs:
                context_parts = []
                for doc in relevant_docs[:3]:
                    source_collection = doc.get('source_collection', 'unknown')
                    text = doc.get('text', '')
                    context_parts.append(f"[Collection: {source_collection}]\n{text}")
                context = "\n\n".join(context_parts)
            
            # Construir histórico de chat
            history = ""
            if chat_history:
                recent_messages = chat_history[-6:]  # Últimas 6 mensagens
                history = "\n".join([
                    f"{msg.role}: {msg.content}" for msg in recent_messages
                ])
            
            # Prompt para o LLM
            prompt = f"""Você é um assistente educacional especializado em Processamento de Linguagem Natural.

Contexto dos documentos:
{context}

Histórico da conversa:
{history}

Pergunta do usuário: {query}

Responda de forma clara e educativa, baseando-se no contexto fornecido. Se não houver informações relevantes no contexto, seja honesto sobre isso.

Resposta:"""
            
            # Usar OpenAI para gerar resposta
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                api_key=config.OPENAI_API_KEY,
                model=config.OPENAI_MODEL,
                temperature=0.7
            )
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"
    
    def get_collections(self) -> List[str]:
        """Retorna lista de collections disponíveis."""
        try:
            if self.use_qdrant:
                collections = self.vector_store.list_collections()
                return [c['name'] for c in collections if c.get('exists_in_qdrant')]
            else:
                return ["default"]
        except Exception as e:
            print(f"Erro ao listar collections: {e}")
            return ["default"]


class ChatManager:
    """Gerenciador de chat com persistência."""
    
    def __init__(self, storage_file: str = "data/chat_sessions.json"):
        """Inicializa o gerenciador de chat."""
        self.storage_file = storage_file
        self.chat_service = RAGChatService()
        self._load_sessions()
    
    def _load_sessions(self):
        """Carrega sessões do arquivo."""
        try:
            import json
            from pathlib import Path
            
            file_path = Path(self.storage_file)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                
                for session_data in sessions_data:
                    session = ChatSession(session_data["session_id"])
                    session.messages = session_data.get("messages", [])
                    session.created_at = datetime.fromisoformat(session_data["created_at"])
                    session.last_activity = datetime.fromisoformat(session_data["last_activity"])
                    self.chat_service.sessions[session.session_id] = session
                    
        except Exception as e:
            print(f"Erro ao carregar sessões: {e}")
    
    def _save_sessions(self):
        """Salva sessões no arquivo."""
        try:
            import json
            from pathlib import Path
            
            file_path = Path(self.storage_file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            sessions_data = [session.to_dict() for session in self.chat_service.sessions.values()]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Erro ao salvar sessões: {e}")
    
    def chat(self, session_id: str, message: str, collection_names: Union[str, List[str]] = None, 
             similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """Processa mensagem de chat com persistência e threshold de similaridade."""
        result = self.chat_service.chat(session_id, message, collection_names, similarity_threshold)
        self._save_sessions()
        return result
    
    # Método de compatibilidade para código antigo
    def generate_response(self, message: str, context_docs: List[Dict[str, Any]], session_id: str) -> str:
        """Método de compatibilidade - gera resposta usando o sistema antigo."""
        try:
            # Usar o novo sistema de chat com documentos fornecidos
            if session_id not in self.chat_service.sessions:
                session_id = self.create_session()
            
            session = self.chat_service.sessions[session_id]
            response = self.chat_service.generate_response(message, context_docs, session.messages)
            return response
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"
    
    def create_session(self) -> str:
        """Cria nova sessão com persistência."""
        session_id = self.chat_service.create_session()
        self._save_sessions()
        return session_id
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta sessão com persistência."""
        result = self.chat_service.delete_session(session_id)
        if result:
            self._save_sessions()
        return result
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões."""
        return self.chat_service.list_sessions()
    
    def get_collections(self) -> List[str]:
        """Lista collections disponíveis."""
        return self.chat_service.get_collections() 