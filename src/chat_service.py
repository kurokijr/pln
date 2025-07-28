"""Serviço de chat RAG com Qdrant."""

import os
import json
from typing import List, Dict, Any, Optional
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
    
    def chat(self, session_id: str, message: str, collection_name: str = None) -> Dict[str, Any]:
        """Processa uma mensagem de chat."""
        try:
            # Verificar se a sessão existe
            if session_id not in self.sessions:
                session_id = self.create_session()
            
            session = self.sessions[session_id]
            
            # Adicionar mensagem do usuário
            session.add_message("user", message)
            
            # Buscar documentos relevantes
            relevant_docs = self.search_relevant_documents(message, collection_name)
            
            # Gerar resposta
            response = self.generate_response(message, relevant_docs, session.messages)
            
            # Adicionar resposta do assistente
            session.add_message("assistant", response, relevant_docs)
            
            return {
                "response": response,
                "sources": relevant_docs,
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "response": f"Erro ao processar mensagem: {str(e)}",
                "sources": [],
                "session_id": session_id
            }
    
    def search_relevant_documents(self, query: str, collection_name: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca documentos relevantes para a consulta."""
        try:
            if self.use_qdrant and collection_name:
                return self.vector_store.search_similar(collection_name, query, top_k)
            elif self.use_qdrant:
                # Se não há collection específica, buscar em todas as collections
                all_results = []
                collections = self.vector_store.list_collections()
                
                for collection_info in collections:
                    if collection_info.get("exists_in_qdrant"):
                        try:
                            results = self.vector_store.search_similar(
                                collection_info["name"], query, top_k
                            )
                            all_results.extend(results)
                        except Exception as e:
                            print(f"Erro ao buscar na collection {collection_info['name']}: {e}")
                            continue
                
                # Ordenar por score e retornar os melhores
                all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
                return all_results[:top_k]
            else:
                return []
        except Exception as e:
            print(f"Erro na busca de documentos: {e}")
            return []
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]], 
                         chat_history: List[ChatMessage]) -> str:
        """Gera resposta baseada nos documentos relevantes."""
        try:
            # Construir contexto dos documentos
            context = ""
            if relevant_docs:
                context = "\n\n".join([doc.get('text', '') for doc in relevant_docs[:3]])
            
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
    
    def chat(self, session_id: str, message: str, collection_name: str = None) -> Dict[str, Any]:
        """Processa mensagem de chat com persistência."""
        result = self.chat_service.chat(session_id, message, collection_name)
        self._save_sessions()
        return result
    
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