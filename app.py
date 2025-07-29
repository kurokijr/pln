"""Aplicação Flask principal do RAG-Demo."""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from src.config import get_config
from src.document_processor import DocumentProcessor
from src.qa_generator import qa_generator
from langchain_core.documents import Document
from src.vector_store import QdrantVectorStore
from src.storage import StorageManager
from src.chat_service import ChatManager

# Configuração
config = get_config()

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar serviços
document_processor = DocumentProcessor()
storage_manager = StorageManager()
chat_manager = ChatManager()

# Verificar qual tipo de storage está sendo usado
print(f"🗄️ Tipo de storage: {'MinIO' if storage_manager.use_minio else 'Local'}", file=sys.stderr)
print(f"🗄️ Classe de storage: {type(storage_manager.storage).__name__}", file=sys.stderr)

# Inicializar banco de vetores (Qdrant)
import time
max_retries = 5
retry_delay = 5

for attempt in range(max_retries):
    try:
        print(f"🔄 Tentativa {attempt + 1}/{max_retries} de conectar ao Qdrant...")
        vector_store = QdrantVectorStore()
        use_qdrant = True
        print("✅ Conectado ao Qdrant com sucesso!")
        break
    except Exception as e:
        print(f"❌ Erro ao conectar ao Qdrant (tentativa {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            print(f"⏳ Aguardando {retry_delay} segundos antes da próxima tentativa...")
            time.sleep(retry_delay)
        else:
            print("❌ Qdrant é obrigatório para este projeto")
            raise e

# Criar diretórios necessários
Path("uploads").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)


@socketio.on('chat_message')
def handle_chat_message(data):
    """Handler para mensagens de busca por similaridade via WebSocket."""
    try:
        message = data.get('message')
        collection_name = data.get('collection_name')
        similarity_threshold = data.get('similarity_threshold', 0.0)
        
        if not message:
            emit('chat_response', {'error': 'Mensagem é obrigatória'})
            return
        
        # Validar threshold de similaridade
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0.0 or similarity_threshold > 1.0:
            similarity_threshold = 0.0
        
        # Buscar documentos similares diretamente
        if collection_name:
            collection_names = [collection_name]
        else:
            # Buscar em todas as collections
            collections = vector_store.list_collections()
            collection_names = [c['name'] for c in collections]
        
        all_results = []
        for coll_name in collection_names:
            try:
                results = vector_store.search_similar(
                    collection_name=coll_name,
                    query=message,
                    top_k=10,
                    similarity_threshold=similarity_threshold
                )
                # Adicionar informação da collection e número do chunk
                for i, result in enumerate(results, 1):
                    result['source_collection'] = coll_name
                    result['chunk_number'] = i
                all_results.extend(results)
            except Exception as e:
                print(f"Erro ao buscar na collection {coll_name}: {e}")
                continue
        
        # Ordenar por similaridade (maior primeiro)
        all_results.sort(key=lambda x: x.get('similarity_percentage', x.get('score', 0) * 100), reverse=True)
        
        # Enviar resposta via WebSocket
        emit('chat_response', {
            'success': True,
            'response': f"Encontrados {len(all_results)} documentos com similaridade ≥ {(similarity_threshold * 100):.0f}%",
            'sources': all_results,
            'similarity_threshold': similarity_threshold
        })
        
    except Exception as e:
        emit('chat_response', {'error': str(e)})


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo é permitido."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')

@app.route('/api/test')
def test():
    """Endpoint de teste."""
    print("=== TESTE ENDPOINT ===", file=sys.stderr)
    return jsonify({'message': 'Teste OK'})


@app.route('/api/storage-info')
def storage_info():
    """Endpoint para informações do storage e documentos disponíveis."""
    print("=== TESTE STORAGE ENDPOINT ===", file=sys.stderr)
    try:
        storage_type = 'MinIO' if storage_manager.use_minio else 'Local'
        print(f"🗄️ Usando storage: {storage_type}", file=sys.stderr)
        
        # Listar documentos usando o método unificado
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents)}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'storage_type': storage_type,
            'storage_class': type(storage_manager.storage).__name__,
            'documents_count': len(documents),
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no storage: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['GET'])
def list_collections():
    """Lista collections disponíveis."""
    try:
        collections = vector_store.list_collections()
        
        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['POST'])
def create_collection():
    """Cria uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        collection_name = data.get('name')
        embedding_model = data.get('embedding_model')
        description = data.get('description', '')
        
        if not collection_name or not embedding_model:
            return jsonify({'error': 'Nome da collection e modelo de embedding são obrigatórios'}), 400
        
        # Criar collection
        created_name = vector_store.create_collection(
            collection_name=collection_name,
            embedding_model=embedding_model,
            description=description
        )
        
        return jsonify({
            'success': True,
            'message': f'Collection "{created_name}" criada com sucesso',
            'collection_name': created_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name: str):
    """Deleta uma collection."""
    try:
        success = vector_store.delete_collection(collection_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" deletada com sucesso'
            })
        else:
            return jsonify({'error': f'Collection "{collection_name}" não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/embedding-models', methods=['GET'])
def list_embedding_models():
    """Lista modelos de embedding disponíveis."""
    try:
        models = []
        for key, model_config in config.EMBEDDING_MODELS.items():
            models.append({
                'id': key,
                'name': model_config['name'],
                'model': model_config['model'],
                'dimension': model_config['dimension'],
                'provider': model_config['provider']
            })
        
        return jsonify({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/status', methods=['GET'])
def storage_status():
    """Verifica o status do sistema de armazenamento."""
    try:
        storage_type = "MinIO" if storage_manager.use_minio else "Local"
        storage_class = type(storage_manager.storage).__name__
        
        # Testar conectividade básica
        try:
            # Tentar listar documentos para testar se está funcionando
            files = storage_manager.get_document_list()
            connected = True
            error = None
        except Exception as e:
            connected = False
            error = str(e)
        
        return jsonify({
            'storage_type': storage_type,
            'storage_class': storage_class,
            'connected': connected,
            'error': error,
            'status': 'connected' if connected else 'disconnected'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files', methods=['GET'])
def list_storage_files():
    """Lista arquivos armazenados."""
    try:
        collection_name = request.args.get('collection')
        prefix = request.args.get('prefix', '')
        
        files = storage_manager.get_document_list(topic=collection_name)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_files': len(files),
            'collection': collection_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files/<path:object_name>', methods=['DELETE'])
def delete_storage_file(object_name):
    """Deleta um arquivo do storage."""
    try:
        storage_manager.delete_document(object_name)
        return jsonify({
            'success': True,
            'message': f'Arquivo "{object_name}" deletado com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload e processamento de documentos."""
    print("=== INÍCIO DO UPLOAD ===", file=sys.stderr)
    sys.stderr.flush()
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        collection_name = request.form.get('collection_name')
        
        if not file.filename:
            return jsonify({'error': 'Nome do arquivo não fornecido'}), 400
        
        if not collection_name:
            return jsonify({'error': 'Collection não selecionada'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        print(f"📁 Arquivo salvo temporariamente: {file_path}", file=sys.stderr)
        
        # === DEBUG: Verificar storage manager ===
        print(f"🔍 DEBUG Storage Manager:", file=sys.stderr)
        print(f"  - Tipo: {type(storage_manager.storage).__name__}", file=sys.stderr)
        print(f"  - Usando MinIO: {storage_manager.use_minio}", file=sys.stderr)
        
        # Upload do arquivo original para o MinIO
        try:
            print(f"🚀 Iniciando upload para MinIO na collection: {collection_name}", file=sys.stderr)
            print(f"📂 Arquivo: {file_path}", file=sys.stderr)
            sys.stderr.flush()
            
            upload_result = storage_manager.upload_document(file_path, topic=collection_name)
            
            print(f"✅ Upload para MinIO concluído:", file=sys.stderr)
            print(f"   - Path: {upload_result['original_path']}", file=sys.stderr)
            print(f"   - Object: {upload_result['object_name']}", file=sys.stderr)
            print(f"   - Topic: {upload_result['topic']}", file=sys.stderr)
            sys.stderr.flush()
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO no upload para MinIO: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Erro ao fazer upload para MinIO: {str(e)}'}), 500
        
        # Processar documento
        print(f"🔍 Iniciando processamento do arquivo: {file_path}", file=sys.stderr)
        try:
            result = document_processor.process_document(file_path)
            print(f"✅ Processamento concluído: {result.keys() if result else 'None'}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': str(e)}), 500
        
        if not result or 'chunks' not in result:
            print(f"❌ Resultado inválido: {result}", file=sys.stderr)
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': 'Não foi possível processar o documento'}), 400
        
        # Salvar documento processado no MinIO
        try:
            print(f"💾 Salvando documento processado no MinIO", file=sys.stderr)
            processed_filename = f"processed_{filename}"
            processed_path = storage_manager.save_processed_document(
                text=result['enhanced_text'],
                file_name=processed_filename,
                topic=collection_name
            )
            print(f"✅ Documento processado salvo: {processed_path}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao salvar documento processado no MinIO: {str(e)}", file=sys.stderr)
            # Continuar mesmo se falhar ao salvar o processado
            processed_path = None
        
        # Atualizar metadados dos chunks com informações do MinIO
        print(f"📝 Atualizando metadados dos chunks", file=sys.stderr)
        for i, chunk in enumerate(result['chunks']):
            chunk.metadata.update({
                'collection_name': collection_name,
                'minio_original_path': upload_result['original_path'],
                'minio_processed_path': processed_path,
                'upload_timestamp': upload_result['upload_time']
            })
            print(f"   Chunk {i+1}: {len(chunk.page_content)} chars, metadata atualizado", file=sys.stderr)
        
        # Inserir no banco de vetores
        print(f"🔗 Inserindo no banco de vetores (QDrant)", file=sys.stderr)
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=result['chunks']
        )
        
        if success:
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
                print(f"🗑️ Arquivo temporário removido: {file_path}", file=sys.stderr)
            except:
                pass
            
            print(f"🎉 UPLOAD COMPLETO COM SUCESSO!", file=sys.stderr)
            print(f"   - MinIO: {upload_result['original_path']}", file=sys.stderr)
            print(f"   - QDrant: {len(result['chunks'])} chunks", file=sys.stderr)
            sys.stderr.flush()
            
            return jsonify({
                'success': True,
                'message': f'Documento "{filename}" processado e inserido com sucesso',
                'file_name': filename,
                'chunks_count': len(result['chunks']),
                'minio_path': upload_result['original_path'],
                'collection_name': collection_name
            })
        else:
            return jsonify({'error': 'Erro ao inserir documentos no banco de vetores'}), 500
            
    except Exception as e:
        print(f"❌ ERRO GERAL NO UPLOAD: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        # Limpar arquivo temporário em caso de erro
        try:
            if 'file_path' in locals():
                os.remove(file_path)
        except:
            pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para chat com RAG com suporte a múltiplas collections e threshold de similaridade."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        message = data.get('message')
        collection_names = data.get('collection_names')  # Pode ser string, lista ou None
        collection_name = data.get('collection_name')  # Compatibilidade com versão anterior
        session_id = data.get('session_id')
        similarity_threshold = data.get('similarity_threshold', 0.0)  # Threshold de similaridade (0.0 a 1.0)
        
        if not message:
            return jsonify({'error': 'Mensagem é obrigatória'}), 400
        
        # Validar threshold de similaridade
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0.0 or similarity_threshold > 1.0:
            similarity_threshold = 0.0
        
        # Suporte a compatibilidade: se collection_name foi fornecido mas collection_names não
        if collection_name and not collection_names:
            collection_names = collection_name
        
        # Processar mensagem usando o ChatManager
        result = chat_manager.chat(
            session_id=session_id or "",
            message=message,
            collection_names=collection_names,
            similarity_threshold=similarity_threshold
        )
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'sources': result['sources'],
            'session_id': result['session_id'],
            'collections_used': result.get('collections_used', []),
            'processed_by': result.get('processed_by', 'unknown'),
            'similarity_threshold': similarity_threshold
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """Lista sessões de chat."""
    try:
        sessions = chat_manager.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Cria uma nova sessão de chat."""
    try:
        data = request.get_json()
        session_name = data.get('name', 'Nova Sessão')
        
        session_id = chat_manager.create_session(session_name)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Deleta uma sessão de chat."""
    try:
        success = chat_manager.delete_session(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Sessão deletada com sucesso'
            })
        else:
            return jsonify({'error': 'Sessão não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """Lista documentos disponíveis no MinIO."""
    print("=== ENDPOINT /api/documents CHAMADO ===", file=sys.stderr)
    try:
        print("🔍 Chamando storage_manager.get_document_list()", file=sys.stderr)
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents) if documents else 0}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no endpoint /api/documents: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/documents', methods=['GET'])
def list_collection_documents(collection_name: str):
    """Lista documentos originais de uma collection."""
    try:
        print(f"🔍 Listando documentos originais da collection: {collection_name}", file=sys.stderr)
        limit = request.args.get('limit', 1000, type=int)
        
        documents = vector_store.list_collection_documents(
            collection_name=collection_name,
            limit=limit
        )
        
        print(f"📄 Encontrados {len(documents)} documentos originais", file=sys.stderr)
        for i, doc in enumerate(documents[:3]):  # Log dos primeiros 3 para debug
            print(f"   Doc {i+1}: {doc.get('name', 'Sem nome')} - {doc.get('file_type', 'tipo desconhecido')}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total': len(documents),
            'collection_name': collection_name
        })
        
    except Exception as e:
        print(f"❌ Erro ao listar documentos da collection {collection_name}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/recalculate-count', methods=['POST'])
def recalculate_collection_count(collection_name: str):
    """Recalcula a contagem de documentos de uma collection."""
    try:
        vector_store._recalculate_collection_document_count(collection_name)
        return jsonify({
            'success': True,
            'message': f'Contagem de documentos da collection "{collection_name}" recalculada'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<document_name>/content', methods=['GET'])
def get_document_content(document_name: str):
    """Obtém o conteúdo de um documento específico."""
    try:
        # Decodificar o nome do documento se necessário
        import urllib.parse
        document_name = urllib.parse.unquote(document_name)
        
        # Buscar o documento no MinIO
        try:
            content_bytes = storage_manager.storage.download_file(document_name)
            content = content_bytes.decode('utf-8')
        except Exception as e:
            return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        
        return jsonify({
            'success': True,
            'content': content,
            'document_name': document_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/content', methods=['GET'])
def get_collection_content(collection_name: str):
    """Obtém o conteúdo de todos os documentos de uma collection para geração de Q&A."""
    try:
        # Verificar se é uma requisição para documento específico
        document_name = request.args.get('document')
        
        if document_name:
            # Buscar documento específico no storage
            try:
                # Primeiro, tentar encontrar o documento na collection para obter o caminho processado
                documents = vector_store.list_collection_documents(collection_name)
                
                # Encontrar o documento específico por nome original
                target_doc = None
                for doc in documents:
                    # Comparar pelo nome do arquivo original ou pelo minio_original_path
                    if (doc.get('name') == document_name or 
                        doc.get('file_name') == document_name or
                        doc.get('minio_original_path') == document_name or
                        doc.get('original_path') == document_name):
                        target_doc = doc
                        break
                
                if not target_doc:
                    return jsonify({'error': f'Documento {document_name} não encontrado na collection {collection_name}'}), 404
                
                # Usar o caminho processado se disponível, senão o original
                processed_path = target_doc.get('minio_processed_path')
                if not processed_path:
                    return jsonify({'error': f'Documento {document_name} não possui versão processada disponível'}), 404
                
                print(f"🔍 Buscando documento processado: {processed_path}", file=sys.stderr)
                
                if storage_manager.use_minio:
                    # MinIO storage
                    content_bytes = storage_manager.storage.download_file(processed_path)
                    # Tentar diferentes codificações
                    try:
                        content = content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            content = content_bytes.decode('latin-1')
                            print(f"⚠️ Usando codificação latin-1 para {processed_path}", file=sys.stderr)
                        except UnicodeDecodeError:
                            try:
                                content = content_bytes.decode('cp1252')
                                print(f"⚠️ Usando codificação cp1252 para {processed_path}", file=sys.stderr)
                            except UnicodeDecodeError:
                                # Como último recurso, usar utf-8 com erro 'ignore'
                                content = content_bytes.decode('utf-8', errors='ignore')
                                print(f"⚠️ Usando UTF-8 com ignore para {processed_path}", file=sys.stderr)
                else:
                    # Local storage
                    try:
                        content = storage_manager.storage.read_file(processed_path)
                    except UnicodeDecodeError:
                        # Tentar ler como binário e decodificar
                        with open(processed_path, 'rb') as f:
                            content_bytes = f.read()
                        try:
                            content = content_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            content = content_bytes.decode('utf-8', errors='ignore')
                
                print(f"✅ Conteúdo obtido com sucesso. Tamanho: {len(content)} caracteres", file=sys.stderr)
                
                return jsonify({
                    'success': True,
                    'content': content,
                    'document_name': target_doc.get('name', document_name),
                    'processed_path': processed_path,
                    'document_count': 1
                })
            except Exception as e:
                print(f"❌ Erro ao buscar documento: {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        else:
            # Comportamento original - conteúdo da collection
            documents = vector_store.list_collection_documents(collection_name)
            
            # Concatenar conteúdo de todos os documentos
            content = ""
            for doc in documents:
                if doc.get('content'):
                    content += doc['content'] + "\n\n"
            
            return jsonify({
                'success': True,
                'content': content,
                'document_count': len(documents)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/qa-generate', methods=['POST'])
def generate_qa():
    """Gera perguntas e respostas a partir de um documento (apenas geração, sem vetorização)."""
    try:
        data = request.get_json()
        print(f"🔍 Dados recebidos no qa-generate: {data is not None}", file=sys.stderr)
        
        if not data:
            print("❌ Nenhum dado JSON fornecido", file=sys.stderr)
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        content = data.get('content')
        num_questions = data.get('num_questions', 10)
        difficulty = data.get('difficulty', 'Intermediário')
        temperature = data.get('temperature', 0.5)
        context_keywords = data.get('context_keywords', '')
        custom_prompt = data.get('custom_prompt', '')
        
        print(f"📄 Tamanho do conteúdo: {len(content) if content else 0}", file=sys.stderr)
        
        # Debug individual das variáveis
        try:
            print(f"🔢 num_questions: {num_questions} (tipo: {type(num_questions)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com num_questions: {e}", file=sys.stderr)
            
        try:
            print(f"🎚️ difficulty: '{difficulty}' (tipo: {type(difficulty)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com difficulty: {e}", file=sys.stderr)
            
        try:
            print(f"🌡️ temperature: {temperature} (tipo: {type(temperature)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com temperature: {e}", file=sys.stderr)
            
        try:
            print(f"🔤 Context keywords: '{context_keywords}' (tipo: {type(context_keywords)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com context_keywords: {e}", file=sys.stderr)
            
        try:
            print(f"📝 Custom prompt length: {len(custom_prompt) if custom_prompt else 0}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com custom_prompt: {e}", file=sys.stderr)
        
        if not content:
            print("❌ Conteúdo vazio ou não fornecido", file=sys.stderr)
            return jsonify({'error': 'Conteúdo é obrigatório'}), 400
        
        if not content.strip():
            print("❌ Conteúdo contém apenas espaços em branco", file=sys.stderr)
            return jsonify({'error': 'Conteúdo não pode estar vazio'}), 400
        
        print(f"✅ Validações passadas. qa_generator: {type(qa_generator)}", file=sys.stderr)
        
        # Processar custom prompt substituindo placeholders
        if custom_prompt:
            processed_prompt = custom_prompt.format(
                num_questions=num_questions,
                context_keywords=context_keywords,
                difficulty=difficulty,
                document_text=content
            )
            print(f"🔧 Prompt processado (primeiros 100 chars): {repr(processed_prompt[:100])}", file=sys.stderr)
        else:
            processed_prompt = custom_prompt
            print(f"🔧 Usando prompt padrão", file=sys.stderr)
        
        # Parâmetros para geração de Q&A
        params = {
            'num_questions': num_questions,
            'context_keywords': context_keywords,
            'difficulty': difficulty,
            'temperature': temperature,
            'custom_prompt': processed_prompt
        }
        
        # Gerar Q&A
        print(f"🚀 Iniciando geração de Q&A com {len(content)} caracteres...", file=sys.stderr)
        print(f"📋 Parâmetros completos: {params}", file=sys.stderr)
        
        try:
            print("⚡ Prestes a chamar qa_generator.generate_qa_pairs()", file=sys.stderr)
            qa_content = qa_generator.generate_qa_pairs(content, params)
            print(f"✅ Função generate_qa_pairs retornou!", file=sys.stderr)
            print(f"📊 Resultado da geração: {type(qa_content)}, length: {len(qa_content) if qa_content else 0}", file=sys.stderr)
            if qa_content:
                print(f"📄 Preview: {repr(qa_content[:100])}", file=sys.stderr)
        except Exception as gen_error:
            print(f"❌ Erro durante geração: {str(gen_error)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Erro na geração de Q&A: {str(gen_error)}'}), 500
        
        if not qa_content:
            print("❌ Q&A generator retornou conteúdo vazio", file=sys.stderr)
            return jsonify({'error': 'Não foi possível gerar perguntas e respostas'}), 400
        
        if not qa_content.strip():
            print("❌ Q&A generator retornou apenas espaços em branco", file=sys.stderr)
            return jsonify({'error': 'Conteúdo Q&A gerado está vazio'}), 400
        
        # Converter para documentos (apenas para contar)
        documents = qa_generator.qa_to_documents(qa_content, "temp")
        
        return jsonify({
            'success': True,
            'message': f'{len(documents)} pares de Q&A gerados com sucesso',
            'qa_content': qa_content,
            'qa_count': len(documents)
        })
            
    except Exception as e:
        print(f"❌ Erro ao gerar Q&A: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/qa-vectorize', methods=['POST'])
def vectorize_qa():
    """Vetoriza Q&As já gerados em uma collection específica."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        qa_content = data.get('qa_content')
        collection_name = data.get('collection_name')
        
        if not qa_content or not collection_name:
            return jsonify({'error': 'Conteúdo Q&A e collection são obrigatórios'}), 400
        
        # Converter para documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        # Inserir no banco de vetores
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{len(documents)} pares de Q&A inseridos com sucesso na collection {collection_name}',
                'qa_count': len(documents)
            })
        else:
            return jsonify({'error': 'Erro ao inserir Q&A no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/create-qa-embeddings', methods=['POST'])
def create_qa_embeddings():
    """Cria embeddings a partir dos Q&As gerados e insere em uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        qa_content = data.get('qa_content')
        collection_name = data.get('collection_name')
        embedding_model = data.get('embedding_model', 'text-embedding-3-small')
        
        if not qa_content or not collection_name:
            return jsonify({'error': 'Conteúdo Q&A e nome da collection são obrigatórios'}), 400
        
        # Converter Q&A em documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        if not documents:
            return jsonify({'error': 'Não foi possível processar os Q&As'}), 400
        
        # Inserir documentos na nova collection
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" criada com {len(documents)} Q&As como embeddings',
                'collection_name': collection_name,
                'documents_count': len(documents),
                'embedding_model': embedding_model
            })
        else:
            return jsonify({'error': 'Erro ao criar embeddings no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/semantic-search', methods=['POST'])
def semantic_search():
    """Endpoint para busca semântica que aciona o N8N."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        question = data.get('question')
        collection_name = data.get('collection_name', '')
        models = data.get('models', {})
        
        if not question:
            return jsonify({'error': 'Pergunta é obrigatória'}), 400
        
        # Verificar se pelo menos um modelo foi selecionado
        openai_enabled = models.get('openai', False)
        gemini_enabled = models.get('gemini', False)
        
        if not openai_enabled and not gemini_enabled:
            return jsonify({'error': 'Pelo menos um modelo deve ser selecionado'}), 400
        
        # Configuração do N8N
        n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
        if not n8n_webhook_url:
            return jsonify({'error': 'N8N_WEBHOOK_URL não configurada no .env'}), 500
        
        # Ajustar URL para o webhook de busca semântica
        if '/webhook-test/' in n8n_webhook_url:
            # Se for um webhook de teste, usar o mesmo padrão para semantic-search
            n8n_webhook_url = n8n_webhook_url.replace('/webhook-test/', '/webhook/semantic-search/')
        elif not n8n_webhook_url.endswith('/semantic-search'):
            # Se não terminar com /semantic-search, adicionar
            n8n_webhook_url = n8n_webhook_url.rstrip('/') + '/semantic-search'
        
        # Preparar dados para o N8N
        n8n_payload = {
            'question': question,
            'collection_name': collection_name,
            'models': {
                'openai': openai_enabled,
                'gemini': gemini_enabled
            },
            'timestamp': time.time()
        }
        
        # Fazer requisição para o N8N
        import requests
        try:
            response = requests.post(
                n8n_webhook_url,
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
                
                return jsonify({
                    'success': True,
                    'responses': responses,
                    'n8n_workflow_id': n8n_result.get('workflow_id'),
                    'processing_time': n8n_result.get('processing_time')
                })
            else:
                return jsonify({
                    'error': f'Erro no N8N: {response.status_code} - {response.text}'
                }), 500
                
        except requests.exceptions.RequestException as e:
            return jsonify({
                'error': f'Erro de conexão com N8N: {str(e)}'
            }), 500
            
    except Exception as e:
        print(f"❌ Erro na busca semântica: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=== ROTAS REGISTRADAS ===", file=sys.stderr)
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}", file=sys.stderr)
    print("=========================", file=sys.stderr)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) 