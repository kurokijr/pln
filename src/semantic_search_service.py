"""Serviço de busca semântica integrada com N8N."""

import os
import time
import requests
from typing import Dict, Any, List
from src.config import get_config
from src.multi_agent_chat_service import MultiAgentChatService

config = get_config()


class SemanticSearchService:
    """Serviço especializado em busca semântica com integração N8N."""
    
    def __init__(self):
        """Inicializa o serviço de busca semântica."""
        self.n8n_webhook_url = config.N8N_WEBHOOK_URL
        self.multi_agent_service = MultiAgentChatService()
    
    def _organize_collections_by_model(self, collection_names: List[str], 
                                     openai_enabled: bool, gemini_enabled: bool) -> Dict[str, Any]:
        """
        Organiza collections por modelo baseado nos providers ativos.
        
        Args:
            collection_names: Lista de nomes das collections
            openai_enabled: Se OpenAI está habilitado
            gemini_enabled: Se Gemini está habilitado
            
        Returns:
            Dict com collections organizadas por modelo
        """
        # Obter informações detalhadas das collections
        collections_info = self.multi_agent_service.get_knowledge_sources_info(collection_names)
        
        # Organizar por modelo
        models = {}
        
        if openai_enabled:
            openai_collections = [
                col["name"] for col in collections_info 
                if col.get("model_provider") == "openai"
            ]
            models["openai"] = {
                "enabled": True,
                "collections": openai_collections
            }
        
        if gemini_enabled:
            gemini_collections = [
                col["name"] for col in collections_info 
                if col.get("model_provider") == "gemini"
            ]
            models["gemini"] = {
                "enabled": True,
                "collections": gemini_collections
            }
        
        return models
    
    def search_with_n8n(self, question: str, collection_names: List[str] = None, 
                       openai_enabled: bool = False, gemini_enabled: bool = False) -> Dict[str, Any]:
        """
        Executa busca semântica usando N8N para orquestração de múltiplos modelos de IA.
        
        Args:
            question: Pergunta/query do usuário
            collection_names: Lista de nomes das collections para buscar
            openai_enabled: Se deve usar OpenAI
            gemini_enabled: Se deve usar Gemini
        
        Returns:
            Dict com os resultados da busca semântica
        """
        try:
            # Verificar se N8N_WEBHOOK_URL está configurada
            if not self.n8n_webhook_url:
                return {
                    'success': False,
                    'error': 'N8N_WEBHOOK_URL não configurada no .env'
                }
            
            # Verificar conectividade com N8N antes de fazer a requisição
            n8n_base_url = self.n8n_webhook_url.split('/webhook-test/')[0]
            
            try:
                health_check = requests.get(f"{n8n_base_url}/healthz", timeout=5)
                if health_check.status_code != 200:
                    return {
                        'success': False,
                        'error': f'N8N não está respondendo corretamente. Status: {health_check.status_code}'
                    }
            except requests.exceptions.RequestException as e:
                return {
                    'success': False,
                    'error': f'N8N não está acessível. Verifique se está rodando na porta 5678. Erro: {str(e)}'
                }
            
            # Organizar collections por modelo
            organized_models = self._organize_collections_by_model(
                collection_names or [], openai_enabled, gemini_enabled
            )
            
            # Preparar dados para o N8N com estrutura agrupada por modelo
            n8n_payload = {
                'question': question,
                'models': organized_models,
                'timestamp': time.time()
            }
            
            # Fazer requisição para o N8N
            response = requests.post(
                self.n8n_webhook_url,
                json=n8n_payload,
                headers={'Content-Type': 'application/json'},
                timeout=60  # Timeout de 60 segundos
            )
            
            if response.status_code == 200:
                n8n_result = response.json()
                
                # Processar resposta do N8N
                responses = {}
                
                if openai_enabled and 'openai_response' in n8n_result:
                    responses['openai'] = n8n_result['openai_response']
                
                if gemini_enabled and 'gemini_response' in n8n_result:
                    responses['gemini'] = n8n_result['gemini_response']
                
                return {
                    'success': True,
                    'responses': responses,
                    'n8n_workflow_id': n8n_result.get('workflow_id'),
                    'processing_time': n8n_result.get('processing_time')
                }
            elif response.status_code == 404:
                # Webhook não registrado - erro específico
                try:
                    error_data = response.json()
                    if 'webhook' in error_data.get('message', '').lower():
                        return {
                            'success': False,
                            'error': 'Webhook do N8N não está registrado. Execute o workflow no N8N primeiro para ativar o webhook.',
                            'details': error_data.get('message', ''),
                            'hint': error_data.get('hint', '')
                        }
                except:
                    pass
                
                return {
                    'success': False,
                    'error': f'Webhook do N8N não encontrado (404). Verifique se o workflow está ativo.',
                    'status_code': response.status_code,
                    'response_text': response.text
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro no N8N: {response.status_code} - {response.text}'
                }
                
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f'Erro de conexão com N8N: Não foi possível conectar ao servidor N8N. Verifique se está rodando.',
                'details': str(e)
            }
        except requests.exceptions.Timeout as e:
            return {
                'success': False,
                'error': f'Timeout na conexão com N8N: A requisição demorou mais de 60 segundos.',
                'details': str(e)
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Erro de conexão com N8N: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro geral na busca semântica: {str(e)}'
            }
    
    def test_n8n_connectivity(self) -> Dict[str, Any]:
        """Testa a conectividade com o N8N."""
        try:
            if not self.n8n_webhook_url:
                return {
                    'success': False,
                    'message': 'N8N_WEBHOOK_URL não configurada no .env'
                }
            
            n8n_base_url = self.n8n_webhook_url.split('/webhook-test/')[0]
            
            # Teste de conectividade básica
            health_check = requests.get(f"{n8n_base_url}/healthz", timeout=5)
            
            if health_check.status_code == 200:
                # Teste do webhook
                webhook_response = requests.get(self.n8n_webhook_url, timeout=5)
                
                return {
                    'success': True,
                    'message': 'N8N está acessível e funcionando',
                    'health_status': health_check.status_code,
                    'webhook_status': webhook_response.status_code,
                    'webhook_url': self.n8n_webhook_url,
                    'n8n_version': health_check.headers.get('X-N8N-Version', 'unknown')
                }
            else:
                return {
                    'success': False,
                    'message': f'N8N health check falhou com status: {health_check.status_code}',
                    'health_status': health_check.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f'Erro de conexão com N8N: {str(e)}'
            }